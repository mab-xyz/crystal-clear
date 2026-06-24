import asyncio

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.api.routers import analysis
from src.api.schemas.analysis import RawTxRiskRequest, SimulationRequest


class _CaptureEngine:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def simulate_and_check(self, call_object, **kwargs):
        self.calls.append((call_object, kwargs))
        return self.result


def _patch_interaction_helpers(
    monkeypatch,
    contract_dangerous_types=None,
    sender_dangerous_types=None,
    contract_missing_types=None,
    sender_missing_types=None,
    interaction_first_time=None,
    interaction_state=None,
):
    monkeypatch.setattr(
        analysis,
        "seed_interaction_scan_state_from_tx",
        lambda **_k: 0,
    )
    monkeypatch.setattr(
        analysis,
        "_evaluate_interaction_scan_risk",
        lambda **_k: (
            interaction_first_time or {},
            interaction_state or {},
            contract_dangerous_types or [],
            sender_dangerous_types or [],
            contract_missing_types or [],
            sender_missing_types or [],
        ),
    )


@pytest.mark.asyncio
# Verifies optional tx fields are forwarded and dangerous status derives from interaction scan.
async def test_simulate_transaction_sets_all_optional_fields(monkeypatch):
    addr = "0x3333333333333333333333333333333333333333"
    _patch_interaction_helpers(
        monkeypatch,
        contract_dangerous_types=["contract_direct"],
        interaction_first_time={addr: {"contract_direct": True}},
        interaction_state={addr: {"contract_direct": "FOUND"}},
    )
    engine = _CaptureEngine(
        {
            addr: {
                "first_time": True,
                "verification": {"verification": "unknown"},
                "depth": 1,
                "types": {"CALL": 1},
            }
        }
    )
    body = SimulationRequest(
        from_addr="0x1111111111111111111111111111111111111111",
        to_addr="0x2222222222222222222222222222222222222222",
        data="0xdeadbeef",
        value="0x1",
        gas="0x5208",
        gasPrice="0x2",
        maxFeePerGas="0x3",
        maxPriorityFeePerGas="0x4",
        tx_type="0x2",
        from_block=" 100 ",
        to_block="200",
    )

    response = await analysis.simulate_transaction(
        body,
        risk_engine=engine,
        session=object(),
    )

    call_object, kwargs = engine.calls[0]
    assert response.status == "DANGEROUS"
    assert response.danger_reason == "UNVERIFIED"
    assert call_object["gas"] == "0x5208"
    assert call_object["gasPrice"] == "0x2"
    assert call_object["maxFeePerGas"] == "0x3"
    assert call_object["maxPriorityFeePerGas"] == "0x4"
    assert call_object["type"] == "0x2"
    assert kwargs["from_block"] == " 100 "
    assert kwargs["to_block"] == "200"


@pytest.mark.asyncio
# Verified first-time contracts are also dangerous (FIRST_TIME_INTERACTION).
async def test_simulate_transaction_verified_first_time_is_dangerous(monkeypatch):
    addr = "0x3333333333333333333333333333333333333333"
    _patch_interaction_helpers(
        monkeypatch,
        contract_dangerous_types=["contract_direct"],
        interaction_first_time={addr: {"contract_direct": True}},
        interaction_state={addr: {"contract_direct": "FOUND"}},
    )
    engine = _CaptureEngine(
        {
            addr: {
                "first_time": True,
                "verification": {"verification": "verified"},
                "depth": 1,
                "types": {"CALL": 1},
            }
        }
    )
    body = SimulationRequest(
        from_addr="0x1111111111111111111111111111111111111111",
        to_addr="0x2222222222222222222222222222222222222222",
        data="0x",
    )

    response = await analysis.simulate_transaction(
        body,
        risk_engine=engine,
        session=object(),
    )

    assert response.status == "DANGEROUS"
    assert response.danger_reason == "FIRST_TIME_INTERACTION"


