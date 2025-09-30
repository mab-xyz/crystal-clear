<div align="center">

# 🔍 Crystal Clear

A cutting-edge platform for analyzing Ethereum smart contract supply chains, funded by the [Ethereum Foundation](https://ethereum.foundation/). Crystal-Clear allows you to visualize, analyze, and assess the risks of smart contract interactions.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/Tests-passing-brightgreen.svg)](https://github.com/mab-xyz/crystal-clear/actions)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

## 🚀 What is Crystal-Clear?

Crystal-Clear is a comprehensive tool designed to provide insights into the complex interactions of Ethereum smart contracts. It enables users to:
- 🔍 **Analyze contract dependencies**: Understand how contracts interact with each other across the blockchain.
- 📊 **Generate detailed call graphs**: Visualize the flow of calls between contracts.
- ⚠️ **Assess risks**: Identify mutability risks, detects `proxy upgradeability` and `permissioned functions`.
- 🌐 **Interactive dashboards**: Explore contract data through an intuitive web interface.

---

## 🏗️ Project Structure

```
crystal-clear/
├── docs/         # Documentation
├── experiments/  # Research Implementations
└── webapp/
    ├── backend/  
    │   ├── api/            # API Implementation
    │   └── crystal-clear/  # Core Tool
    └── frontend/           # Frontend Implementation
```

---

## 📦 Key Features

### 🔗 Dependency Analysis
- Generate **comprehensive call graphs** to visualize contract interactions.
- Analyze dependencies across **specific block ranges**.
- Export results in **DOT** or **JSON** formats for further analysis.

### ⚠️ Risk Assessment
- Perform **risk analysis** for individual contracts or entire supply chains.
- Detect **proxy risks** and **permission risks**.
- Enrich contract data with **Etherscan** and **Allium** APIs.

### 🌐 Interactive Web Dashboard
- Explore contract data through an **interactive visualization tool**.
- Highlight nodes and edges to understand relationships in detail.
- View contract metadata, including deployment and verification status.

### ⚙️ Flexible Configuration
- Connect to any Ethereum node (local or remote) with **trace_filter** support.
- Customize logging levels and export formats for tailored analysis.

---

## 📚 Documentation

- [📖 Tool Guide](webapp/backend/crystal-clear/README.md)

---

## 🤝 Contributing

We welcome contributions from the community! Whether it's fixing bugs, adding features, or improving documentation, your help is appreciated.

---

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">
Made with transparency 🔍 by the crystal-clear team
</div>
