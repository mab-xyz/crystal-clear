import matplotlib.pyplot as plt
import networkx as nx
import nxviz as nv
from nxviz import annotate
import pandas as pd
import numpy as np
import requests
import requests_cache
import os
from dotenv import load_dotenv
import sys
from config import contracts_file_path, official_labels_file_path


# Load environment variables from a .env file
load_dotenv()

output_file = sys.argv[1]
# Install a cache for Etherscan API responses
requests_cache.install_cache("etherscan_cache")

# Check if ETHERSCAN_API_KEY is set
api_key = os.getenv("ETHERSCAN_API_KEY")
if not api_key:
    raise ValueError("ETHERSCAN_API_KEY is not set, please set it in the .env file")


def get_contract_verification_status(contract_address, api_key):
    """
    Query Etherscan API to check if the contract's source code is verified.
    Returns True if verified, False if not verified, and None if API request fails.
    """
    url = "https://api.etherscan.io/api"
    params = {
        "module": "contract",
        "action": "getabi",
        "address": contract_address,
        "apikey": api_key,
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if (
            data["status"] == "1"
            and data["result"] != "Contract source code not verified"
        ):
            return True
        else:
            print(f"Response for {contract_address}: {data}")
            return False
    else:
        return None


def load_data(contracts_file, labels_file):
    """Load contracts and address labels data from CSV files."""
    data = pd.read_csv(contracts_file)
    address_labels = pd.read_csv(labels_file)
    # Create a dictionary for quick label lookup (keys in lowercase)
    address_label_dict = {
        k.lower(): v for k, v in zip(address_labels["address"], address_labels["label"])
    }
    return data, address_label_dict


def build_graph(data):
    """Create a graph from the contract interactions data."""
    G = nx.Graph()
    for _, row in data.iterrows():
        G.add_edge(
            row["from_address"].lower(),
            row["to_address"].lower(),
            weight=row["call_count"],
        )
    return G


def remove_invalid_nodes(G):
    """Remove nodes with addresses starting with the invalid pattern."""
    invalid_nodes = [
        node
        for node in G.nodes()
        if str(node).startswith("0x000000000000000000000000000000000000000")
    ]
    G.remove_nodes_from(invalid_nodes)
    return G


def update_verification_status(G, api_key):
    """
    Update each node in the graph with its verification status.
    Verified nodes get a tick ("✓") while non-verified ones get a cross ("✗").
    """
    for node in G.nodes():
        is_verified = get_contract_verification_status(node, api_key)
        print(f"Contract {node} is {'verified' if is_verified else 'not verified'}.")
        G.nodes[node]["verified"] = "✓" if is_verified else "✗"
    return G


def relabel_nodes_with_labels(G, address_label_dict):
    """
    Relabel nodes using the provided address labels dictionary.
    Then, shorten long hexadecimal addresses and append the verification tick.
    """
    # Replace addresses with official labels if available
    G = nx.relabel_nodes(G, address_label_dict)
    # For any node that is still an address, shorten it (e.g., 0x1234...abcd)
    G = nx.relabel_nodes(
        G, lambda x: x[:4] + "..." + x[-4:] if str(x).startswith("0x") else x
    )
    # Append verification status to each node label
    G = nx.relabel_nodes(G, lambda x: x + " " + str(G.nodes[x]["verified"]))
    return G


def apply_edge_transformations(G):
    """Apply logarithmic transformation to the edge weights."""
    for u, v, d in G.edges(data=True):
        d["log_weight"] = np.log1p(d["weight"])
    return G


def assign_color_groups(G):
    """
    Assign a color group to each node based on whether it is an address.
    Nodes that start with '0x' are group 0; all others are group 1.
    """
    for node in G.nodes():
        if str(node).startswith("0x"):
            G.nodes[node]["color_group"] = 0
        else:
            G.nodes[node]["color_group"] = 1
    return G


def generate_plot(G, output_file):
    """Generate a circos plot of the network using nxviz and save the output."""
    plt.figure(figsize=(14, 14))
    nv.circos(G, node_color_by="color_group", edge_lw_by="log_weight")
    annotate.circos_labels(G, layout="rotate")
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Saved network diagram to {output_file}")


def print_node_statistics(G):
    """Print the number of nodes and their distribution by color group."""
    print(f"Number of all nodes: {len(G.nodes())}")
    color_group_counts = {0: 0, 1: 0}
    for node in G.nodes():
        color_group = G.nodes[node]["color_group"]
        color_group_counts[color_group] += 1
    print("Number of nodes in each color group:")
    for group, count in color_group_counts.items():
        print(f"Color group {group}: {count} nodes")


def main():
    # Load data and build initial graph
    data, address_label_dict = load_data(contracts_file_path, official_labels_file_path)
    G = build_graph(data)
    G = remove_invalid_nodes(G)

    # Update nodes with verification status from Etherscan
    G = update_verification_status(G, api_key)

    # Relabel nodes with official labels and verification ticks
    G = relabel_nodes_with_labels(G, address_label_dict)

    # Apply transformations to edge weights and assign color groups to nodes
    G = apply_edge_transformations(G)
    G = assign_color_groups(G)

    # Print some statistics about the graph
    print_node_statistics(G)

    # Generate and save the network plot
    generate_plot(G, output_file)


if __name__ == "__main__":
    main()