@pytest.mark.asyncio
# Reproduces issue #248 tx 0x2eef...: unverified MEV root contract with self-interaction
# FOUND (after the self-interaction fix) must still be DANGEROUS because the contract is
# unverified, not because it is first-time.
async def test_simulate_transaction_unverified_root_contract_is_dangerous(monkeypatch):
    # The root contract is the only touched address. After the self-interaction fix
    # its interaction_state is FOUND/not-first-time, so contract_dangerous_types and
    # contract_missing_types are both empty. Status must still be DANGEROUS because
    # the contract itself is unverified.
    root = "0x51c72848c68a965f66fa7a88855f9f7784502a7f"
    _patch_interaction_helpers(
        monkeypatch,
        # Self-interaction is FOUND/not-first-time — neither dangerous nor missing.
        contract_dangerous_types=[],
        contract_missing_types=[],
        interaction_first_time={root: {"contract_direct": False, "contract_transitive": False}},
        interaction_state={root: {"contract_direct": "FOUND", "contract_transitive": "FOUND"}},
    )
    # Checksummed address as the engine would return it.
    engine = _CaptureEngine(
        {
            "0x51C72848c68a965f66FA7a88855F9f7784502a7F": {
                "verification": {"verification": "not-verified"},
                "depth": 0,
                "types": {"CALL": 1},
            }
        }
    )
    body = SimulationRequest(
        from_addr="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        to_addr="0x51C72848c68a965f66FA7a88855F9f7784502a7F",
        data="0x",
    )

    response = await analysis.simulate_transaction(
        body,
        risk_engine=engine,
        session=object(),
    )

    # Status must be DANGEROUS because the root contract is unverified.
    assert response.status == "DANGEROUS"
    assert response.danger_reason == "UNVERIFIED"
    # The root contract must appear in the details list (contracts must not disappear).
    assert len(response.details) == 1
    assert response.details[0].address == "0x51C72848c68a965f66FA7a88855F9f7784502a7F"
    # interaction_state must show FOUND after the self-interaction fix.
    assert response.details[0].interaction_state == {
        "contract_direct": "FOUND",
        "contract_transitive": "FOUND",
    }


