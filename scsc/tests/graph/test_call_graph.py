import json
import os
import shutil
import unittest

from scsc.graph import CallGraph


class TestCallGraph(unittest.TestCase):

    def setUp(self):
        self.contract_address = "0x123"
        self.call_graph = CallGraph(self.contract_address)
        self.test_dir = "test_output"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_add_contract(self):
        address = "0x456"
        self.call_graph.add_contract(
            address, data="TestData", metadata={"key": "value"}
        )
        node_data = self.call_graph.G.nodes[address]
        self.assertEqual(node_data["data"], "TestData")
        self.assertEqual(node_data["metadata"], {"key": "value"})

    def test_add_call(self):
        from_address = "0x123"
        to_address = "0x456"
        self.call_graph.add_call(from_address, to_address, data="CallData")
        edge_data = self.call_graph.G.edges[from_address, to_address]
        self.assertEqual(edge_data["data"], "CallData")

    def test_get_callee_contracts(self):
        from_address = "0x123"
        to_address = "0x456"
        self.call_graph.add_call(from_address, to_address)
        callees = self.call_graph.get_callee_contracts(from_address)
        self.assertIn(to_address, callees)

    def test_get_caller_contracts(self):
        from_address = "0x123"
        to_address = "0x456"
        self.call_graph.add_call(from_address, to_address)
        callers = self.call_graph.get_caller_contracts(to_address)
        self.assertIn(from_address, callers)

    def test_export_dot(self):
        filename = os.path.join(self.test_dir, "test.dot")
        self.call_graph.export_dot(filename)
        with open(filename, "r") as f:
            content = f.read()
        self.assertIn("digraph", content)

    def test_export_json(self):
        filename = os.path.join(self.test_dir, "test.json")
        self.call_graph.export_json(filename)
        with open(filename, "r") as f:
            content = json.load(f)
        self.assertIn("nodes", content)
        self.assertIn("edges", content)


if __name__ == "__main__":
    unittest.main()
