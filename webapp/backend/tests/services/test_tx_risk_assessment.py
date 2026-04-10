from src.api.services.tx_risk_assessment import (
    _has_allowlisted_verification,
    _has_unverified_dangerous,
)


def test_allowlisted_contracts_are_not_unverified_dangerous():
    assert (
        _has_unverified_dangerous(
            [{"verification": {"verification": "allowlisted"}}]
        )
        is False
    )


def test_detects_allowlisted_verification():
    assert (
        _has_allowlisted_verification(
            [{"verification": {"verification": "allowlisted"}}]
        )
        is True
    )