@pytest.mark.asyncio
# Same scenario via tx-risk-raw: unverified root contract with FOUND self-interaction
# must still produce DANGEROUS with UNVERIFIED (issue #248).
async def test_tx_risk_raw_unverified_root_contract_is_dangerous(monkeypatch):
    root = "0x51c72848c68a965f66fa7a88855f9f7784502a7f"

    class _TypedObj:
        def as_dict(self):
            return {
                "to": "0x51C72848c68a965f66FA7a88855F9f7784502a7F",
                "data": "0x",
                "type": "0x2",
            }

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            return _TypedObj()

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.Account,
        "recover_transaction",
        lambda _b: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    )
    _patch_interaction_helpers(
        monkeypatch,
        contract_dangerous_types=[],
        contract_missing_types=[],
        interaction_first_time={root: {"contract_direct": False, "contract_transitive": False}},
        interaction_state={root: {"contract_direct": "FOUND", "contract_transitive": "FOUND"}},
    )
    engine = _CaptureEngine(
        {
            "0x51C72848c68a965f66FA7a88855F9f7784502a7F": {
                "verification": {"verification": "not-verified"},
                "depth": 0,
                "types": {"CALL": 1},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x02aa"),
        risk_engine=engine,
        session=object(),
    )

    assert response.status == "DANGEROUS"
    assert response.danger_reason == "UNVERIFIED"
    assert len(response.details) == 1
    assert response.details[0].address == "0x51C72848c68a965f66FA7a88855F9f7784502a7F"
    assert response.details[0].interaction_state == {
        "contract_direct": "FOUND",
        "contract_transitive": "FOUND",
    }


@pytest.mark.asyncio
# Full call-chain scenario (issue #248): root is unverified, two further contracts are
# called during execution. All three must appear in details with correct per-contract
# interaction_state and verification. Only one unverified contract is enough to make the
# whole tx DANGEROUS/UNVERIFIED.
async def test_simulate_transaction_full_call_chain_all_contracts_present(monkeypatch):
    # Addresses as the engine would return them (checksummed).
    root  = "0x51C72848c68a965f66FA7a88855F9f7784502a7F"  # unverified MEV bot
    addr_b = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # verified, MISSING history
    addr_c = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"  # verified, FOUND/not-first-time

    root_n  = root.lower()
    addr_b_n = addr_b.lower()
    addr_c_n = addr_c.lower()

    _patch_interaction_helpers(
        monkeypatch,
        contract_dangerous_types=[],
        contract_missing_types=["contract_direct", "contract_transitive"],
        interaction_first_time={
            root_n:   {"contract_direct": False, "contract_transitive": False},
            addr_b_n: {"contract_direct": True,  "contract_transitive": True},
            addr_c_n: {"contract_direct": False, "contract_transitive": False},
        },
        interaction_state={
            root_n:   {"contract_direct": "FOUND",   "contract_transitive": "FOUND"},
            addr_b_n: {"contract_direct": "MISSING", "contract_transitive": "MISSING"},
            addr_c_n: {"contract_direct": "FOUND",   "contract_transitive": "FOUND"},
        },
    )
    engine = _CaptureEngine(
        {
            root: {
                "verification": {"verification": "not-verified"},
                "depth": 0,
                "types": {"CALL": 1},
            },
            addr_b: {
                "verification": {"verification": "verified"},
                "depth": 1,
                "types": {"CALL": 1},
            },
            addr_c: {
                "verification": {"verification": "verified"},
                "depth": 1,
                "types": {"STATICCALL": 2},
            },
        }
    )
    body = SimulationRequest(
        from_addr="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        to_addr=root,
        data="0x",
    )

    response = await analysis.simulate_transaction(
        body,
        risk_engine=engine,
        session=object(),
    )

    # Unverified root contract drives the overall status.
    assert response.status == "DANGEROUS"
    assert response.danger_reason == "UNVERIFIED"

    # All three contracts from the call chain must be present.
    assert len(response.details) == 3
    by_addr = {item.address: item for item in response.details}
    assert root   in by_addr, "root contract missing from details"
    assert addr_b in by_addr, "addr_b missing from details"
    assert addr_c in by_addr, "addr_c missing from details"

    # Root: self-interaction → FOUND, not first-time, unverified.
    assert by_addr[root].interaction_state == {
        "contract_direct": "FOUND",
        "contract_transitive": "FOUND",
    }
    assert by_addr[root].first_time is False
    assert by_addr[root].verification == {"verification": "not-verified"}

    # addr_b: no scan history → MISSING, first-time True, but verified.
    assert by_addr[addr_b].interaction_state == {
        "contract_direct": "MISSING",
        "contract_transitive": "MISSING",
    }
    assert by_addr[addr_b].first_time is True
    assert by_addr[addr_b].verification == {"verification": "verified"}

    # addr_c: known contract, not first-time, verified.
    assert by_addr[addr_c].interaction_state == {
        "contract_direct": "FOUND",
        "contract_transitive": "FOUND",
    }
    assert by_addr[addr_c].first_time is False
    assert by_addr[addr_c].verification == {"verification": "verified"}


@pytest.mark.asyncio
# Sender-side first-time interactions should mark interaction_status as dangerous without flipping overall status.
async def test_simulate_transaction_marks_sender_dangerous_in_status(monkeypatch):
    _patch_interaction_helpers(
        monkeypatch,
        sender_dangerous_types=["sender_direct"],
    )
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
                "depth": 0,
                "types": {"CALL": 1},
            }
        }
    )
    body = SimulationRequest(
        from_addr="0x1111111111111111111111111111111111111111",
        to_addr="0x2222222222222222222222222222222222222222",
        data="0x",
        interaction_types=["sender_direct"],
    )

    response = await analysis.simulate_transaction(
        body,
        risk_engine=engine,
        session=object(),
    )

    assert response.status == "OK"
    assert response.interaction_status["sender_direct"] == "dangerous"
    assert response.interaction_status["contract_direct"] == "not_checked"


