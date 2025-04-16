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

    def _add_labeled_edge(self, u, v, label):
        if self.G.has_edge(u, v):
            # If edge already exists, update the label count
            types = self.G[u][v].setdefault("types", {})
            types[label] = types.get(label, 0) + 1
        else:
            # New edge with initial label count
            self.G.add_edge(u, v, types={label: 1})

    def add_call(
        self, from_address: str, to_address: str, call_type: str
    ) -> None:
        """
        Adds a call edge to the graph.
        """
        self._add_labeled_edge(from_address, to_address, call_type)

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
