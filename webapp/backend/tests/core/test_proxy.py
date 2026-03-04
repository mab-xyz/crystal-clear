import builtins

from src.api.core import proxy


def test_clean_line_and_extract_helpers():
    assert proxy.clean_line("x = 1; // comment") == "x = 1;"
    assert proxy.is_hex_or_operation("0xabc") is True
    assert proxy.is_hex_or_operation("varName") is False
    assert proxy.is_hardcoded_address("0x" + "a" * 40) is True
    assert proxy.is_hardcoded_address("0x123") is False

    vars_ = proxy.extract_variables_from_expression("impl = (slot >> 8) & 0xff + msg")
    assert "impl" in vars_ or "slot" in vars_



def test_keccak_and_storage_detection():
    lines = [
        "slot = keccak256(0x360894);",
        "storage[slot] = implementation;",
    ]
    traces = proxy.detect_keccak256_traces(lines)
    assert traces["slot"] == "0x360894"

    assigns = proxy.detect_storage_assignments(traces, lines)
    assert assigns["0x360894"] == "implementation"



def test_extract_implementation_address():
    line = "result = delegatecall(gas(), implVar, data, len);"
    assert proxy.extract_implementation_address(line) == "implVar"



def test_function_boundaries_and_delegatecall_marking():
    lines = [
        "function foo() {",
        "x = 1;",
        "}",
        "fallback() {",
        "delegatecall(gas(), impl, 0, 0)",
        "}",
    ]
    funcs = proxy.find_function_boundaries(lines)
    proxy.mark_delegatecall_functions([], funcs, lines)
    fallback_idx = proxy.identify_fallback_function(funcs, lines)

    assert fallback_idx is not None
    assert any(v.get("delegatecall") for v in funcs.values())



def test_trace_variable_and_assignment_checks():
    lines = [
        "owner = admin;",
        "impl = owner;",
        "fallback() {",
        "delegatecall(gas(), impl, 0, 0)",
        "}",
    ]

    origins = proxy.trace_variable("impl", lines, 3)
    assert "admin" in origins or "owner" in origins

    funcs = proxy.find_function_boundaries(
        [
            "function setImpl() {",
            "impl = newImpl;",
            "}",
            "fallback() {",
            "delegatecall(gas(), impl, 0, 0)",
            "}",
        ]
    )
    fb = proxy.identify_fallback_function(funcs, [
        "function setImpl() {",
        "impl = newImpl;",
        "}",
        "fallback() {",
        "delegatecall(gas(), impl, 0, 0)",
        "}",
    ])
    assignments = proxy.check_assignments_outside_fallback("impl", funcs, fb, [
        "function setImpl() {",
        "impl = newImpl;",
        "}",
        "fallback() {",
        "delegatecall(gas(), impl, 0, 0)",
        "}",
    ])
    assert assignments



def test_detect_delegatecall_and_address_branches(monkeypatch):
    monkeypatch.setattr(proxy, "run_sevm_command", lambda *_a, **_k: None)
    t, m, lines = proxy.detect_delegatecall_and_address("0xabc", "http://rpc")
    assert t == "Unknown"
    assert lines is None

    monkeypatch.setattr(proxy, "run_sevm_command", lambda *_a, **_k: ["function f() {", "}"])
    t, m, lines = proxy.detect_delegatecall_and_address("0xabc", "http://rpc")
    assert t == "Not a proxy"

    base_lines = [
        "fallback() {",
        "delegatecall(gas(), impl, 0, 0)",
        "}",
    ]
    monkeypatch.setattr(proxy, "run_sevm_command", lambda *_a, **_k: base_lines)
    monkeypatch.setattr(proxy, "extract_implementation_address", lambda _line: "impl")

    monkeypatch.setattr(proxy, "trace_variable", lambda *_a, **_k: ["0x" + "a" * 40])
    t, _, _ = proxy.detect_delegatecall_and_address("0xabc", "http://rpc")
    assert t == "Forward proxy"

    monkeypatch.setattr(proxy, "trace_variable", lambda *_a, **_k: ["slotA"])
    monkeypatch.setattr(proxy, "detect_keccak256_traces", lambda _l: {"impl": "slotA"})
    monkeypatch.setattr(proxy, "detect_storage_assignments", lambda *_a, **_k: {"slotA": "impl"})
    t, _, _ = proxy.detect_delegatecall_and_address("0xabc", "http://rpc")
    assert t == "Upgradeable proxy"


