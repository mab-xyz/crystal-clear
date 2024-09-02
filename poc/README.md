# SCSC CLI

A command-line tool to interact with Ethereum traces and fetch information about smart contract calls within specific blocks.

## Features

- Retrieve call trees for a range of blocks.
- Analyze smart contract interactions based on Ethereum traces.
- Configurable Ethereum node URL.

## Prerequisites

- Python 3.7 or higher
- An Ethereum node (e.g., Geth, Parity) running and accessible via HTTP

## Installation

### 1. Clone the Repository

First, clone the repository to your local machine:

```bash
git clone https://github.com/yourusername/ethereum_trace_cli.git
cd ethereum_trace_cli
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

Edit the config.py file to set your Ethereum node URL and other settings:
```bash
# config.py

ETHEREUM_NODE_URL = 'http://localhost:8545'
BLOCK_OFFSET = 10  # Optional: Adjust the block range offset if needed
```

## Usage
```bash
python scsc.py --block <block_number> --address <contract_address>
```