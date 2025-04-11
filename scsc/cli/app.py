import json

import dash
import dash_cytoscape as cyto
from dash import Input, Output, State, callback, dcc, html
from eth_utils import humanize_hexstr

from scsc.supply_chain import SupplyChain

styles = {
    "container": {
        "display": "flex",
        "background-color": "#f5f6fa",
        "min-height": "100vh",
    },
    "graph_container": {
        "flex": "8",
        "background-color": "white",
        "border-radius": "10px",
        "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
        "margin": "20px",
        "padding": "20px",
        "position": "relative",
        "height": "95vh",
    },
    "sidebar": {
        "flex": "4",
        "margin": "20px",
        "height": "95vh",
        "overflow": "hidden",
    },
    "tab": {
        "padding": "20px",
        "background-color": "white",
        "border-radius": "10px",
        "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)",
        "height": "calc(95vh - 100px)",  # Account for tab header height
        "overflow-y": "auto",
    },
    "json-output": {
        "background-color": "#f8f9fa",
        "padding": "15px",
        "border-radius": "5px",
        "border": "1px solid #dee2e6",
        "height": "300px",
        "overflowY": "auto",
        "font-family": "Monaco, monospace",
        "font-size": "14px",
    },
    "heading": {
        "color": "#2c3e50",
        "font-family": "'Segoe UI', sans-serif",
        "font-size": "24px",
        "margin-bottom": "20px",
        "border-bottom": "2px solid #3498db",
        "padding-bottom": "10px",
    },
    "contract-address": {
        "font-size": "14px",
        "color": "#2196f3",
        "background-color": "#f8f9fa",
        "padding": "8px",
        "border-radius": "4px",
        "margin": "8px 0",
        "font-family": "Monaco, monospace",
        "cursor": "pointer",
        "text-decoration": "none",  # Remove default underline
        "display": "block",  # Make the link block-level
        "transition": "background-color 0.2s",  # Smooth hover effect
        ":hover": {"background-color": "#e3f2fd"},  # Lighter blue on hover
    },
    "label-text": {
        "font-size": "14px",
        "color": "#7f8c8d",
        "font-family": "'Segoe UI', sans-serif",
        "margin-top": "16px",
    },
    "tab-label": {
        "font-family": "'Segoe UI', sans-serif",
        "font-size": "18px",
        "padding": "8px 16px",
    },
}


def get_etherscan_url(address):
    """Generate Etherscan URL for a contract address"""
    return f"https://etherscan.io/address/{address}"


