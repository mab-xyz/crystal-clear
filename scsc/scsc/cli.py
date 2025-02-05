import logging

import click

from scsc.supply_chain import SupplyChain


@click.command()
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
def main(
    url, address, from_block, to_block, export_dot, export_json, log_level
):
    logging.basicConfig(level=log_level.upper())
    logger = logging.getLogger(__name__)

    supply_chain = SupplyChain(url, address)
    supply_chain.collect_calls(from_block, to_block)

    for dep in supply_chain.get_all_dependencies():
        print(dep)

    if export_dot:
        supply_chain.export_dot(export_dot)
        logger.info(f"Call graph exported to DOT file: {export_dot}")

    if export_json:
        supply_chain.export_json(export_json)
        logger.info(f"Call graph exported to JSON file: {export_json}")


if __name__ == "__main__":
    main()
