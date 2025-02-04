from trace_collector import TraceCollector
from call_graph import CallGraph

class SupplyChain:
    def __init__(self, url, contract_address):
        self.tc = TraceCollector(url)
        self.cg = CallGraph(contract_address)
    
    def collect_calls(self, from_block, to_block):
        calls = self.tc.get_calls_from(from_block, to_block, self.cg.contract_address)
        for c in calls:
            self.cg.add_call(c['from'], c['to'], data=c['type'])
    
    def export_dot(self, filename):
        self.cg.export_dot(filename)
    
    def export_json(self, filename):
        self.cg.export_json(filename)