import logging
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import click

from crystal_clear import CrystalClear


@click.group()
def main():
    """Smart Contract Supply Chain Analysis Tool"""
    pass


@main.command(name="dependency")
@click.option(
    "--node-url", type=str, help="Ethereum (archive) node URL",
)
@click.option(
    "--allium-key", type=str, help="Allium API key",
)
@click.option("--address", required=True, type=str, help="Contract address")
@click.option(
    "--from-block", required=True, type=str, help="Starting block number"
)
@click.option(
    "--to-block", required=True, type=str, help="Ending block number"
)
@click.option("--export-dot", type=str, help="Export call graph to DOT file")
@click.option("--export-json", type=str, help="Export call graph to JSON file")
@click.option("--log-level", default="ERROR", type=str, help="Logging level")
def dependency(
    node_url, allium_key, address, from_block, to_block, export_dot, export_json, log_level
):
    """Analyze contract calls and generate dependency graph"""
    logging.basicConfig(level=log_level.upper())
    logger = logging.getLogger(__name__)

    if not node_url and not allium_key:
        raise ValueError("You must provide at least a node-url or an allium-api-key.")
    
    try:
        cc = CrystalClear(url=node_url, api_key=allium_key)
        
        dep = cc.get_dependencies(address, from_block, to_block)
        console = Console()

        # --- Metadata Panel ---
        metadata = (
            f"[bold]Contract:[/bold] {dep['address']}\n"
            f"[bold]Blocks:[/bold] {dep['from_block']} → {dep['to_block']}\n"
            f"[bold]Nodes:[/bold] {dep['n_nodes']}\n"
            f"[bold]Matching Txs:[/bold] {dep['n_matching_transactions']}"
        )
        console.print(Panel(metadata, title="📄 Crystal-Clear CLI: Dependency Analysis", expand=False, border_style="cyan"))


        # --- Nodes Table (first 10 only for readability) ---
        node_table = Table(title="🔗 Nodes", header_style="bold blue")
        node_table.add_column("Index", justify="right", style="yellow")
        node_table.add_column("Address", style="white")
        node_table.add_column("Label", style="white")

        # present the first 10 nodes only for readability
        for i, (node, label) in enumerate(list(dep["nodes"].items())[:10], start=1):
            node_table.add_row(str(i), node, label)
        if len(dep["nodes"]) > 10:
            node_table.add_row("...", f"... {len(dep['nodes']) - 10} more ...", "...")

        console.print(node_table)

        # --- Edges Table (first 10 only for readability) ---
        edge_table = Table(title="➡️ Edges", header_style="bold green")
        edge_table.add_column("Source", style="cyan")
        edge_table.add_column("Target", style="cyan")
        edge_table.add_column("Type(s)", style="magenta")
        # edge_table.add_column("Depth", justify="right", style="yellow")

        for edge in dep["edges"][:10]:
            types = ", ".join(f"{k} ({v})" for k, v in edge["types"].items())
            edge_table.add_row(edge["source"], edge["target"], types)

        if len(dep["edges"]) > 10:
            edge_table.add_row("...", "...", f"... {len(dep['edges']) - 10} more ...")
        console.print(edge_table)
        console.print("[grey]Export the report to a JSON file for complete analysis.[/grey]")

        if export_json:
            with open(export_json, "w") as f:
                json.dump(dep, f, indent=4)
            logger.info(f"Call graph exported to JSON file: {export_json}")
        
        if export_dot:
            logger.warning("DOT export not implemented in TraceCollector.")
            with open(export_dot, "w") as f:
                f.write("digraph G {\n")

                # Optional: declare nodes
                for node in dep["nodes"]:
                    f.write(f'    "{node}";\n')

                # Add edges
                for edge in dep["edges"]:
                    source = edge["source"]
                    target = edge["target"]
                    label = ", ".join(f"{k} ({v})" for k, v in edge["types"].items())
                    f.write(f'    "{source}" -> "{target}" [label="{label}"];\n')

                f.write("}\n")


    except Exception as e:
        logger.error(f"analyze: {e}")


if __name__ == "__main__": 
    main()
