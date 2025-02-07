<div align="center">

# 🔍 Crystal Clear

A powerful research platform for analyzing smart contract supply chains on Ethereum

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-passing-brightgreen.svg)](https://github.com/chains-project/crystal-clear/actions)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## 🚀 Quick Start

```bash
git clone https://github.com/chains-project/crystal-clear.git
cd crystal-clear/scsc
poetry install

# CLI Analysis Example
scsc analyze --address 0xE592427A0AEce92De3Edee1F18E0157C05861564 \
            --from-block 0x14c3b86 \
            --to-block 0x14c3b90 \
            --export-dot graph.dot

# Or launch the interactive web interface
scsc web --address 0xE592427A0AEce92De3Edee1F18E0157C05861564 \
         --from-block 0x14c3b86 \
         --to-block 0x14c3b90
```

## 🏗️ Project Structure

```
crystal-clear/
├── scsc/         # 🛠️ Core Analysis Tool
├── data/         # 📊 Contract Interaction Datasets
├── notebooks/    # 📈 Analysis & Visualization
└── experiments/  # 🧪 Research Implementations
```

## 📦 Components

### Core Tool (`/scsc`)
The main analysis engine for smart contract supply chains, featuring:
- 📊 Command-line interface for data extraction and analysis
- 🌐 Interactive web visualization dashboard
- 🔍 Comprehensive contract dependency tracking

### Data & Analysis
- 📊 `/data` - Comprehensive contract interaction datasets
- 📈 `/notebooks` - Interactive analysis & visualization tools
- 🧪 `/experiments` - Cutting-edge research implementations

## 📚 Documentation
- [📖 Tool Guide](scsc/README.md)

## 🔮 Upcoming Features
Smart contract supply chain graphs will be enriched with metadata including supplier identification, mutability status, and security metrics.

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


---

<div align="center">
Made with transparency 🔍 by the crystal-clear team
</div>
