# Crystal-Clear CLI: Smart Contract Supply Chain 🔗

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-dependency%20manager-blue)](https://python-poetry.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-passing-brightgreen.svg)](https://github.com/chains-project/crystal-clear/actions)

Analyze and visualize Ethereum smart contract dependencies with ease.
SCSC helps you understand contract interactions by generating detailed call graphs from on-chain data.

## ✨ Features

- 📊 Generate comprehensive call graphs from smart contract interactions
- 🔍 Analyze contract dependencies across specified block ranges
- 📈 Export visualizations in DOT format for further analysis
- ⚙️ Flexible configuration options for node connections and logging

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- Access to an Archive Ethereum node (local or remote)
- Allium API access: optional, used to enrich addresses with labels
- Etherscan API access: required for retrieving verified smart contract source code
- Poetry

### Installation

```bash
# Clone the repository
git clone https://github.com/chains-project/crystal-clear.git
cd crystal-clear

# Install with Poetry
poetry install

# Activate the environment
poetry shell
```

## 💻 Usage

Crystal-Clear CLI provides two main commands:

### 1. Analyze Dependencies Command

**Dependency Graph**
```bash
# note the RPC node must have method trace_filter 
crystal-clear dependency --node-url <node_url> \
            --address <contract_address> \
            --from-block <block> \
            --to-block <block> \
            [options]

# this exports the smart contract dependency graph
crystal-clear dependency
            --address 0xE592427A0AEce92De3Edee1F18E0157C05861564 \
            --from-block 0x14c3b86 \
            --to-block 0x14c3b90 \
            --export-dot graph.dot
```

**Risk analysis per contract** (computes the risk factors, incl. proxy and permission risks)

You can select the scope of the analysis:
- `single` – assesses the risk of the specified contract only.
- `supply-chain` – assesses the risk of the contract and all dependent contracts in its supply chain.
```bash
crystal-clear risk --etherscan-api-key <etherscan_api> \
            --node-url <node_url> \
            --scope [single|supply-chain]
            --address <contract_address> \
            [options]

crystal-clear risk
            --address 0xE592427A0AEce92De3Edee1F18E0157C05861564 \
            --scope single
            --export-json analysis.json
```


### Key Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--node-url` | Ethereum node URL | `http://localhost:8545` |
| `--allium-api-key` | Allium API Key| `` | 
| `--etherscan-api-key` | Etherscan API Key | `` |
| `--address` | Contract address to analyze | `0xE592427A0AEce92De3Edee1F18E0157C05861564` |
| `--from-block` | Starting block number (hex/decimal) | `0x14c3b86` or `21665670` |
| `--to-block` | Ending block number (hex/decimal) | `0x14c3b90` or `21665680` |
| `--log-level` | Logging verbosity (analyze only) | `ERROR`, `INFO`, `DEBUG` |
| `--export-dot` | Output file for DOT graph (analyze only) | `output.dot` |
| `--export-json` | Output file for JSON (analyze only) | `output.json` |


## 🛠️ Development

We use modern Python tools to maintain high code quality:

- **Black**: Code formatting
- **Ruff**: Fast Python linting
- **pre-commit**: Git hooks

Set up the development environment:

```bash
# Install development dependencies
poetry install --with dev

# Set up pre-commit hooks
pre-commit install
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

---

<div align="center">
Made with transparency 🔍 by the crystal-clear team
</div>
