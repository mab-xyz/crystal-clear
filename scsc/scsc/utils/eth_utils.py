from web3 import Web3


def validate_and_convert_block(block: str) -> str:
    """
    Validates if block number is decimal or hex and returns hex format.
    """
    if isinstance(block, int):
        return hex(block)

    if isinstance(block, str):
        if block.startswith("0x"):
            try:
                int(block, 16)
                return block
            except ValueError as e:
                raise ValueError(f"Invalid hex block number: {block}") from e

        if block.isdigit():
            return hex(int(block))

    raise ValueError(
        f"Block number must be decimal or hexadecimal: {block}"
    ) from None


def validate_and_convert_address(address: str) -> str:
    """
    Validates if the address is a valid Ethereum address and converts to checksum.

    Args:
        address: Ethereum address
    Returns:
        Checksum address
    Raises:
        ValueError: If address is invalid
    """
    if not Web3.is_address(address):
        raise ValueError(f"Invalid Ethereum address: {address}")
    return Web3.to_checksum_address(address)
