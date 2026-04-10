"""Hard-coded contract verification allowlist.

Add addresses to CONTRACT_VERIFICATION_ALLOWLIST when a contract should bypass
Sourcify/Etherscan verification checks and be marked as allowlisted.
"""

CONTRACT_VERIFICATION_ALLOWLIST: set[str] = {
    # "0x1111111111111111111111111111111111111111",
}


def get_contract_verification_allowlist() -> set[str]:
    return {
        address.strip().lower()
        for address in CONTRACT_VERIFICATION_ALLOWLIST
        if address.strip().lower().startswith("0x")
    }
