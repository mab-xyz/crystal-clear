# Smart Contract Supply Chain (SCSC) 🔗

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/poetry-dependency%20manager-blue)](https://python-poetry.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Analyze and visualize Ethereum smart contract dependencies with ease.
SCSC helps you understand contract interactions by generating detailed call graphs from on-chain data.

## ✨ Features

- 📊 Generate comprehensive call graphs from smart contract interactions
- 🔍 Analyze contract dependencies across specified block ranges
- 📈 Export visualizations in DOT format for further analysis
- ⚙️ Flexible configuration options for node connections and logging
- 🚀 Built with modern Python and best practices

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- Access to an Ethereum node (local or remote)
- Poetry

### Installation

```bash
# Clone the repository
git clone https://github.com/chains-project/crystal-clear.git
cd scsc

# Install with Poetry
poetry install

# Activate the environment
poetry shell
```

## 💻 Usage

### Basic Command Structure

```bash
scsc --url <node_url> \
     --address <contract_address> \
     --from-block <block> \
     --to-block <block> \
     [options]
```

### Key Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--url` | Ethereum node URL | `http://localhost:8545` |
| `--address` | Contract address to analyze | `0xE592427A0AEce92De3Edee1F18E0157C05861564` |
| `--from-block` | Starting block number (hex/decimal) | `0x14c3b86` or `21665670` |
| `--to-block` | Ending block number (hex/decimal) | `0x14c3b90` or `21665680` |
| `--log-level` | Logging verbosity | `ERROR`, `INFO`, `DEBUG` |
| `--export-dot` | Output file for DOT graph | `output.dot` |
| `--export-json` | Output file for JSON | `output.json` |

### Example

```bash
scsc --url http://localhost:8545 \
     --address 0xE592427A0AEce92De3Edee1F18E0157C05861564 \
     --from-block 0x14c3b86 \
     --to-block 0x14c3b90 \
     --log-level ERROR \
     --export-dot call_graph.dot
```

## 🛠️ Development

We use modern Python tools to maintain high code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **Ruff**: Fast Python linting
- **pre-commit**: Git hooks

Set up the development environment:

```bash
# Install development dependencies
poetry install --with dev

# Set up pre-commit hooks
pre-commit install
```

## 📚 Documentation [TODO]

For more detailed information about SCSC features and usage, check out our documentation:

- [Installation Guide](docs/installation.md)
- [Usage Examples](docs/examples.md)
- [Configuration Options](docs/configuration.md)
- [Contributing Guide](CONTRIBUTING.md)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

---

<div align="center">
Made with ❤️ by the SCSC team
</div>