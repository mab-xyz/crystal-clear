import json
from typing import Any, Dict, List

import networkx as nx
from networkx.drawing.nx_pydot import write_dot


class CallGraph:
    """
    Represents a call graph for a smart contract.
    """

    def __init__(self, contract_address: str):
        """
        Initializes the CallGraph with a contract address.
        """
        self.G = nx.DiGraph()
        self.contract_address = contract_address
        self.add_contract(contract_address)

    def add_contract(
        self, address: str, data: Any = None, metadata: Dict[str, Any] = None
    ) -> None:
        """
        Adds a contract node to the graph.
        """
        self.G.add_node(address, data=data, metadata=metadata)

    def add_call(
        self, from_address: str, to_address: str, data: Any = None
    ) -> None:
        """
        Adds a call edge to the graph.
        """
        self.G.add_edge(from_address, to_address, data=data)

    def get_all_contracts(self) -> List[str]:
        """
        Returns a list of all contracts in the graph.
        """
        return list(self.G.nodes())

    def get_callee_contracts(self, address: str) -> List[str]:
        """
        Returns a list of contracts called by the given address.
        """
        return list(self.G.successors(address))

    def get_caller_contracts(self, address: str) -> List[str]:
        """
        Returns a list of contracts that called the given address.
        """
        return list(self.G.predecessors(address))

    def get_graph(self) -> nx.DiGraph:
        """
        Returns the graph object.
        """
        return self.G.graph

    def export_dot(self, filename: str) -> None:
        """
        Exports the graph to a DOT file.
        """
        write_dot(self.G, filename)

    def to_json(self) -> Dict[str, Any]:
        """
        Converts the graph to a JSON serializable format.
        """
        return nx.node_link_data(self.G, edges="edges")

    def export_json(self, filename: str) -> None:
        """
        Exports the graph to a JSON file.
        """
        with open(filename, "w") as f:
            json.dump(self.to_json(), f)