def create_app(
    url: str, contract_address: str, from_block: str, to_block: str
):
    """Create and configure the dash application"""
    sc = SupplyChain(url, contract_address)
    sc.collect_calls(from_block, to_block)

    source_node = sc.cg.contract_address
    elements = [
        {"data": {"id": node, "label": humanize_hexstr(node)}}
        for node in sc.cg.G.nodes()
    ]
    elements += [
        {
            "data": {
                "id": u + "-" + v,
                "source": u,
                "target": v,
                "label": sc.cg.G[u][v]["data"],
            }
        }
        for u, v in sc.cg.G.edges()
    ]
    called_contracts = sc.get_all_dependencies()
    num_called_contracts = len(sc.cg.G.nodes()) - 1

    default_stylesheet = [
        {
            "selector": "node",
            "style": {
                "opacity": 0.65,
                "z-index": 9999,
                "label": "data(label)",
            },
        },
        {
            "selector": f'[id = "{source_node}"]',
            "style": {
                "background-color": "#5dade2",
                "opacity": 1,
            },
        },
        {
            "selector": "edge",
            "style": {
                "curve-style": "bezier",
                "opacity": 0.45,
                "z-index": 5000,
                "target-arrow-shape": "triangle",
            },
        },
        {
            "selector": ":selected",
            "style": {
                "background-color": "#FFC300",
                "line-color": "#FFC300",
                "target-arrow-color": "#FFC300",
                "opacity": 1,
                "label": "data(label)",
                "color": "black",
            },
        },
        {
            "selector": ".highlighted",
            "style": {
                "background-color": "#FFC300",
                "line-color": "#FFC300",
                "target-arrow-color": "#FFC300",
                "opacity": 1,
            },
        },
    ]

    app = dash.Dash(__name__)

    app.layout = html.Div(
        style=styles["container"],
        children=[
            html.Div(
                className="eight columns",
                style=styles["graph_container"],
                children=[
                    cyto.Cytoscape(
                        id="cytoscape",
                        elements=elements,
                        stylesheet=default_stylesheet,
                        style={
                            "height": "100%",
                            "width": "100%",
                            "position": "absolute",
                            "top": 0,
                            "left": 0,
                        },
                        layout={
                            "name": "cose",
                            "fit": True,
                            "padding": 30,
                            "componentSpacing": 100,
                            "nodeRepulsion": 400000,
                            "edgeElasticity": 100,
                            "nestingFactor": 5,
                            "gravity": 80,
                            "numIter": 1000,
                        },
                        responsive=True,
                    )
                ],
            ),
            html.Div(
                className="four columns",
                style=styles["sidebar"],
                children=[
                    dcc.Tabs(
                        id="tabs",
                        style={"border-radius": "10px"},
                        colors={
                            "border": "#dee2e6",
                            "primary": "#3498db",
                            "background": "#ffffff",
                        },
                        children=[
                            dcc.Tab(
                                label="Overview",
                                style=styles["tab-label"],
                                selected_style=styles["tab-label"],
                                children=[
                                    html.Div(
                                        style=styles["tab"],
                                        children=[
                                            html.H2(
                                                "Smart Contract Supply Chain",
                                                style=styles["heading"],
                                            ),
                                            html.P(
                                                "Analyzing Contract:",
                                                style=styles["label-text"],
                                            ),
                                            html.A(
                                                source_node,
                                                href=get_etherscan_url(
                                                    source_node
                                                ),
                                                target="_blank",
                                                style=styles[
                                                    "contract-address"
                                                ],
                                            ),
                                            html.P(
                                                f"Number of Called Contracts: {num_called_contracts}",
                                                style=styles["label-text"],
                                            ),
                                            html.P(
                                                "Called Contracts:",
                                                style=styles["label-text"],
                                            ),
                                            html.Div(
                                                [
                                                    html.A(
                                                        contract,
                                                        href=get_etherscan_url(
                                                            contract
                                                        ),
                                                        target="_blank",
                                                        style=styles[
                                                            "contract-address"
                                                        ],
                                                    )
                                                    for contract in called_contracts
                                                ],
                                            ),
                                        ],
                                    )
                                ],
                            ),
                            dcc.Tab(
                                label="Selection",
                                style=styles["tab-label"],
                                selected_style=styles["tab-label"],
                                children=[
                                    html.Div(
                                        style=styles["tab"],
                                        children=[
                                            html.H2(
                                                "Selected Elements",
                                                style=styles["heading"],
                                            ),
                                            html.Div(
                                                id="highlighted-elements",
                                                children=[
                                                    html.P(
                                                        "Selected Node:",
                                                        style=styles[
                                                            "label-text"
                                                        ],
                                                    ),
                                                    html.Div(
                                                        id="selected-node"
                                                    ),
                                                    html.P(
                                                        "Connected Nodes:",
                                                        style=styles[
                                                            "label-text"
                                                        ],
                                                    ),
                                                    html.Div(
                                                        id="connected-nodes"
                                                    ),
                                                ],
                                            ),
                                        ],
                                    )
                                ],
                            ),
                            dcc.Tab(
                                label="JSON",
                                style=styles["tab-label"],
                                selected_style=styles["tab-label"],
                                children=[
                                    html.Div(
                                        style=styles["tab"],
                                        children=[
                                            html.P(
                                                "Node Object JSON:",
                                                style={"color": "#7f8c8d"},
                                            ),
                                            html.Pre(
                                                id="tap-node-json-output",
                                                style=styles["json-output"],
                                            ),
                                            html.P(
                                                "Edge Object JSON:",
                                                style={"color": "#7f8c8d"},
                                            ),
                                            html.Pre(
                                                id="tap-edge-json-output",
                                                style=styles["json-output"],
                                            ),
                                        ],
                                    )
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )

    @callback(
        Output("tap-node-json-output", "children"),
        Input("cytoscape", "tapNode"),
    )
    def display_tap_node(data):
        if data:
            data = data["data"]
        return json.dumps(data, indent=2)

    @callback(
        Output("tap-edge-json-output", "children"),
        Input("cytoscape", "tapEdge"),
    )
    def display_tap_edge(data):
        if data:
            data = data["data"]
        return json.dumps(data, indent=2)

    # Replace the existing callback with this updated version
    @callback(
        Output("cytoscape", "stylesheet"),
        [Input("cytoscape", "tapNode"), Input("cytoscape", "tapEdge")],
        State("cytoscape", "elements"),
    )
    def highlight_neighbors(node, edge, elements):
        # Determine which was the most recent action based on which one is not None
        ctx = dash.callback_context
        if not ctx.triggered:
            return default_stylesheet

        trigger_id = ctx.triggered[0]["prop_id"].split(".")[1]
        stylesheet = default_stylesheet.copy()

        if trigger_id == "tapNode" and node:
            # Get selected node id
            selected_id = node["data"]["id"]

            # Find all edges from selected node
            connected_edges = [
                edge["data"]["target"]
                for edge in elements
                if "source" in edge["data"]
                and edge["data"]["source"] == selected_id
            ]

            # Add highlighting style for connected nodes and edges
            stylesheet.append(
                {
                    "selector": f'[id = "{selected_id}"]',
                    "style": {"background-color": "#FFC300", "opacity": 1},
                }
            )

            for target in connected_edges:
                # Highlight connected nodes
                stylesheet.append(
                    {
                        "selector": f'[id = "{target}"]',
                        "style": {"background-color": "#FFC300", "opacity": 1},
                    }
                )
                # Highlight edges
                stylesheet.append(
                    {
                        "selector": f'[source = "{selected_id}"][target = "{target}"]',
                        "style": {
                            "line-color": "#FFC300",
                            "target-arrow-color": "#FFC300",
                            "opacity": 1,
                        },
                    }
                )

        elif trigger_id == "tapEdge" and edge:
            # Get source and target nodes of the selected edge
            source_id = edge["data"]["source"]
            target_id = edge["data"]["target"]

            # Highlight source and target nodes
            for node_id in [source_id, target_id]:
                stylesheet.append(
                    {
                        "selector": f'[id = "{node_id}"]',
                        "style": {"background-color": "#FFC300", "opacity": 1},
                    }
                )

            # Highlight the selected edge
            stylesheet.append(
                {
                    "selector": f'[source = "{source_id}"][target = "{target_id}"]',
                    "style": {
                        "line-color": "#FFC300",
                        "target-arrow-color": "#FFC300",
                        "opacity": 1,
                    },
                }
            )

        return stylesheet

    @callback(
        [
            Output("selected-node", "children"),
            Output("connected-nodes", "children"),
        ],
        [Input("cytoscape", "tapNode")],
        State("cytoscape", "elements"),
    )
    def update_highlighted_elements(node, elements):
        if not node:
            return "No node selected", "No connected nodes"

        selected_id = node["data"]["id"]
        selected_node = html.A(
            selected_id,
            href=get_etherscan_url(selected_id),
            target="_blank",
            style=styles["contract-address"],
        )

        # Find connected nodes
        connected_nodes = [
            edge["data"]["target"]
            for edge in elements
            if "source" in edge["data"]
            and edge["data"]["source"] == selected_id
        ]

        connected_elements = [
            html.A(
                node_id,
                href=get_etherscan_url(node_id),
                target="_blank",
                style=styles["contract-address"],
            )
            for node_id in connected_nodes
        ]

        return (
            selected_node,
            connected_elements if connected_elements else "No connected nodes",
        )

    return app
