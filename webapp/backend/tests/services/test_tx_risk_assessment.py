from src.api.services.tx_risk_assessment import _has_unverified_dangerous


def test_allowlisted_contracts_are_not_unverified_dangerous():
    assert (
        _has_unverified_dangerous(
            [{"verification": {"verification": "allowlisted"}}]
        )
        is False
    )
