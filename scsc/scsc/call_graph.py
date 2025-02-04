import json
import networkx as nx
from networkx.drawing.nx_pydot import write_dot

class CallGraph:
    def __init__(self, contract_address):
        self.G = nx.DiGraph()
        self.contract_address = contract_address
        self.add_contract(contract_address)

    def add_contract(self, address, data=None, metadata=None):
        self.G.add_node(address, data=data, metadata=metadata)

    def add_call(self, from_address, to_address, data=None):
        self.G.add_edge(from_address, to_address, data=data)
    
    def get_callee_contracts(self, address: str):
        return list(self.G.successors(address))

    def get_caller_contracts(self, address: str):
        return list(self.G.predecessors(address))
    
    def get_graph(self):
        return self.G.graph

    def export_dot(self, filename):
        write_dot(self.G, filename)

    def to_json(self):
        return nx.node_link_data(self.G, edges="edges")
    
    def export_json(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.to_json(), f)