@pytest.mark.asyncio
# Exercises typed-transaction decode path and call-object construction.
async def test_tx_risk_raw_uses_typed_transaction_decode(monkeypatch):
    _patch_interaction_helpers(monkeypatch)
    class _TypedObj:
        def as_dict(self):
            return {
                "to": "0x2222222222222222222222222222222222222222",
                "data": "0xdeadbeef",
                "value": 1,
                "gas": 21000,
                "gasPrice": 2,
                "type": "0x2",
            }

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            return _TypedObj()

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.Account, "recover_transaction", lambda _b: "0x" + "1" * 40
    )
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "fully-verified"},
            }
        }
    )

    body = RawTxRiskRequest(raw_tx="0x02aa", from_block=" ", to_block="10")
    response = await analysis.get_tx_risk_from_raw(
        body, risk_engine=engine, session=object()
    )

    call_object, kwargs = engine.calls[0]
    assert response.status == "OK"
    assert call_object["from"] == "0x" + "1" * 40
    assert call_object["to"] == "0x2222222222222222222222222222222222222222"
    assert call_object["data"] == "0xdeadbeef"
    assert call_object["type"] == "0x2"
    assert kwargs["from_block"] is None
    assert kwargs["to_block"] == "10"


@pytest.mark.asyncio
# Maps Type-1 RLP decode failure into HTTP 422 decode error.
async def test_tx_risk_raw_type1_rlp_decode_error(monkeypatch):
    _patch_interaction_helpers(monkeypatch)
    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.rlp,
        "decode",
        lambda _b: (_ for _ in ()).throw(RuntimeError("decode error")),
    )

    with pytest.raises(HTTPException) as exc:
        await analysis.get_tx_risk_from_raw(
            RawTxRiskRequest(raw_tx="0x01aa"),
            risk_engine=_CaptureEngine({}),
            session=object(),
        )

    assert exc.value.status_code == 422
    assert "RLP decode failed for Type 1 payload" in exc.value.detail


@pytest.mark.asyncio
async def test_tx_risk_raw_uses_numeric_block_tag_as_default_to_block(monkeypatch):
    _patch_interaction_helpers(monkeypatch)

    class _TypedObj:
        def as_dict(self):
            return {
                "type": 2,
                "to": bytes.fromhex("22" * 20),
                "data": b"\xde\xad\xbe\xef",
                "value": 0,
                "gas": 21000,
            }

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            return _TypedObj()

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.Account, "recover_transaction", lambda _b: "0x" + "1" * 40
    )
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x02aa", block_tag="12345"),
        risk_engine=engine,
        session=object(),
    )

    _call_object, kwargs = engine.calls[0]
    assert response.status == "OK"
    assert kwargs["to_block"] == "12345"


@pytest.mark.asyncio
async def test_tx_risk_raw_keeps_explicit_to_block_over_block_tag(monkeypatch):
    _patch_interaction_helpers(monkeypatch)

    class _TypedObj:
        def as_dict(self):
            return {
                "type": 2,
                "to": bytes.fromhex("22" * 20),
                "data": b"\xde\xad\xbe\xef",
                "value": 0,
                "gas": 21000,
            }

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            return _TypedObj()

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.Account, "recover_transaction", lambda _b: "0x" + "1" * 40
    )
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x02aa", block_tag="12345", to_block="999"),
        risk_engine=engine,
        session=object(),
    )

    _call_object, kwargs = engine.calls[0]
    assert kwargs["to_block"] == "999"


