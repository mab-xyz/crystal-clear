from sqlmodel import select

from src.api.models.interaction_scan_state import InteractionScanState
from src.api.services.interaction_scan_seed import (
    seed_interaction_scan_state_from_tx,
)


def test_seed_interaction_scan_state_from_tx_inserts_expected_rows(session):
    inserted = seed_interaction_scan_state_from_tx(
        session=session,
        sender_address="0x1111111111111111111111111111111111111111",
        root_contract="0x2222222222222222222222222222222222222222",
        touched_addresses=[
            "0x2222222222222222222222222222222222222222",
            "0x3333333333333333333333333333333333333333",
        ],
    )

    # sender->{root,c2} x2 types + root->c2 x2 types
    assert inserted == 6
    rows = session.exec(select(InteractionScanState)).all()
    assert len(rows) == 6


def test_seed_interaction_scan_state_from_tx_is_idempotent(session):
    payload = dict(
        sender_address="0x1111111111111111111111111111111111111111",
        root_contract="0x2222222222222222222222222222222222222222",
        touched_addresses=[
            "0x2222222222222222222222222222222222222222",
            "0x3333333333333333333333333333333333333333",
        ],
    )
    first = seed_interaction_scan_state_from_tx(session=session, **payload)
    second = seed_interaction_scan_state_from_tx(session=session, **payload)

    assert first == 6
    assert second == 0


def test_seed_interaction_scan_state_from_tx_skips_invalid_sender(session):
    inserted = seed_interaction_scan_state_from_tx(
        session=session,
        sender_address="not-an-address",
        root_contract="0x2222222222222222222222222222222222222222",
        touched_addresses=[
            "0x3333333333333333333333333333333333333333",
        ],
    )

    assert inserted == 0
    rows = session.exec(select(InteractionScanState)).all()
    assert rows == []

