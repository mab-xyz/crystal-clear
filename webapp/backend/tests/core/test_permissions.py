import pytest

from src.api.core import permissions


class _Var:
    def __init__(self, name, type_="address"):
        self.name = name
        self.type = type_


class _ReadVar:
    def __init__(self, name):
        self.name = name


class _Node:
    def __init__(self, expr, has_if=True, has_req=False, solidity_read=None, vars_read=None):
        self.expression = expr
        self._has_if = has_if
        self._has_req = has_req
        self.solidity_variables_read = solidity_read or []
        self.variables_read = vars_read or []

    def contains_if(self):
        return self._has_if

    def contains_require_or_assert(self):
        return self._has_req


class _Call:
    def __init__(self, function):
        self.function = function


class _Fn:
    def __init__(self, name, nodes=None, modifiers=None, internal_calls=None, writes=None):
        self.name = name
        self.nodes = nodes or []
        self.modifiers = modifiers or []
        self._internal = internal_calls or []
        self._writes = writes or []

    def all_internal_calls(self):
        return self._internal

    def all_state_variables_written(self):
        return self._writes


class _Contract:
    def __init__(self, inheritance, writes, functions):
        self._inheritance = inheritance
        self.all_state_variables_written = writes
        self.functions = functions


class _Slither:
    def __init__(self, *_a, **_k):
        pass

    def get_contract_from_name(self, _name):
        sv_owner = _Var("owner", "address")
        cond_node = _Node(
            "require(msg.sender == owner)",
            has_if=False,
            has_req=True,
            solidity_read=[_ReadVar("msg.sender")],
            vars_read=[_ReadVar("owner")],
        )
        fn = _Fn(
            "setOwner",
            nodes=[cond_node],
            internal_calls=[],
            modifiers=[],
            writes=[_Var("owner", "address")],
        )
        parent = type("Parent", (), {"all_state_variables_written": [sv_owner]})()
        contract = _Contract(inheritance=[parent], writes=[sv_owner], functions=[fn])
        return [contract]


def test_get_msg_sender_checks_and_owner_condition(monkeypatch):
    monkeypatch.setattr(permissions, "Function", _Fn)

    node = _Node(
        "if (msg.sender == owner)",
        has_if=True,
        has_req=False,
        solidity_read=[_ReadVar("msg.sender")],
        vars_read=[_ReadVar("owner")],
    )
    fn = _Fn("f", nodes=[node], modifiers=[], internal_calls=[])

    checks = permissions.get_msg_sender_checks(fn)
    assert len(checks) == 1
    assert permissions.check_onwer_condition(checks, [_Var("owner", "address")]) is True


def test_detect_permissions_and_get_permissions(monkeypatch):
    monkeypatch.setattr(permissions, "Function", _Fn)
    monkeypatch.setattr(permissions, "Slither", _Slither)

    detected = permissions.detect_permissions("0xabc", "Main")
    assert detected and detected[0]["function"] == "setOwner"

    monkeypatch.setattr(
        permissions,
        "get_contract_sourcecode",
        lambda *_a, **_k: {"result": [{"ContractName": "Main"}]},
    )
    monkeypatch.setattr(permissions, "detect_permissions", lambda *_a, **_k: [{"function": "setOwner"}])

    out = permissions.get_permissions("0xabc")
    assert out == [{"function": "setOwner"}]


def test_get_contract_sourcecode_status_and_get_permissions_errors(monkeypatch):
    class _Resp:
        def __init__(self, status_code):
            self.status_code = status_code

        @staticmethod
        def json():
            return {"ok": True}

    monkeypatch.setattr(permissions.requests, "get", lambda *_a, **_k: _Resp(200))
    assert permissions.get_contract_sourcecode("0xabc", "k")["ok"] is True

    monkeypatch.setattr(permissions.requests, "get", lambda *_a, **_k: _Resp(500))
    with pytest.raises(Exception):
        permissions.get_contract_sourcecode("0xabc", "k")

    monkeypatch.setattr(permissions, "get_contract_sourcecode", lambda *_a, **_k: {"result": []})
    with pytest.raises(ValueError):
        permissions.get_permissions("0xabc")

    monkeypatch.setattr(permissions, "get_contract_sourcecode", lambda *_a, **_k: {"result": [{"ContractName": "Main"}]})
    monkeypatch.setattr(permissions, "detect_permissions", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        permissions.get_permissions("0xabc")