@pytest.mark.asyncio
# Covers signed Type-1 fallback decode and downstream response validation error case.
async def test_tx_risk_raw_type1_signed_rlp_branch(monkeypatch):
    _patch_interaction_helpers(monkeypatch)
    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.rlp,
        "decode",
        lambda _b: [
            b"\x00",
            b"\x00",
            b"\x05",
            b"\x52\x08",
            b"\x11" * 20,
            b"\x01",
            b"\xab\xcd",
            b"",
            b"",
            b"",
            b"",
            b"",
        ],
    )
    monkeypatch.setattr(
        analysis.Account, "recover_transaction", lambda _b: "0x" + "2" * 40
    )
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": "not-a-dict",
            }
        }
    )

    with pytest.raises(ValidationError):
        await analysis.get_tx_risk_from_raw(
            RawTxRiskRequest(raw_tx="0x01aa"),
            risk_engine=engine,
            session=object(),
        )
    call_object, _kwargs = engine.calls[0]
    assert call_object["from"] == "0x" + "2" * 40
    assert call_object["to"] == "0x" + ("11" * 20)
    assert call_object["data"] == "0xabcd"
    assert call_object["gas"] == hex(int.from_bytes(b"\x52\x08", "big"))
    assert call_object["gasPrice"] == "0x5"
    assert call_object["type"] == "0x1"


@pytest.mark.asyncio
# Covers unsigned Type-2 fallback that relies on provided sender address.
async def test_tx_risk_raw_type2_unsigned_with_sender(monkeypatch):
    _patch_interaction_helpers(monkeypatch)
    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(analysis.rlp, "decode", lambda _b: [b""] * 8)
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(
            raw_tx="0x02aa",
            sender_address="0x" + "3" * 40,
            from_block=" 123 ",
            to_block="",
        ),
        risk_engine=engine,
        session=object(),
    )

    call_object, kwargs = engine.calls[0]
    assert response.status == "OK"
    assert call_object["from"] == "0x" + "3" * 40
    assert call_object["type"] == "0x2"
    assert kwargs["from_block"] == "123"
    assert kwargs["to_block"] is None


@pytest.mark.asyncio
# Covers signed Type-2 fallback decode and EIP-1559 fee mapping.
async def test_tx_risk_raw_type2_signed_rlp_branch(monkeypatch):
    _patch_interaction_helpers(monkeypatch)
    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.rlp,
        "decode",
        lambda _b: [
            b"\x00",
            b"\x00",
            b"\x02",
            b"\x03",
            b"\x52\x08",
            b"\x22" * 20,
            b"\x04",
            b"\xfe\xed",
            b"",
            b"",
            b"",
            b"",
        ],
    )
    monkeypatch.setattr(
        analysis.Account, "recover_transaction", lambda _b: "0x" + "4" * 40
    )
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x02aa"),
        risk_engine=engine,
        session=object(),
    )

    call_object, _kwargs = engine.calls[0]
    assert response.status == "OK"
    assert call_object["from"] == "0x" + "4" * 40
    assert call_object["to"] == "0x" + ("22" * 20)
    assert call_object["data"] == "0xfeed"
    assert call_object["maxPriorityFeePerGas"] == "0x2"
    assert call_object["maxFeePerGas"] == "0x3"
    assert call_object["type"] == "0x2"


@pytest.mark.asyncio
# Covers legacy fallback with unexpected RLP length but explicit sender supplied.
async def test_tx_risk_raw_legacy_invalid_length_with_sender(monkeypatch):
    _patch_interaction_helpers(monkeypatch)
    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(analysis.rlp, "decode", lambda _b: [b""] * 7)
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x80aa", sender_address="0x" + "5" * 40),
        risk_engine=engine,
        session=object(),
    )

    call_object, _kwargs = engine.calls[0]
    assert response.status == "OK"
    assert call_object["from"] == "0x" + "5" * 40
    assert call_object["type"] == "0x0"


@pytest.mark.asyncio
# Covers Type-1 fallback with unexpected length and sender override path.
async def test_tx_risk_raw_type1_unexpected_length_with_sender(monkeypatch):
    _patch_interaction_helpers(monkeypatch)

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(analysis.rlp, "decode", lambda _b: [b""] * 7)
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x01aa", sender_address="0x" + "6" * 40),
        risk_engine=engine,
        session=object(),
    )
    assert response.status == "OK"
    call_object, _kwargs = engine.calls[0]
    assert call_object["type"] == "0x1"


