import json
import logging
import os

import click
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from crystal_clear import CrystalClear, RiskAnalysis
from crystal_clear.clients import VerificationDetails
from crystal_clear.code_analyzer import PermissionsInfo, ProxyInfo
from crystal_clear.traces import CallGraph

logger = logging.getLogger(__name__)


def setup_logging(log_level: str) -> None:
    """Setup logging configuration for the CLI"""
    logging.basicConfig(
        level=log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.setLevel(log_level.upper())


@click.group(
    context_settings=dict(help_option_names=["-h", "--help"]),
    help=(
        "Smart Contract Supply Chain Analysis Tool.\n\n"
        "Commands:\n"
        "  - dependency: Build call graph dependencies across blocks\n"
        "  - risk:       Assess code-level risks via Etherscan sources\n"
        "  - tx-risk:    Simulate a call or inspect a tx and check 'first-time' + verification\n\n"
        "Use --help on any subcommand for details and examples."
    ),
)
def main():
    """Crystal-Clear CLI"""
    pass


@main.command(name="dependency")
@click.option(
    "--node-url",
    type=str,
    help="Ethereum (archive) node URL",
)
@click.option(
    "--allium-api-key",
    type=str,
    help="Allium API key",
)
@click.option("--address", required=True, type=str, help="Contract address")
@click.option(
    "--from-block", required=False, type=str, help="Starting block number"
)
@click.option(
    "--to-block", required=False, type=str, help="Ending block number"
)
@click.option("--export-dot", type=str, help="Export call graph to DOT file")
@click.option("--export-json", type=str, help="Export call graph to JSON file")
@click.option("--log-level", default="ERROR", type=str, help="Logging level")
def dependency(
    node_url,
    allium_api_key,
    address,
    from_block,
    to_block,
    export_dot,
    export_json,
    log_level,
):
    """Analyze contract calls and generate dependency graph"""
    setup_logging(log_level)

    node_url = node_url or os.getenv("NODE_URL")
    allium_api_key = allium_api_key or os.getenv("ALLIUM_API_KEY")
    console = Console()
    if not node_url:
        console.print(
            "[red]Error: You must provide a node URL via --node-url or NODE_URL env variable.[/red]"
        )
        return

    try:
        cc = CrystalClear(
            url=node_url, allium_api_key=allium_api_key, log_level=log_level
        )

        dep: CallGraph = cc.get_dependencies_full(
            address, from_block=from_block, to_block=to_block
        )
        # --- Metadata Panel ---
        metadata = (
            f"[bold]Contract:[/bold] {dep.address}\n"
            f"[bold]Blocks:[/bold] {dep.from_block} → {dep.to_block}\n"
            f"[bold]Nodes:[/bold] {dep.n_nodes}\n"
            f"[bold]Matching Txs:[/bold] {dep.n_matching_transactions}"
        )
        console.print(
            Panel(
                metadata,
                title="📄 Crystal-Clear CLI: Dependency Analysis",
                expand=False,
                border_style="cyan",
            )
        )

        # --- Nodes Table (first 10 only for readability) ---
        node_table = Table(title="🔗 Nodes", header_style="bold blue")
        node_table.add_column("Index", justify="right", style="yellow")
        node_table.add_column("Address", style="white")
        node_table.add_column("Label", style="white")
        node_table.add_column("Depth", style="white")

        # present the first 10 nodes only for readability
        for i, (node, label) in enumerate(
            list(dep.nodes.items())[:10], start=1
        ):
            depth = dep.dependency_depths.get(node.lower(), 0)
            node_table.add_row(str(i), node, label, str(depth))
        if len(dep.nodes) > 10:
            node_table.add_row(
                "...", f"... {len(dep.nodes) - 10} more ...", "...", "..."
            )

        console.print(node_table)
        if not allium_api_key:
            console.print(
                "[yellow]Warning: Allium API key not provided. Labels are not available.[/yellow]"
            )

        # --- Edges Table (first 10 only for readability) ---
        edge_table = Table(title="➡️ Edges", header_style="bold green")
        edge_table.add_column("Source", style="cyan")
        edge_table.add_column("Target", style="cyan")
        edge_table.add_column("Type(s)", style="magenta")
        # edge_table.add_column("Depth", justify="right", style="yellow")

        for edge in dep.edges[:10]:
            types = ", ".join(f"{k} ({v})" for k, v in edge.types.items())
            edge_table.add_row(edge.source, edge.target, types)

        if len(dep.edges) > 10:
            edge_table.add_row(
                "...", "...", f"... {len(dep.edges) - 10} more ..."
            )
        console.print(edge_table)
        console.print(
            "[grey]Export the report to a JSON file for complete analysis.[/grey]"
        )

        if export_json:
            with open(export_json, "w") as f:
                json.dump(dep.to_dict(), f, indent=4)
            logger.info(f"Call graph exported to JSON file: {export_json}")

        if export_dot:
            logger.warning("DOT export not implemented in TraceCollector.")
            with open(export_dot, "w") as f:
                f.write("digraph G {\n")

                # Optional: declare nodes
                for node in dep.nodes.keys():
                    f.write(f'    "{node}";\n')

                # Add edges
                for edge in dep.edges:
                    source = edge.source
                    target = edge.target
                    label = ", ".join(
                        f"{k} ({v})" for k, v in edge.types.items()
                    )
                    f.write(
                        f'    "{source}" -> "{target}" [label="{label}"];\n'
                    )

                f.write("}\n")

    except Exception as e:
        logger.error(f"analyze: {e}")


@main.command(name="risk")
@click.option(
    "--etherscan-api-key",
    type=str,
    help="Etherscan API key",
)
@click.option("--node-url", type=str, help="Ethereum (archive) node URL")
@click.option(
    "--scope",
    default="single",
    type=click.Choice(["single", "supply-chain"]),
    help="Analysis scope",
)
@click.option("--address", required=True, type=str, help="Contract address")
@click.option(
    "--from-block",
    required=False,
    type=str,
    help="Starting block number (for supply-chain scope)",
)
@click.option(
    "--to-block",
    required=False,
    type=str,
    help="Ending block number (for supply-chain scope)",
)
@click.option(
    "--blocks",
    default=5,
    type=int,
    help="Number of blocks to fetch at a time (for supply-chain scope)",
)
@click.option("--log-level", default="ERROR", type=str, help="Logging level")
@click.option("--export-json", type=str, help="Export call graph to JSON file")
def risk(
    etherscan_api_key,
    node_url,
    scope,
    address,
    from_block,
    to_block,
    blocks,
    log_level,
    export_json,
):
    """Analyze contract code for potential vulnerabilities"""
    setup_logging(log_level)

    etherscan_key = os.getenv("ETHERSCAN_API_KEY") or etherscan_api_key
    console = Console()
    if etherscan_key is None or etherscan_key.strip() == "":
        console.print(
            "[red]Error: You must provide an Etherscan API key via --etherscan-api-key or ETHERSCAN_API_KEY env variable.[/red]"
        )
        return

    try:
        cc = CrystalClear(
            url=node_url, etherscan_api_key=etherscan_key, log_level=log_level
        )

        analysis: RiskAnalysis = cc.get_risk_factors(
            address,
            scope=scope,
            from_block=from_block,
            to_block=to_block,
            blocks=blocks,
        )
        status = "✅" if analysis.aggregated_risks.verified else "❌"
        metadata_general = (
            f"[bold]Root Contract:[/bold] {analysis.root_address}\n"
            f"[bold]Scope:[/bold] {scope}\n"
            f"[bold]Dependencies Analyzed:[/bold] {len(analysis.dependencies)}\n"
            f"[bold]All Verified Contracts:[/bold] {status}\n"
            f"[bold]Aggregated Risks:[/bold] {analysis.aggregated_risks.risk_factors}"
        )

        table = Table(
            title="📊 Dependency Risk Summary",
            header_style="bold red",
            expand=True,
            show_lines=True,
        )
        table.add_column("Contract Address", style="cyan", no_wrap=True)
        table.add_column("Dependency Depth", style="magenta")
        table.add_column("Risk Factors", style="red")
        sorted_deps = sorted(
            analysis.dependencies, key=lambda d: d.dependency_depth
        )

        for i, dep in enumerate(sorted_deps):
            if i >= 5:
                table.add_row(
                    "...",
                    "...",
                    f"... {len(analysis.dependencies) - 5} more ...",
                )
                break
            table.add_row(
                dep.address,
                str(dep.dependency_depth),
                str(dep.risk_factors),
            )

        # console.print(table)
        group_general = Group(metadata_general, table)
        console.print(
            Panel(
                group_general,
                title="Aggregated Risk Analysis",
                expand=True,  # ensures panel stretches
                border_style="cyan",
                width=100,  # fixed width for consistent borders
            )
        )
        console.print(
            "[grey]\n\n\nDetailed risk reports for the first 3 contracts are shown below.\n[/grey]"
        )
        for i, dep in enumerate(sorted_deps):
            if i >= 3:
                console.print(
                    f"[yellow]... ({len(analysis.dependencies) - 3} more contracts omitted)[/yellow]"
                )
                break

            details = dep.details or {}
            verification_data = details.get("verification_info") or None
            verification_info = (
                None
                if not verification_data
                else VerificationDetails(**verification_data)
            )
            proxy_data = details.get("proxy_info") or None
            proxy_info = None if not proxy_data else ProxyInfo(**proxy_data)
            permissions_data = details.get("permissions_info") or None
            permissions_info = (
                None
                if not permissions_data
                else PermissionsInfo(**permissions_data)
            )

            # --- Metadata text ---
            metadata = (
                f"[bold]Contract:[/bold] {dep.address}\n"
                f"[bold]Dependency Depth:[/bold] {dep.dependency_depth}\n"
                f"[bold]Verification Status:[/bold] "
                f"{verification_info.verification if verification_info else 'Unknown'}\n"
                f"[bold]Proxy Information:[/bold] "
                f"{proxy_info.description if proxy_info else 'No information available.'}\n"
                f"[bold]Permissioned Functions:[/bold] "
                f"{len(permissions_info.permissions) if permissions_info else 0}"
            )

            # --- Permissioned Functions Table ---
            if not permissions_info or len(permissions_info.permissions) == 0:
                func_table = (
                    "[green]No permissioned functions detected.[/green]"
                )
            else:
                func_table = Table(
                    title="⚠️ Permissioned Functions",
                    header_style="bold red",
                    expand=True,
                    show_lines=True,
                )
                func_table.add_column("Function", style="white", no_wrap=True)
                func_table.add_column("State Variables Written", style="white")
                func_table.add_column(
                    "Conditions on msg.sender", style="white"
                )

                # Show only first 3 functions
                for j, item in enumerate(permissions_info.permissions):
                    if j >= 3:
                        func_table.add_row(
                            "...",
                            "",
                            f"[yellow]{len(permissions_info.permissions) - 3} more functions omitted[/yellow]",
                        )
                        break
                    conditions = "\n".join(
                        [f"- {cond}" for cond in item.conditions]
                    )
                    state_vars = ", ".join(item.state_variables)
                    func_table.add_row(item.function, state_vars, conditions)

            # --- Combine metadata + table into one panel ---
            group = Group(metadata, func_table)
            console.print(
                Panel(
                    group,
                    title=f"Risk Analysis: {dep.address}",
                    expand=True,  # ensures panel stretches
                    border_style="cyan",
                    width=100,  # fixed width for consistent borders
                )
            )
        if export_json:
            with open(export_json, "w") as f:
                json.dump(analysis.to_dict(), f, indent=4)
            logger.info(f"Call graph exported to JSON file: {export_json}")

    except Exception as e:
        logger.error(f"risk: {e}")


@main.group(
    name="tx-risk",
    help=(
        "Simulate a call (trace_call) or analyze a single on-chain transaction.\n\n"
        "Examples:\n"
        "  crystal-clear tx-risk call --node-url $NODE --from 0xEOA --to 0xCONTRACT --data 0x --value 0x0\n"
        "  crystal-clear tx-risk tx   --node-url $NODE --tx-hash 0x...\n\n"
        "Checks 'first-time' interactions on-chain. Use --from-block/--to-block to bound history."
    ),
)
def simulate_group():
    """Tx risk simulation for calls and single transactions"""
    pass


@simulate_group.command(name="call")
@click.option("--node-url", type=str, help="Ethereum node URL")
@click.option(
    "--etherscan-api-key", type=str, help="Etherscan API key (optional)"
)
@click.option(
    "--from", "from_addr", required=True, type=str, help="Sender address"
)
@click.option(
    "--to", "to_addr", required=True, type=str, help="Target contract address"
)
@click.option("--data", default="0x", type=str, help="Calldata (hex)")
@click.option("--value", default="0x0", type=str, help="Value (hex)")
@click.option("--gas", required=False, type=str, help="Gas limit (hex)")
@click.option("--gas-price", required=False, type=str, help="Gas price (hex)")
@click.option(
    "--block-tag",
    default="latest",
    type=str,
    help='Block tag (e.g. "latest", number, or 0x-hex)',
)
@click.option(
    "--from-block",
    required=False,
    type=str,
    help="On-chain scan start (optional)",
)
@click.option(
    "--to-block", required=False, type=str, help="On-chain scan end (optional)"
)
@click.option(
    "--latest-offset",
    default=0,
    type=int,
    help="If set (>0) and --from-block not given, from_block = max(0, to_block - offset)",
)
@click.option(
    "--call-file",
    type=str,
    help=(
        "Path to JSON file with a full call object (keys: from,to,data,value[,gas,gasPrice]); flags override file"
    ),
)
@click.option("--export-json", type=str, help="Export results to JSON file")
@click.option("--log-level", default="ERROR", type=str, help="Logging level")
def simulate_call(
    node_url,
    etherscan_api_key,
    from_addr,
    to_addr,
    data,
    value,
    gas,
    gas_price,
    block_tag,
    from_block,
    to_block,
    latest_offset,
    call_file,
    export_json,
    log_level,
):
    """Run a trace_call and assess tx risk targets"""
    setup_logging(log_level)
    console = Console()

    node_url = node_url or os.getenv("NODE_URL")
    if not node_url:
        console.print(
            "[red]Error: You must provide a node URL via --node-url or NODE_URL env variable.[/red]"
        )
        return

    # Load call object from file if provided
    call_object = {}
    if call_file:
        try:
            with open(call_file, "r") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    call_object.update(loaded)
        except Exception as e:
            console.print(f"[red]Error loading call file: {e}[/red]")
            return

    # Apply CLI flag overrides
    if from_addr:
        call_object["from"] = from_addr
    if to_addr:
        call_object["to"] = to_addr
    if data is not None:
        call_object["data"] = data
    if value is not None:
        call_object["value"] = value
    if gas:
        call_object["gas"] = gas
    if gas_price:
        call_object["gasPrice"] = gas_price

    if not call_object.get("to"):
        console.print(
            "[red]Error: target address is required (use --to or call file).[/red]"
        )
        return

    try:
        cc = CrystalClear(
            url=node_url,
            etherscan_api_key=etherscan_api_key,
            log_level=log_level,
        )
        results = cc.simulate_and_check(
            call_object,
            block_tag=block_tag,
            from_block=from_block,
            to_block=to_block,
            latest_offset=latest_offset,
        )

        # Render results
        table = Table(
            title="🎯 Tx Risk (Simulated Call)", header_style="bold green"
        )
        table.add_column("Address", style="cyan")
        table.add_column("First Time", style="yellow")
        table.add_column("Verification", style="magenta")
        table.add_column("Source", style="white")

        for addr, info in results.items():
            v = info.get("verification", {}) or {}
            table.add_row(
                addr,
                "Yes" if info.get("first_time") else "No",
                str(v.get("verification", "unknown")),
                str(v.get("source", "-")),
            )

        console.print(table)

        if export_json:
            with open(export_json, "w") as f:
                json.dump(results, f, indent=4)
            logger.info(
                f"Tx-risk results exported to JSON file: {export_json}"
            )
    except Exception as e:
        logger.error(f"tx-risk call: {e}")


@simulate_group.command(name="tx")
@click.option("--node-url", type=str, help="Ethereum node URL")
@click.option(
    "--etherscan-api-key", type=str, help="Etherscan API key (optional)"
)
@click.option("--tx-hash", required=True, type=str, help="Transaction hash")
@click.option(
    "--from-block",
    required=False,
    type=str,
    help="On-chain scan start (optional)",
)
@click.option(
    "--to-block",
    required=False,
    type=str,
    help="On-chain scan end (optional). Defaults to block-1 of the tx",
)
@click.option(
    "--latest-offset",
    default=0,
    type=int,
    help="If set (>0) and --from-block not given, from_block = max(0, to_block - offset)",
)
@click.option("--export-json", type=str, help="Export results to JSON file")
@click.option("--log-level", default="ERROR", type=str, help="Logging level")
def simulate_tx(
    node_url,
    etherscan_api_key,
    tx_hash,
    from_block,
    to_block,
    latest_offset,
    export_json,
    log_level,
):
    """Analyze an on-chain tx via debug trace and assess tx risk targets"""
    setup_logging(log_level)
    console = Console()

    node_url = node_url or os.getenv("NODE_URL")
    if not node_url:
        console.print(
            "[red]Error: You must provide a node URL via --node-url or NODE_URL env variable.[/red]"
        )
        return

    try:
        cc = CrystalClear(
            url=node_url,
            etherscan_api_key=etherscan_api_key,
            log_level=log_level,
        )
        results = cc.simulate_from_tx(
            tx_hash,
            from_block=from_block,
            to_block=to_block,
            latest_offset=latest_offset,
        )

        table = Table(
            title="🧾 Tx Risk (On-chain Tx)", header_style="bold green"
        )
        table.add_column("Address", style="cyan")
        table.add_column("First Time", style="yellow")
        table.add_column("Verification", style="magenta")
        table.add_column("Source", style="white")

        for addr, info in results.items():
            v = info.get("verification", {}) or {}
            table.add_row(
                addr,
                "Yes" if info.get("first_time") else "No",
                str(v.get("verification", "unknown")),
                str(v.get("source", "-")),
            )

        console.print(table)

        if export_json:
            with open(export_json, "w") as f:
                json.dump(results, f, indent=4)
            logger.info(
                f"Tx-risk (tx) results exported to JSON file: {export_json}"
            )
    except Exception as e:
        logger.error(f"tx-risk tx: {e}")


if __name__ == "__main__":
    main()
