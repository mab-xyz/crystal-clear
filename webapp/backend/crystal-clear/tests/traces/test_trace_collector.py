import unittest
from unittest.mock import patch

from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from crystal_clear.traces import TraceCollector


class TestTraceCollector(unittest.TestCase):
    @patch("web3.Web3.is_connected", return_value=True)
    def setUp(self, mock_is_connected):
        # Use EthereumTesterProvider instead of HTTPProvider
        self.mock_provider = EthereumTesterProvider()

        # Create a Web3 instance using EthereumTesterProvider
        self.mock_w3 = Web3(self.mock_provider)
        self.mock_w3.is_connected.return_value = True

        # Instantiate TraceCollector with a mock URL and log level
        self.trace_collector = TraceCollector(url="http://mock.ethereum.node")

        self.trace_collector.w3 = self.mock_w3

    def test_init_connection_failure(self):
        with patch("web3.Web3.is_connected", return_value=False):
            with self.assertRaises(ConnectionError):
                TraceCollector("http://mock.ethereum.node")

    @patch.object(
        TraceCollector, "_filter_txs_from", return_value={"0x123", "0x456"}
    )
    @patch.object(TraceCollector, "_validate_contract", return_value=True)
    @patch("web3.Web3")
    def test_get_calls_from(
        self, MockWeb3, mock_validate_contract, mock_filter_txs_from
    ):
        # Mock tracing.trace_filter to return sample data
        mock_w3_instance = MockWeb3.return_value
        mock_w3_instance.tracing.trace_filter.return_value = [
            {"transactionHash": "0x123", "type": "call"},
            {"transactionHash": "0x456", "type": "call"},
        ]
        mock_w3_instance.geth.debug.trace_transaction.return_value = {
            "from": "0xcf5Ef58EE0dee71FE010aBFCFd00917fbCC3c569",
            "to": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "type": "CALL",
            "calls": [
                {
                    "from": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                    "to": "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
                    "type": "CALL",
                }
            ],
        }

        # Assign the mock Web3 instance to the trace_collector
        self.trace_collector.w3 = mock_w3_instance

        # Test the get_calls_from method
        contract_address = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
        from_block = 1000
        to_block = 1005
        result = self.trace_collector.get_calls_from(
            from_block, to_block, contract_address
        )
        # Verify the returned calls
        self.assertEqual(len(result), 7)
        self.assertEqual(result["contract_address"], contract_address)
        self.assertEqual(result["from_block"], from_block)
        self.assertEqual(result["to_block"], to_block)
        self.assertEqual(result["n_matching_transactions"], 2)
        self.assertEqual(result["n_nodes"], 2)
        self.assertEqual(
            set(result["nodes"]),
            {
                "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
            },
        )
        self.assertEqual(result["edges"][0]["source"], "0xE592427A0AEce92De3Edee1F18E0157C05861564")
        self.assertEqual(result["edges"][0]["target"], "0x5D27FDD96c8e4028edbAbF3D667be24769425199")
        self.assertEqual(result["edges"][0]["types"], {"CALL": 2})

        # Verify that _validate_contract was called
        mock_validate_contract.assert_called_with("0x5D27FDD96c8e4028edbAbF3D667be24769425199", hex(to_block))

    @patch("web3.Web3")
    def test_filter_txs_from(self, MockWeb3):
        # Mock tracing.trace_filter to return sample data
        mock_w3_instance = MockWeb3.return_value
        mock_w3_instance.tracing.trace_filter.return_value = [
            {"transactionHash": "0x1", "type": "call"},
            {"transactionHash": "0x2", "type": "call"},
        ]

        # Assign the mock Web3 instance to the trace_collector
        self.trace_collector.w3 = mock_w3_instance

        # Test the _filter_txs_from method
        tx_hashes = self.trace_collector._filter_txs_from(1, 10, "0x123")
        self.assertEqual(tx_hashes, {"0x1", "0x2"})

    @patch("web3.Web3")
    def test_get_calls_from_tx(self, MockWeb3):
        # Mock geth.debug.trace_transaction to return sample data
        mock_w3_instance = MockWeb3.return_value
        mock_w3_instance.geth.debug.trace_transaction.return_value = {
            "calls": []
        }

        # Assign the mock Web3 instance to the trace_collector
        self.trace_collector.w3 = mock_w3_instance

        # Test the _get_calls_from_tx method
        res = self.trace_collector._get_calls_from_tx("0x1")
        self.assertEqual(res, {"calls": []})

    def test_extract_all_subcalls(self):
        calls = {}
        call = {
            "from": "0x1",
            "to": "0x2",
            "type": "DELEGATECALL",
            "calls": [{"from": "0x1", "to": "0x3", "type": "CALL"}],
        }
        caller = "0x1"
        self.trace_collector._extract_all_subcalls(call, calls, caller)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[("0x1", "0x2")]["source"], "0x1")
        self.assertEqual(calls[("0x1", "0x2")]["target"], "0x2")
        self.assertEqual(calls[("0x1", "0x2")]["types"], {"DELEGATECALL": 1})
        self.assertEqual(calls[("0x1", "0x2")]["depth"], 1)

        self.assertEqual(calls[("0x2", "0x3")]["source"], "0x2")
        self.assertEqual(calls[("0x2", "0x3")]["target"], "0x3")
        self.assertEqual(calls[("0x2", "0x3")]["types"], {"CALL": 1})
        self.assertEqual(calls[("0x2", "0x3")]["depth"], 2)

    def test_extract_calls(self):
        calls = {}
        call = {
            "from": "0xeoa",
            "to": "0x1",
            "type": "call",
            "calls": [{"from": "0x1", "to": "0x2", "type": "call"}],
        }
        self.trace_collector._extract_calls(call, "0x1", calls)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[("0x1", "0x2")]["source"], "0x1")
        self.assertEqual(calls[("0x1", "0x2")]["target"], "0x2")
        self.assertEqual(calls[("0x1", "0x2")]["types"], {"call": 1})
        self.assertEqual(calls[("0x1", "0x2")]["depth"], 1)

    @patch("web3.Web3")
    def test_get_calls(self, MockWeb3):
        # Mock geth.debug.trace_transaction to return sample data
        mock_w3_instance = MockWeb3.return_value
        mock_w3_instance.geth.debug.trace_transaction.return_value = {
            "from": "0xeoa",
            "to": "0x1",
            "type": "call",
            "calls": [{"from": "0x1", "to": "0x2", "type": "call"}],
        }

        # Assign the mock Web3 instance to the trace_collector
        self.trace_collector.w3 = mock_w3_instance

        # Test the get_calls method
        tx_hashes = {"0xtx1"}
        calls = self.trace_collector.get_calls(tx_hashes, "0x1")
        calls = list(calls)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["source"], "0x1")
        self.assertEqual(calls[0]["target"], "0x2")
        self.assertEqual(calls[0]["types"], {"call": 1})
        self.assertEqual(calls[0]["depth"], 1)


if __name__ == "__main__":
    unittest.main()
