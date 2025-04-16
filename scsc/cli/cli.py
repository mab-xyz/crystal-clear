import logging

import click

from cli.app import create_app
from scsc.supply_chain import SupplyChain


@click.group()
def main():
    """Smart Contract Supply Chain Analysis Tool"""
    pass


@main.command(name="analyze")
@click.option(
    "--url",
    default="http://localhost:8545",
    type=str,
    help="Ethereum node URL",
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
def analyze(
    url, address, from_block, to_block, export_dot, export_json, log_level
):
    """Analyze contract calls and generate dependency graph"""
    logging.basicConfig(level=log_level.upper())
    logger = logging.getLogger(__name__)

    try:
        supply_chain = SupplyChain(url, address)
        supply_chain.collect_calls(from_block, to_block)

        print(f"Contract address: {address}")
        print("Called addresses:")
        for dep in supply_chain.get_all_dependencies():
            print(dep)
        print(f"Total addresses: {len(supply_chain.get_all_dependencies())}")

        if export_dot:
            supply_chain.export_dot(export_dot)
            logger.info(f"Call graph exported to DOT file: {export_dot}")

        if export_json:
            supply_chain.export_json(export_json)
            logger.info(f"Call graph exported to JSON file: {export_json}")
    except Exception as e:
        logger.error(f"analyze: {e}")


@main.command(name="web")
@click.option(
    "--url",
    default="http://localhost:8545",
    type=str,
    help="Ethereum node URL",
)
@click.option("--address", required=True, type=str, help="Contract address")
@click.option(
    "--from-block", required=True, type=str, help="Starting block number"
)
@click.option(
    "--to-block", required=True, type=str, help="Ending block number"
)
@click.option("--port", default=8050, type=int, help="Web server port")
@click.option("--debug", is_flag=True, help="Run in debug mode")
def web(url, address, from_block, to_block, port, debug):
    """Launch web interface to visualize contract calls"""
    app = create_app(url, address, from_block, to_block)
    app.run_server(debug=debug, port=port)


if __name__ == "__main__":
    main()