def test_run_sevm_command_success_and_failure(monkeypatch):
    class _Result:
        def __init__(self, code, out, err):
            self.returncode = code
            self.stdout = out
            self.stderr = err

    monkeypatch.setattr(
        proxy.subprocess,
        "run",
        lambda *_a, **_k: _Result(0, "line1\nline2", ""),
    )
    assert proxy.run_sevm_command("0xabc", "http://rpc") == ["line1", "line2"]

    monkeypatch.setattr(
        proxy.subprocess,
        "run",
        lambda *_a, **_k: _Result(1, "", "boom"),
    )
    assert proxy.run_sevm_command("0xabc", "http://rpc") is None


def test_extract_implementation_address_returns_none_for_constants():
    assert (
        proxy.extract_implementation_address(
            "delegatecall(gas(), 0x1234 + 1, calldata, 0);"
        )
        is None
    )


def test_find_function_boundaries_handles_missing_closing_brace():
    lines = ["function x() {", "impl = v;"]
    funcs = proxy.find_function_boundaries(lines)
    first = list(funcs.values())[0]
    assert first["end"] == len(lines) - 1


def test_trace_variable_cycle_and_hardcoded_origin():
    cyclic_lines = ["a = b;", "b = a;", "delegatecall(gas(), a, 0, 0)"]
    assert proxy.trace_variable("a", cyclic_lines, 2) == ["b"]

    hardcoded_lines = [
        "impl = 0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa;",
        "delegatecall(gas(), impl, 0, 0)",
    ]
    origins = proxy.trace_variable("impl", hardcoded_lines, 1)
    assert origins == ["0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]


def test_detect_delegatecall_and_address_extra_branches(monkeypatch):
    lines = ["fallback() {", "delegatecall(gas(), impl, 0, 0)", "}"]
    monkeypatch.setattr(proxy, "run_sevm_command", lambda *_a, **_k: lines)
    monkeypatch.setattr(proxy, "extract_implementation_address", lambda _line: None)
    t, m, _ = proxy.detect_delegatecall_and_address("0xabc", "http://rpc")
    assert t == "Forward proxy"
    assert "No valid implementation assignment found" in m

    monkeypatch.setattr(proxy, "extract_implementation_address", lambda _line: "impl")
    monkeypatch.setattr(proxy, "trace_variable", lambda *_a, **_k: ["impl_state"])
    monkeypatch.setattr(proxy, "detect_keccak256_traces", lambda _l: {})
    monkeypatch.setattr(proxy, "detect_storage_assignments", lambda *_a, **_k: {})
    monkeypatch.setattr(
        proxy,
        "check_assignments_outside_fallback",
        lambda *_a, **_k: [],
    )
    t, m, _ = proxy.detect_delegatecall_and_address("0xabc", "http://rpc")
    assert t == "Forward proxy"
    assert "No assignments to impl outside the fallback function" in m

    monkeypatch.setattr(
        proxy,
        "check_assignments_outside_fallback",
        lambda *_a, **_k: [{"line_number": 1, "assignment": "impl = x;"}],
    )
    t, m, _ = proxy.detect_delegatecall_and_address("0xabc", "http://rpc")
    assert t == "Upgradeable proxy"
    assert "assigned outside the fallback function" in m


def test_save_bytecode_to_file_and_main(monkeypatch, tmp_path, capsys):
    out_file = tmp_path / "bytecode.txt"
    proxy.save_bytecode_to_file("0xdeadbeef", str(out_file))
    assert out_file.read_text() == "0xdeadbeef"

    monkeypatch.setattr(builtins, "input", lambda _p: "0xabc")
    monkeypatch.setattr(
        proxy,
        "detect_delegatecall_and_address",
        lambda _b: ("Forward proxy", "ok", []),
    )
    proxy.main()
    out = capsys.readouterr().out
    assert "Proxy Type: Forward proxy" in out
    assert "Message: ok" in out
