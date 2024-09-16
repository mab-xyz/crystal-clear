import argparse
from web3 import Web3
import config
from call_tree import get_blocks_calltree, get_blocks_called_addresses

def main():
    w3 = Web3(Web3.HTTPProvider(config.ETHEREUM_NODE_URL))
    parser = argparse.ArgumentParser(description="SCSC")

    parser.add_argument('--block', type=int, required=False, help='Block number')
    parser.add_argument('--offset', type=int, required=False, default=0, help='offset of blocks')
    parser.add_argument('--address', type=str, required=True, help='Address')
    parser.add_argument('--calls', action="store_true", help='Print call trees')


    args = parser.parse_args()
    if args.block is None:
        block_number = w3.eth.block_number
    else:
        block_number = args.block
    offset = args.offset
    address = args.address
    calls = args.calls

    print("Analyzing Supply Chain of Contract:", address)
    print(f"Start block: {block_number - offset}")
    print(f"End block: {block_number}")

    get_blocks_called_addresses(w3, block_number - offset, block_number + 1, address)

    if calls:
         get_blocks_calltree(w3, block_number - offset, block_number + 1, address)


if __name__ == "__main__":
    main()
