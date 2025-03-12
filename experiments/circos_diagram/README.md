# Circos Diagram

This project generates a circos plot of Ethereum contract interactions using data from Etherscan. The plot visualizes the network of contract calls, highlighting verified contracts and categorizing nodes by their type.

## Features

- **Data Loading**: Load contract interaction data and address labels from CSV files.
- **Graph Construction**: Build a network graph from the interaction data.
- **Node Verification**: Check contract verification status using the Etherscan API.
- **Node Relabeling**: Relabel nodes with official labels and append verification status.
- **Edge Transformation**: Apply logarithmic transformation to edge weights.
- **Node Coloring**: Assign color groups to nodes based on their type.
- **Visualization**: Generate a circos plot of the network and save it as an image.


## Installation

1. Install the required packages:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Set up your environment variables:
   - Create a `.env` file in the root directory.
   - Add your Etherscan API key:
     ```
     ETHERSCAN_API_KEY=your_api_key_here
     ```

## Usage

1. Prepare your data:
   - Ensure you have the contracts interaction data and address labels in CSV format.
   - Update the paths in the `config.py` file:
     ```python
     contracts_file_path = "path/to/contracts.csv"
     official_labels_file_path = "path/to/labels.csv"
     ```

2. Run the script:
   ```bash
   python experiments/circos_diagram/circos_diagram.py output_image.png
   ```

3. The script will generate a circos plot and save it as `output_image.png`.

## Output

- The script outputs a circos plot image file showing the network of Ethereum contract interactions.
- Nodes are colored based on their type, and verified contracts are marked with a tick.