@pytest.mark.asyncio
# Maps legacy RLP decode failure into HTTP 422 decode error.
async def test_tx_risk_raw_legacy_decode_failure(monkeypatch):
    _patch_interaction_helpers(monkeypatch)

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.rlp,
        "decode",
        lambda _b: (_ for _ in ()).throw(RuntimeError("legacy decode fail")),
    )

    with pytest.raises(HTTPException) as exc:
        await analysis.get_tx_risk_from_raw(
            RawTxRiskRequest(raw_tx="0x80aa"),
            risk_engine=_CaptureEngine({}),
            session=object(),
        )
    assert exc.value.status_code == 422
    assert "RLP decode failed for Legacy transaction" in exc.value.detail


@pytest.mark.asyncio
# Covers signed legacy decode branch and legacy call-object field conversions.
async def test_tx_risk_raw_legacy_signed_branch(monkeypatch):
    _patch_interaction_helpers(monkeypatch)

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.rlp,
        "decode",
        lambda _b: [
            b"\x01",
            b"\x02",
            b"\x52\x08",
            b"\x33" * 20,
            b"\x04",
            b"\xde\xad",
            b"",
            b"",
            b"",
        ],
    )
    monkeypatch.setattr(
        analysis.Account, "recover_transaction", lambda _b: "0x" + "7" * 40
    )
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x80aa"),
        risk_engine=engine,
        session=object(),
    )

    assert response.status == "OK"
    call_object, _kwargs = engine.calls[0]
    assert call_object["from"] == "0x" + "7" * 40
    assert call_object["to"] == "0x" + ("33" * 20)
    assert call_object["gas"] == hex(int.from_bytes(b"\x52\x08", "big"))
    assert call_object["gasPrice"] == "0x2"
    assert call_object["type"] == "0x0"


@pytest.mark.asyncio
# When sender_address is provided, it takes precedence over signature recovery.
async def test_tx_risk_raw_prefers_explicit_sender_over_signature(monkeypatch):
    _patch_interaction_helpers(monkeypatch)

    class _TypedObj:
        def as_dict(self):
            return {
                "to": "0x" + ("22" * 20),
                "data": "0x",
                "type": "0x2",
            }

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            return _TypedObj()

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.Account, "recover_transaction", lambda _b: "0x" + "9" * 40
    )
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(
            raw_tx="0x02aa",
            sender_address="0x" + "8" * 40,
        ),
        risk_engine=engine,
        session=object(),
    )

    assert response.status == "OK"
    call_object, _kwargs = engine.calls[0]
    assert call_object["from"] == "0x" + "8" * 40


@pytest.mark.asyncio
# Regression: plain ETH transfer to an EOA must not be flagged DANGEROUS.
# The simulation returns no contract interactions (empty results) because the
# target has no bytecode, so there is nothing to verify.
async def test_simulate_transaction_eoa_target_is_ok(monkeypatch):
    _patch_interaction_helpers(monkeypatch)
    engine = _CaptureEngine({})  # no contract interactions — target is an EOA

    body = SimulationRequest(
        from_addr="0x1111111111111111111111111111111111111111",
        to_addr="0x2222222222222222222222222222222222222222",
        data="0x",
    )

    response = await analysis.simulate_transaction(
        body,
        risk_engine=engine,
        session=object(),
    )

    assert response.status == "OK"
    assert response.danger_reason is None
    assert response.ok_reason == "to EOA"
    assert response.details == []


# Allowlisted contracts are OK when no first-time or missing-history signal exists.
def test_simulate_transaction_allowlisted_contract_sets_ok_reason(monkeypatch):
    addr = "0x3333333333333333333333333333333333333333"
    _patch_interaction_helpers(
        monkeypatch,
        interaction_first_time={addr: {"contract_direct": False}},
        interaction_state={addr: {"contract_direct": "FOUND"}},
    )
    engine = _CaptureEngine(
        {
            addr: {
                "first_time": False,
                "verification": {"verification": "allowlisted"},
                "depth": 0,
                "types": {"CALL": 1},
            }
        }
    )
    body = SimulationRequest(
        from_addr="0x1111111111111111111111111111111111111111",
        to_addr=addr,
        data="0x",
    )

    response = asyncio.run(
        analysis.simulate_transaction(
            body,
            risk_engine=engine,
            session=object(),
        )
    )

    assert response.status == "OK"
    assert response.danger_reason is None
    assert response.ok_reason == "allowlist"


