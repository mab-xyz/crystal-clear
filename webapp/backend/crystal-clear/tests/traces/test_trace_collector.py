from unittest.mock import MagicMock, patch

import pytest
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from crystal_clear.traces import CallGraph, TraceCollector


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


@patch.object(
    TraceCollector, "_filter_txs_from", return_value={"0x123", "0x456"}
)
@patch.object(TraceCollector, "_validate_contract", return_value=True)
@patch("web3.Web3")
def test_get_calls_from(
    MockWeb3, mock_validate_contract, mock_filter_txs_from, trace_collector
):
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

    result: CallGraph = trace_collector.get_calls_from(
        from_block, to_block, contract_address
    )
    assert result.address == contract_address
    assert result.from_block == from_block
    assert result.to_block == to_block
    assert result.n_matching_transactions == 2
    assert result.n_nodes == 2
    assert set(result.nodes) == {
        "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
    }

    assert (
        result.edges[0].source == "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    )
    assert (
        result.edges[0].target == "0x5D27FDD96c8e4028edbAbF3D667be24769425199"
    )
    assert result.edges[0].types == {"CALL": 2}
    assert len(result.dependency_depths) == 1
    address = "0x5D27FDD96c8e4028edbAbF3D667be24769425199".lower()
    assert result.dependency_depths[address] == 1

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
def test_filter_txs_from_collects_unique_transactions_before_capping(
    MockWeb3, trace_collector
):
    mock_w3_instance = MockWeb3.return_value
    duplicate_traces = [
        {"transactionHash": "0xdup", "type": "call"} for _ in range(100)
    ]
    mock_w3_instance.tracing.trace_filter.side_effect = [
        duplicate_traces,
        [{"transactionHash": "0xnext", "type": "call"}],
    ]

    trace_collector.w3 = mock_w3_instance

    tx_hashes = trace_collector._filter_txs_from(1, 10, "0x123")

    assert tx_hashes == {"0xdup", "0xnext"}
    assert mock_w3_instance.tracing.trace_filter.call_args_list[0].args[0][
        "after"
    ] == 0
    assert mock_w3_instance.tracing.trace_filter.call_args_list[0].args[0][
        "count"
    ] == 100
    assert mock_w3_instance.tracing.trace_filter.call_args_list[1].args[0][
        "after"
    ] == 100


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
        "from": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        "to": "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
        "type": "DELEGATECALL",
        "calls": [
            {
                "from": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "to": "0xf89d7b9c864f589bbF53a82105107622B35EaA40",
                "type": "CALL",
            }
        ],
    }
    caller = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    trace_collector._extract_all_subcalls(call, calls, caller)

    assert len(calls) == 2
    assert (
        calls[
            (
                "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
            )
        ].source
        == "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    )
    assert (
        calls[
            (
                "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
            )
        ].target
        == "0x5D27FDD96c8e4028edbAbF3D667be24769425199"
    )
    assert calls[
        (
            "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
        )
    ].types == {"DELEGATECALL": 1}

    assert (
        calls[
            (
                "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
                "0xf89d7b9c864f589bbF53a82105107622B35EaA40",
            )
        ].source
        == "0x5D27FDD96c8e4028edbAbF3D667be24769425199"
    )
    assert (
        calls[
            (
                "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
                "0xf89d7b9c864f589bbF53a82105107622B35EaA40",
            )
        ].target
        == "0xf89d7b9c864f589bbF53a82105107622B35EaA40"
    )
    assert calls[
        (
            "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
            "0xf89d7b9c864f589bbF53a82105107622B35EaA40",
        )
    ].types == {"CALL": 1}


def test_extract_calls(trace_collector):
    calls = {}
    call = {
        "from": "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d",
        "to": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        "type": "call",
        "calls": [
            {
                "from": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "to": "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
                "type": "call",
            }
        ],
    }
    trace_collector._extract_calls(
        call, "0xE592427A0AEce92De3Edee1F18E0157C05861564", calls
    )

    assert len(calls) == 1
    assert (
        calls[
            (
                "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
            )
        ].source
        == "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    )
    assert (
        calls[
            (
                "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
            )
        ].target
        == "0x5D27FDD96c8e4028edbAbF3D667be24769425199"
    )
    assert calls[
        (
            "0xE592427A0AEce92De3Edee1F18E0157C05861564",
            "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
        )
    ].types == {"call": 1}


@patch("web3.Web3")
def test_get_calls(MockWeb3, trace_collector):
    mock_w3_instance = MockWeb3.return_value
    mock_w3_instance.geth.debug.trace_transaction.return_value = {
        "from": "0xeoa",
        "to": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        "type": "call",
        "calls": [
            {
                "from": "0xE592427A0AEce92De3Edee1F18E0157C05861564",
                "to": "0x5D27FDD96c8e4028edbAbF3D667be24769425199",
                "type": "call",
            }
        ],
    }

    trace_collector.w3 = mock_w3_instance

    tx_hashes = {"0xtx1"}
    calls = list(
        trace_collector.get_calls(
            tx_hashes, "0xE592427A0AEce92De3Edee1F18E0157C05861564"
        )
    )

    assert len(calls) == 1
    assert calls[0].source == "0xE592427A0AEce92De3Edee1F18E0157C05861564"
    assert calls[0].target == "0x5D27FDD96c8e4028edbAbF3D667be24769425199"
    assert calls[0].types == {"call": 1}

    @patch.object(TraceCollector, "_filter_txs_from", return_value={"0x123"})
    @patch.object(TraceCollector, "_validate_contract", return_value=True)
    @patch.object(TraceCollector, "_get_calls_from_tx")
    @patch.object(TraceCollector, "_filter_contract_calls")
    def test_get_calls_from(
        mock_filter_contract_calls,
        mock_get_calls_from_tx,
        mock_validate_contract,
        mock_filter_txs_from,
        trace_collector,
    ):
        # Mock call trace result
        call_trace = {
            "from": "0xAAA",
            "to": "0xBBB",
            "type": "CALL",
            "calls": [],
        }
        mock_get_calls_from_tx.return_value = call_trace

        # Mock filter_contract_calls returns one CallEdge
        from api.models import CallEdge  # adjust if located elsewhere

        edge = CallEdge(source="0xAAA", target="0xBBB", types={"CALL": 1})
        mock_filter_contract_calls.return_value = [edge]

        result: CallGraph = trace_collector.get_calls_from(1, 2, "0xAAA")

        assert isinstance(result, CallGraph)
        assert result.address == "0xAAA"
        assert result.from_block == 1
        assert result.to_block == 2
        assert result.n_nodes == 2
        assert result.n_matching_transactions == 1
        assert set(result.nodes) == {"0xAAA", "0xBBB"}
        assert result.edges[0].source == "0xAAA"
        assert result.edges[0].target == "0xBBB"
        assert result.dependency_depths["0xbbb"] == 1

    @patch.object(TraceCollector, "get_calls_from")
    def test_get_call_graph_with_defaults(
        mock_get_calls_from, trace_collector
    ):
        # Pretend latest block = 200, so from=195, to=200
        trace_collector.w3.eth.block_number = 200

        dummy_graph = MagicMock(spec=CallGraph)
        mock_get_calls_from.return_value = dummy_graph

        result = trace_collector.get_call_graph(
            "0xAAA", from_block=None, to_block=None, blocks=5
        )

        assert result is dummy_graph
        mock_get_calls_from.assert_called_once_with(195, 200, "0xAAA")
