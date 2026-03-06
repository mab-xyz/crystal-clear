from types import SimpleNamespace

from src.api.routers import analysis


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    def __init__(self, rows):
        self._rows = rows

    def exec(self, _stmt):
        return _Rows(self._rows)


# Verifies address normalization and interaction-type resolution with dedupe/filtering.
def test_normalize_address_and_resolve_checked_types():
    assert analysis._normalize_address(None) is None
    assert analysis._normalize_address("abc") is None
    assert (
        analysis._normalize_address(" 0xABC ")
        == "0xabc"
    )

    resolved = analysis._resolve_checked_interaction_types(
        ["sender_direct", "sender_direct", "contract_direct"],
        root_contract=None,
    )
    assert resolved == ["sender_direct"]


def test_resolve_checked_types_default_contract_when_not_provided():
    root = "0x1111111111111111111111111111111111111111"
    resolved = analysis._resolve_checked_interaction_types(
        None,
        root_contract=root,
    )
    assert resolved == ["contract_direct", "contract_transitive"]


def test_resolve_checked_types_default_drops_contract_without_root():
    resolved = analysis._resolve_checked_interaction_types(
        None,
        root_contract=None,
    )
    assert resolved == []


# Returns empty maps when required risk-evaluation inputs are invalid/missing.
def test_evaluate_interaction_scan_risk_empty_inputs_short_circuit():
    (
        first_map,
        state_map,
        contract_dangerous,
        sender_dangerous,
    ) = analysis._evaluate_interaction_scan_risk(
        session=_Session([]),
        sender_address="bad-address",
        root_contract=None,
        touched_addresses=["0x1111111111111111111111111111111111111111"],
        checked_interaction_types=["sender_direct"],
    )
    assert first_map == {}
    assert state_map == {}
    assert contract_dangerous == []
    assert sender_dangerous == []


# Builds FOUND/MISSING state maps and dangerous types from scan-state rows.
def test_evaluate_interaction_scan_risk_found_and_missing_rows():
    sender = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    root = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    target = "0xcccccccccccccccccccccccccccccccccccccccc"
    row_found = SimpleNamespace(
        from_address=sender,
        to_address=target,
        interaction_type="sender_direct",
        first_time_interact=False,
    )
    session = _Session([row_found])

    (
        first_map,
        state_map,
        contract_dangerous,
        sender_dangerous,
    ) = analysis._evaluate_interaction_scan_risk(
        session=session,
        sender_address=sender.upper(),
        root_contract=root.upper(),
        touched_addresses=[target.upper(), target.upper()],
        checked_interaction_types=["sender_direct", "contract_direct"],
    )

    assert first_map[target]["sender_direct"] is False
    assert state_map[target]["sender_direct"] == "FOUND"
    assert first_map[target]["contract_direct"] is True
    assert state_map[target]["contract_direct"] == "MISSING"
    assert contract_dangerous == ["contract_direct"]
    assert sender_dangerous == []


# Maps checked vs dangerous interaction types into response status fields.
def test_build_interaction_status_marks_unchecked_and_dangerous():
    status = analysis._build_interaction_status(
        ["sender_direct", "contract_direct"],
        ["contract_direct"],
    )
    assert status["sender_direct"] == "ok"
    assert status["contract_direct"] == "dangerous"
    assert status["sender_transitive"] == "not_checked"
    assert status["contract_transitive"] == "not_checked"


def test_build_interaction_status_marks_sender_types_when_requested():
    status = analysis._build_interaction_status(
        ["sender_direct", "sender_transitive"],
        ["sender_transitive"],
    )
    assert status["sender_direct"] == "ok"
    assert status["sender_transitive"] == "dangerous"


# Skips contract_* interaction checks when no root contract is provided.
def test_evaluate_interaction_scan_risk_skips_contract_type_without_root():
    sender = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    target = "0xcccccccccccccccccccccccccccccccccccccccc"
    (
        first_map,
        state_map,
        contract_dangerous,
        sender_dangerous,
    ) = analysis._evaluate_interaction_scan_risk(
        session=_Session([]),
        sender_address=sender,
        root_contract=None,
        touched_addresses=[target],
        checked_interaction_types=["contract_direct"],
    )
    assert first_map[target] == {}
    assert state_map[target] == {}
    assert contract_dangerous == []
    assert sender_dangerous == []


def test_evaluate_interaction_scan_risk_marks_sender_first_time():
    sender = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    target = "0xcccccccccccccccccccccccccccccccccccccccc"
    session = _Session([])

    (
        first_map,
        state_map,
        contract_dangerous,
        sender_dangerous,
    ) = analysis._evaluate_interaction_scan_risk(
        session=session,
        sender_address=sender,
        root_contract="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        touched_addresses=[target],
        checked_interaction_types=[
            "sender_direct",
            "sender_transitive",
        ],
    )

    assert first_map[target]["sender_direct"] is True
    assert state_map[target]["sender_direct"] == "MISSING"
    assert sender_dangerous == ["sender_direct", "sender_transitive"]
    assert contract_dangerous == []