def test_allowlisted_and_unverified_supply_chain_is_dangerous(monkeypatch):
    allowlisted = "0x3333333333333333333333333333333333333333"
    unverified = "0x4444444444444444444444444444444444444444"
    _patch_interaction_helpers(
        monkeypatch,
        interaction_first_time={
            allowlisted: {"contract_direct": False},
            unverified: {"contract_transitive": False},
        },
        interaction_state={
            allowlisted: {"contract_direct": "FOUND"},
            unverified: {"contract_transitive": "FOUND"},
        },
    )
    engine = _CaptureEngine(
        {
            allowlisted: {
                "first_time": False,
                "verification": {"verification": "allowlisted"},
                "depth": 0,
                "types": {"CALL": 1},
            },
            unverified: {
                "first_time": False,
                "verification": {"verification": "not-verified"},
                "depth": 1,
                "types": {"DELEGATECALL": 1},
            },
        }
    )
    body = SimulationRequest(
        from_addr="0x1111111111111111111111111111111111111111",
        to_addr=allowlisted,
        data="0x",
    )

    response = asyncio.run(
        analysis.simulate_transaction(
            body,
            risk_engine=engine,
            session=object(),
        )
    )

    assert response.status == "DANGEROUS"
    assert response.danger_reason == "UNVERIFIED"
    assert response.ok_reason is None


@pytest.mark.asyncio
# Same regression via tx-risk-raw: plain ETH transfer to an EOA must be OK.
async def test_tx_risk_raw_eoa_target_is_ok(monkeypatch):
    class _TypedObj:
        def as_dict(self):
            return {
                "to": "0x2222222222222222222222222222222222222222",
                "data": "0x",
                "type": "0x2",
            }

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            return _TypedObj()

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.Account,
        "recover_transaction",
        lambda _b: "0x1111111111111111111111111111111111111111",
    )
    _patch_interaction_helpers(monkeypatch)
    engine = _CaptureEngine({})  # no contract interactions — target is an EOA

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x02aa"),
        risk_engine=engine,
        session=object(),
    )

    assert response.status == "OK"
    assert response.danger_reason is None
    assert response.ok_reason == "to EOA"
    assert response.details == []


# Same allowlist OK reason via tx-risk-raw.
def test_tx_risk_raw_allowlisted_contract_sets_ok_reason(monkeypatch):
    addr = "0x3333333333333333333333333333333333333333"

    class _TypedObj:
        def as_dict(self):
            return {
                "to": addr,
                "data": "0x",
                "type": "0x2",
            }

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            return _TypedObj()

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.Account,
        "recover_transaction",
        lambda _b: "0x1111111111111111111111111111111111111111",
    )
    _patch_interaction_helpers(
        monkeypatch,
        interaction_first_time={addr: {"contract_direct": False}},
        interaction_state={addr: {"contract_direct": "FOUND"}},
    )
    engine = _CaptureEngine(
        {
            addr: {
                "first_time": False,
                "verification": {"verification": "allowlisted"},
                "depth": 0,
                "types": {"CALL": 1},
            }
        }
    )

    response = asyncio.run(
        analysis.get_tx_risk_from_raw(
            RawTxRiskRequest(raw_tx="0x02aa"),
            risk_engine=engine,
            session=object(),
        )
    )

    assert response.status == "OK"
    assert response.danger_reason is None
    assert response.ok_reason == "allowlist"


