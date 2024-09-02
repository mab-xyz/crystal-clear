import argparse
from web3 import Web3
import config
from call_tree import get_blocks_calltree

def main():
    parser = argparse.ArgumentParser(description="SCSC")

    parser.add_argument('--block', type=int, required=True, help='Block number')
    parser.add_argument('--address', type=str, required=True, help='Address')

    args = parser.parse_args()
    block_number = args.block
    address = args.address

    w3 = Web3(Web3.HTTPProvider(config.ETHEREUM_NODE_URL))
    
    get_blocks_calltree(w3, block_number - config.BLOCK_OFFSET, block_number + 1, address)


if __name__ == "__main__":
    main()
