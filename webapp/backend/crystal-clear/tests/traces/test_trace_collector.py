import pytest
from unittest.mock import patch

from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from crystal_clear.traces import TraceCollector


@pytest.fixture
@patch("web3.Web3.is_connected", return_value=True)
def trace_collector(mock_is_connected):
    mock_provider = EthereumTesterProvider()
    mock_w3 = Web3(mock_provider)
    mock_w3.is_connected.return_value = True

    collector = TraceCollector(url="http://mock.ethereum.node")
    collector.w3 = mock_w3
    return collector


def test_init_connection_failure():
    with patch("web3.Web3.is_connected", return_value=False):
        with pytest.raises(ConnectionError):
            TraceCollector("http://mock.ethereum.node")


@patch.object(TraceCollector, "_filter_txs_from", return_value={"0x123", "0x456"})
@patch.object(TraceCollector, "_validate_contract", return_value=True)
@patch("web3.Web3")
def test_get_calls_from(MockWeb3, mock_validate_contract, mock_filter_txs_from, trace_collector):
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

    trace_collector.w3 = mock_w3_instance

    contract_address = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    from_block, to_block = 1000, 1005

    result = trace_collector.get_calls_from(from_block, to_block, contract_address)

    assert len(result) == 7
    assert result["address"] == contract_address
    assert result["from_block"] == from_block
    assert result["to_block"] == to_block
    assert result["n_matching_transactions"] == 2
    assert result["n_nodes"] == 2
    assert set(result["nodes"]) == {
        "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
    }
    assert result["edges"][0]["source"] == "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    assert result["edges"][0]["target"] == "0x5D27FDD96c8e4028edbAbF3D667be24769425199"
    assert result["edges"][0]["types"] == {"CALL": 2}

    mock_validate_contract.assert_called_with(
        "0x5D27FDD96c8e4028edbAbF3D667be24769425199", hex(to_block)
    )


@patch("web3.Web3")
def test_filter_txs_from(MockWeb3, trace_collector):
    mock_w3_instance = MockWeb3.return_value
    mock_w3_instance.tracing.trace_filter.return_value = [
        {"transactionHash": "0x1", "type": "call"},
        {"transactionHash": "0x2", "type": "call"},
    ]

    trace_collector.w3 = mock_w3_instance

    tx_hashes = trace_collector._filter_txs_from(1, 10, "0x123")
    assert tx_hashes == {"0x1", "0x2"}


@patch("web3.Web3")
def test_get_calls_from_tx(MockWeb3, trace_collector):
    mock_w3_instance = MockWeb3.return_value
    mock_w3_instance.geth.debug.trace_transaction.return_value = {"calls": []}

    trace_collector.w3 = mock_w3_instance

    res = trace_collector._get_calls_from_tx("0x1")
    assert res == {"calls": []}


def test_extract_all_subcalls(trace_collector):
    calls = {}
    call = {
        "from": "0x1",
        "to": "0x2",
        "type": "DELEGATECALL",
        "calls": [{"from": "0x1", "to": "0x3", "type": "CALL"}],
    }
    caller = "0x1"
    trace_collector._extract_all_subcalls(call, calls, caller)

    assert len(calls) == 2
    assert calls[("0x1", "0x2")]["source"] == "0x1"
    assert calls[("0x1", "0x2")]["target"] == "0x2"
    assert calls[("0x1", "0x2")]["types"] == {"DELEGATECALL": 1}
    assert calls[("0x1", "0x2")]["depth"] == 1

    assert calls[("0x2", "0x3")]["source"] == "0x2"
    assert calls[("0x2", "0x3")]["target"] == "0x3"
    assert calls[("0x2", "0x3")]["types"] == {"CALL": 1}
    assert calls[("0x2", "0x3")]["depth"] == 2


def test_extract_calls(trace_collector):
    calls = {}
    call = {
        "from": "0xeoa",
        "to": "0x1",
        "type": "call",
        "calls": [{"from": "0x1", "to": "0x2", "type": "call"}],
    }
    trace_collector._extract_calls(call, "0x1", calls)

    assert len(calls) == 1
    assert calls[("0x1", "0x2")]["source"] == "0x1"
    assert calls[("0x1", "0x2")]["target"] == "0x2"
    assert calls[("0x1", "0x2")]["types"] == {"call": 1}
    assert calls[("0x1", "0x2")]["depth"] == 1


@patch("web3.Web3")
def test_get_calls(MockWeb3, trace_collector):
    mock_w3_instance = MockWeb3.return_value
    mock_w3_instance.geth.debug.trace_transaction.return_value = {
        "from": "0xeoa",
        "to": "0x1",
        "type": "call",
        "calls": [{"from": "0x1", "to": "0x2", "type": "call"}],
    }

    trace_collector.w3 = mock_w3_instance

    tx_hashes = {"0xtx1"}
    calls = list(trace_collector.get_calls(tx_hashes, "0x1"))

    assert len(calls) == 1
    assert calls[0]["source"] == "0x1"
    assert calls[0]["target"] == "0x2"
    assert calls[0]["types"] == {"call": 1}
    assert calls[0]["depth"] == 1