@pytest.mark.asyncio
# Ensures seed failures are logged/swallowed and both endpoints still return responses.
async def test_seed_failures_are_swallowed_in_both_endpoints(monkeypatch):
    class _TypedObj:
        def as_dict(self):
            return {"to": "0x2222222222222222222222222222222222222222", "type": "0x2"}

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            return _TypedObj()

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    monkeypatch.setattr(
        analysis.Account, "recover_transaction", lambda _b: "0x" + "1" * 40
    )
    monkeypatch.setattr(
        analysis,
        "seed_interaction_scan_state_from_tx",
        lambda **_k: (_ for _ in ()).throw(RuntimeError("seed boom")),
    )
    monkeypatch.setattr(
        analysis,
        "_evaluate_interaction_scan_risk",
        lambda **_k: ({}, {}, [], [], [], []),
    )

    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    sim_resp = await analysis.simulate_transaction(
        SimulationRequest(
            from_addr="0x1111111111111111111111111111111111111111",
            to_addr="0x2222222222222222222222222222222222222222",
            data="0x",
        ),
        risk_engine=engine,
        session=object(),
    )
    raw_resp = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x02aa"),
        risk_engine=engine,
        session=object(),
    )

    assert sim_resp.status == "OK"
    assert raw_resp.status == "OK"


@pytest.mark.asyncio
# Unsigned Type-2 (9 RLP elements) without sender_address → zero address used as sender.
async def test_tx_risk_raw_unsigned_type2_no_sender_uses_zero_address(monkeypatch):
    _patch_interaction_helpers(monkeypatch)

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    # 9 elements = unsigned EIP-1559 layout: chainId nonce maxPrio maxFee gas to value data accessList
    monkeypatch.setattr(
        analysis.rlp,
        "decode",
        lambda _b: [b"", b"", b"\x01", b"\x02", b"\x52\x08", b"\x33" * 20, b"", b"\xca\xfe", []],
    )
    engine = _CaptureEngine(
        {
            "0x3333333333333333333333333333333333333333": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x02aa"),
        risk_engine=engine,
        session=object(),
    )

    call_object, _kwargs = engine.calls[0]
    assert response.status == "OK"
    assert call_object["from"] == "0x0000000000000000000000000000000000000000"
    assert call_object["type"] == "0x2"


@pytest.mark.asyncio
# Unsigned Type-1 (8 RLP elements) without sender_address → zero address used as sender.
async def test_tx_risk_raw_unsigned_type1_no_sender_uses_zero_address(monkeypatch):
    _patch_interaction_helpers(monkeypatch)

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    # 8 elements = unsigned EIP-2930 layout: chainId nonce gasPrice gas to value data accessList
    monkeypatch.setattr(
        analysis.rlp,
        "decode",
        lambda _b: [b"", b"", b"\x05", b"\x52\x08", b"\x44" * 20, b"", b"\xbe\xef", []],
    )
    engine = _CaptureEngine(
        {
            "0x4444444444444444444444444444444444444444": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x01aa"),
        risk_engine=engine,
        session=object(),
    )

    call_object, _kwargs = engine.calls[0]
    assert response.status == "OK"
    assert call_object["from"] == "0x0000000000000000000000000000000000000000"
    assert call_object["type"] == "0x1"


@pytest.mark.asyncio
# Unsigned legacy (6 RLP elements) without sender_address → zero address used as sender.
async def test_tx_risk_raw_unsigned_legacy_no_sender_uses_zero_address(monkeypatch):
    _patch_interaction_helpers(monkeypatch)

    class _Typed:
        @staticmethod
        def from_bytes(_b):
            raise RuntimeError("typed fail")

    monkeypatch.setattr(analysis, "TypedTransaction", _Typed)
    # 6 elements = unsigned legacy layout: nonce gasPrice gas to value data
    monkeypatch.setattr(
        analysis.rlp,
        "decode",
        lambda _b: [b"", b"\x03", b"\x52\x08", b"\x55" * 20, b"", b"\xde\xad"],
    )
    engine = _CaptureEngine(
        {
            "0x5555555555555555555555555555555555555555": {
                "first_time": False,
                "verification": {"verification": "verified"},
            }
        }
    )

    response = await analysis.get_tx_risk_from_raw(
        RawTxRiskRequest(raw_tx="0x80aa"),
        risk_engine=engine,
        session=object(),
    )

    call_object, _kwargs = engine.calls[0]
    assert response.status == "OK"
    assert call_object["from"] == "0x0000000000000000000000000000000000000000"
    assert call_object["type"] == "0x0"
