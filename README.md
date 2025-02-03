# SCSC

Analyzing the smart contract supply chain.

## Prerequisites

- Python 3.7 or higher
- An Ethereum node (e.g., Geth, Parity) running and accessible via HTTP

## Installation

### 1. Clone the Repository

First, clone the repository to your local machine:

```bash
git clone https://github.com/chains-project/scsc.git
cd scsc
```

### 2. Set Up a Virtual Environment (Optional but Recommended)

It's recommended to use a virtual environment to manage dependencies:
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install the required Python packages using pip:
```bash
pip install -r requirements.txt
```


### 4. Configure the Project

Edit the config.py file to set your Ethereum node URL:
```bash
# config.py

ETHEREUM_NODE_URL = 'http://localhost:8545'
```
## Usage

### Single contract supply chain

Computes the supply chain of a smart-contract at a given block (or over a block period TODO)

```bash
python scsc.py [--block <block_number>] [--offset <blocks_offset>] --address <contract_address> [--calls]  [--json]
```

`<block_number>`: Block number that is analyzed. When not provided, assumes the `latest` block number of Ethereum Mainnet.

`<blocks_offset>`: The number of blocks before `<block_number>` that are also analyzed. When not provided, assume the value `0`.

`--calls`: Flag that outputs the call trees of each transaction that was analyzed

`--json`: Save result as a json file

## Future features
### Contract graph 

    ./scsc --graph --from-block 1234 --to-block 2234  --output graph.dot

TODO: explain the medadata available on the graph (supplier, mutable, vulnerable, ...)
