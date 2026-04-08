from types import SimpleNamespace

from src.api.routers import analysis


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Session:
    def __init__(self, rows, skipped_rows=None):
        # First exec() returns InteractionScanState rows; subsequent exec()
        # calls (e.g. the contract_direct skipped-range lookup) return
        # `skipped_rows`. Defaults to [] so existing tests are unaffected.
        self._rows = rows
        self._skipped_rows = skipped_rows or []
        self._call = 0

    def exec(self, _stmt):
        self._call += 1
        if self._call == 1:
            return _Rows(self._rows)
        return _Rows(self._skipped_rows)


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
        contract_missing,
        sender_missing,
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
    assert contract_missing == []
    assert sender_missing == []


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
        contract_missing,
        sender_missing,
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
    # MISSING dangerous types now go to the "missing" buckets, not "dangerous".
    assert contract_dangerous == []
    assert sender_dangerous == []
    assert contract_missing == ["contract_direct"]
    assert sender_missing == []


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
        contract_missing,
        sender_missing,
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
    assert contract_missing == []
    assert sender_missing == []


def test_evaluate_interaction_scan_risk_marks_sender_first_time():
    sender = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    target = "0xcccccccccccccccccccccccccccccccccccccccc"
    session = _Session([])

    (
        first_map,
        state_map,
        contract_dangerous,
        sender_dangerous,
        contract_missing,
        sender_missing,
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
    # MISSING sender types now flow to sender_missing instead of sender_dangerous.
    assert sender_dangerous == []
    assert contract_dangerous == []
    assert sender_missing == ["sender_direct", "sender_transitive"]
    assert contract_missing == []


# A contract's interaction_state with itself should always be FOUND (not first-time).
def test_evaluate_interaction_scan_risk_self_interaction_is_always_found():
    root = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    # root is also included in touched_addresses (the target of the tx is always touched)
    session = _Session([])

    (
        first_map,
        state_map,
        contract_dangerous,
        sender_dangerous,
        contract_missing,
        sender_missing,
    ) = analysis._evaluate_interaction_scan_risk(
        session=session,
        sender_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        root_contract=root,
        touched_addresses=[root],
        checked_interaction_types=["contract_direct", "contract_transitive"],
    )

    # Self-interaction must never be flagged as first-time or missing.
    assert first_map[root]["contract_direct"] is False
    assert state_map[root]["contract_direct"] == "FOUND"
    assert first_map[root]["contract_transitive"] is False
    assert state_map[root]["contract_transitive"] == "FOUND"
    assert contract_dangerous == []
    assert contract_missing == []


# When contract_direct would otherwise be flagged as first-time (row recorded
# with first_time_interact=True), a matching entry in the skipped-range table
# means the scanner gave up on some block range and interactions likely
# existed — so the status must be downgraded to FOUND/not-first-time.
def test_evaluate_interaction_scan_risk_contract_direct_skipped_overrides_first_time():
    sender = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    root = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    target = "0xcccccccccccccccccccccccccccccccccccccccc"
    row_first_time = SimpleNamespace(
        from_address=root,
        to_address=target,
        interaction_type="contract_direct",
        first_time_interact=True,
    )
    skipped = SimpleNamespace(
        from_address=root,
        to_address=target,
        interaction_type="contract_direct",
    )
    session = _Session([row_first_time], skipped_rows=[skipped])

    (
        first_map,
        state_map,
        contract_dangerous,
        sender_dangerous,
        contract_missing,
        sender_missing,
    ) = analysis._evaluate_interaction_scan_risk(
        session=session,
        sender_address=sender,
        root_contract=root,
        touched_addresses=[target],
        checked_interaction_types=["contract_direct"],
    )

    # Skipped-range override: no longer first-time, no longer dangerous.
    assert first_map[target]["contract_direct"] is False
    assert state_map[target]["contract_direct"] == "FOUND"
    assert contract_dangerous == []
    assert contract_missing == []


# Without a skipped-range entry, a contract_direct first-time row remains
# dangerous — guards against the override firing unconditionally.
def test_evaluate_interaction_scan_risk_contract_direct_first_time_without_skip():
    sender = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    root = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    target = "0xcccccccccccccccccccccccccccccccccccccccc"
    row_first_time = SimpleNamespace(
        from_address=root,
        to_address=target,
        interaction_type="contract_direct",
        first_time_interact=True,
    )
    session = _Session([row_first_time])

    (
        first_map,
        state_map,
        contract_dangerous,
        _sender_dangerous,
        contract_missing,
        _sender_missing,
    ) = analysis._evaluate_interaction_scan_risk(
        session=session,
        sender_address=sender,
        root_contract=root,
        touched_addresses=[target],
        checked_interaction_types=["contract_direct"],
    )

    assert first_map[target]["contract_direct"] is True
    assert state_map[target]["contract_direct"] == "FOUND"
    assert contract_dangerous == ["contract_direct"]
    assert contract_missing == []
