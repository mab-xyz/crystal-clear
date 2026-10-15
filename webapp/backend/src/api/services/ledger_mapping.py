"""Map crystal-clear verdicts to Ledger risk score and category."""

from __future__ import annotations

from dataclasses import dataclass

from src.api.services import ledger_descriptor as ld


@dataclass(frozen=True)
class LedgerVerdict:
    risk: int
    category: int
    message: str | None


def map_verdict(
    status: str, danger_reason: str | None, revert_error: str | None = None
) -> LedgerVerdict:
    """Decided mapping (plan Design):

    - UNVERIFIED / EIP_7702_UNVERIFIED_DELEGATE -> Threat, smart contract
    - FIRST_TIME_INTERACTION (contract never interacted with by anyone)
      -> Risk, smart contract
    - MISSING_HISTORY -> Risk, others
    - OK (incl. first time for this sender only) -> Benign
    - top-level call reverts -> Risk, Losing operation, unless already Threat
    """
    verdict = _base_verdict(status, danger_reason)
    if revert_error and verdict.risk < ld.RISK_THREAT:
        return LedgerVerdict(
            ld.RISK_RISK, ld.CATEGORY_LOSING, "Transaction reverts"
        )
    return verdict


def _base_verdict(status: str, danger_reason: str | None) -> LedgerVerdict:
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
