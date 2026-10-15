"""Map crystal-clear verdicts to Ledger risk score and category."""

from __future__ import annotations

from dataclasses import dataclass

from src.api.services import ledger_descriptor as ld


@dataclass(frozen=True)
class LedgerVerdict:
    risk: int
    category: int
    message: str | None


def map_verdict(status: str, danger_reason: str | None) -> LedgerVerdict:
    """Decided mapping (plan Design):

    - UNVERIFIED / EIP_7702_UNVERIFIED_DELEGATE -> Threat, smart contract
    - FIRST_TIME_INTERACTION (contract never interacted with by anyone)
      -> Risk, smart contract
    - MISSING_HISTORY -> Risk, others
    - OK (incl. first time for this sender only) -> Benign
    """
    if status == "OK":
        return LedgerVerdict(ld.RISK_BENIGN, ld.CATEGORY_NA, None)
    if danger_reason in ("UNVERIFIED", "EIP_7702_UNVERIFIED_DELEGATE"):
        return LedgerVerdict(
            ld.RISK_THREAT, ld.CATEGORY_CONTRACT, "Unverified contract"
        )
    if danger_reason == "FIRST_TIME_INTERACTION":
        return LedgerVerdict(
            ld.RISK_RISK, ld.CATEGORY_CONTRACT, "Never-used contract"
        )
    if status == "DANGEROUS":
        return LedgerVerdict(ld.RISK_THREAT, ld.CATEGORY_OTHERS, None)
    return LedgerVerdict(ld.RISK_RISK, ld.CATEGORY_OTHERS, "Incomplete history")
