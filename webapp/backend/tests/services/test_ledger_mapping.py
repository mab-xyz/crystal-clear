import pytest

from src.api.services import ledger_descriptor as ld
from src.api.services.ledger_mapping import map_verdict


@pytest.mark.parametrize(
    "status,reason,revert,risk,cat",
    [
        ("OK", None, None, ld.RISK_BENIGN, ld.CATEGORY_NA),
        ("DANGEROUS", "UNVERIFIED", None, ld.RISK_THREAT, ld.CATEGORY_CONTRACT),
        ("DANGEROUS", "EIP_7702_UNVERIFIED_DELEGATE", None, ld.RISK_THREAT, ld.CATEGORY_CONTRACT),
        ("DANGEROUS", "FIRST_TIME_INTERACTION", None, ld.RISK_RISK, ld.CATEGORY_CONTRACT),
        ("POTENTIAL_DANGEROUS", "MISSING_HISTORY", None, ld.RISK_RISK, ld.CATEGORY_OTHERS),
        ("OK", None, "Reverted", ld.RISK_RISK, ld.CATEGORY_LOSING),
        ("DANGEROUS", "FIRST_TIME_INTERACTION", "Reverted", ld.RISK_RISK, ld.CATEGORY_LOSING),
        ("DANGEROUS", "UNVERIFIED", "Reverted", ld.RISK_THREAT, ld.CATEGORY_CONTRACT),
    ],
)
def test_map_verdict(status, reason, revert, risk, cat):
    v = map_verdict(status, reason, revert)
    assert (v.risk, v.category) == (risk, cat)
    assert v.message is None or len(v.message) <= ld.MAX_PROVIDER_MESSAGE
