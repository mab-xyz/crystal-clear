import unittest
from unittest.mock import patch

from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from scsc.traces import TraceCollector


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
    @patch("web3.Web3")
    def test_get_calls_from(self, MockWeb3, mock_filter_txs_from):
        # Mock tracing.trace_filter to return sample data
        mock_w3_instance = MockWeb3.return_value
        mock_w3_instance.tracing.trace_filter.return_value = [
            {"transactionHash": "0x123", "type": "call"},
            {"transactionHash": "0x456", "type": "call"},
        ]
        mock_w3_instance.geth.debug.trace_transaction.return_value = {
            "from": "0xabc",
            "to": "0xdef",
            "type": "call",
            "calls": [],
        }

        # Assign the mock Web3 instance to the trace_collector
        self.trace_collector.w3 = mock_w3_instance

        # Test the get_calls_from method
        contract_address = "0xabc"
        from_block = 1000
        to_block = 1005
        result = self.trace_collector.get_calls_from(
            from_block, to_block, contract_address
        )

        # Verify the returned calls
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["from"], "0xabc")
        self.assertEqual(result[0]["to"], "0xdef")
        self.assertEqual(result[0]["type"], "call")

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
        calls = []
        call = {
            "from": "0x1",
            "to": "0x2",
            "type": "call",
            "calls": [{"from": "0x2", "to": "0x3", "type": "call"}],
        }
        self.trace_collector._extract_all_subcalls(call, calls)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["from"], "0x1")
        self.assertEqual(calls[1]["from"], "0x2")

    def test_extract_calls(self):
        calls = []
        call = {
            "from": "0x1",
            "to": "0x2",
            "type": "call",
            "calls": [{"from": "0x2", "to": "0x3", "type": "call"}],
        }
        self.trace_collector._extract_calls(call, "0x1", calls)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["from"], "0x1")
        self.assertEqual(calls[1]["from"], "0x2")

    @patch("web3.Web3")
    def test_get_calls(self, MockWeb3):
        # Mock geth.debug.trace_transaction to return sample data
        mock_w3_instance = MockWeb3.return_value
        mock_w3_instance.geth.debug.trace_transaction.return_value = {
            "from": "0x1",
            "to": "0x2",
            "type": "call",
        }

        # Assign the mock Web3 instance to the trace_collector
        self.trace_collector.w3 = mock_w3_instance

        # Test the get_calls method
        tx_hashes = {"0x1"}
        calls = self.trace_collector.get_calls(tx_hashes, "0x1")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["from"], "0x1")


if __name__ == "__main__":
    unittest.main()
