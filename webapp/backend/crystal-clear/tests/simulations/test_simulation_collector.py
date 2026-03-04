from unittest.mock import MagicMock, patch

import pytest

from crystal_clear import CrystalClear
from crystal_clear.clients.models import VerificationDetails
from crystal_clear.traces.adapters.trace_normalizer import from_trace_call
from crystal_clear.traces.models import CallEdge
from crystal_clear.traces.simulation_collector import SimulationCollector


def test_from_trace_call_normalizes_tree():
    traces = [
        {
            "type": "call",
            "action": {"from": "0xA", "to": "0xB", "callType": "call"},
            "traceAddress": [],
        },
        {
            "type": "call",
            "action": {"from": "0xB", "to": "0xC", "callType": "call"},
            "traceAddress": [0],
        },
    ]

    root = from_trace_call(traces)
    assert root["from"].lower() == "0xa"
    assert root["to"].lower() == "0xb"
    assert isinstance(root.get("calls"), list)
    assert len(root["calls"]) == 1
    child = root["calls"][0]
    assert child["from"].lower() == "0xb"
    assert child["to"].lower() == "0xc"


@pytest.fixture
@patch("web3.Web3.is_connected", return_value=True)
def sim_collector(mock_is_connected):
    collector = SimulationCollector(url="http://mock.node")
    # stub out validate contract to avoid code queries
    collector._validate_contract = MagicMock(return_value=True)
    return collector


def test_get_edges_from_simulation(sim_collector):
    mock_w3 = MagicMock()
    sim_collector.w3 = mock_w3
    # Provide a simple trace_call response (flat traces)
    mock_w3.tracing.trace_call.return_value = [
        {
            "type": "call",
            "action": {
                "from": "0x1111111111111111111111111111111111111111",
                "to": "0x2222222222222222222222222222222222222222",
            },
            "traceAddress": [],
        },
        {
            "type": "call",
            "action": {
                "from": "0x2222222222222222222222222222222222222222",
                "to": "0x3333333333333333333333333333333333333333",
            },
            "traceAddress": [0],
        },
    ]

    edges = sim_collector.get_edges_from_simulation(
        {
            "from": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "to": "0x1111111111111111111111111111111111111111",
        },
        block_tag="latest",
    )
    # Should produce at least one edge targeting 0x333...
    targets = {e.target.lower() for e in edges}
    assert "0x3333333333333333333333333333333333333333" in targets


def test_get_edges_from_simulation_with_synthetic_root(sim_collector):
    """trace_call returns multiple top-level frames; ensure we pick the right branch."""
    mock_w3 = MagicMock()
    sim_collector.w3 = mock_w3

    # Two top-level calls (F->R1) and (F->R2), each with their own subcall
    R1 = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    R2 = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    A = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa01"
    B = "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb01"

    mock_w3.tracing.trace_call.return_value = [
        {  # top-level: F -> R1
            "type": "call",
            "action": {
                "from": "0xfefefefefefefefefefefefefefefefefefefefe",
                "to": R1,
                "callType": "call",
            },
            "traceAddress": [],
        },
        {  # sub: R1 -> A
            "type": "call",
            "action": {"from": R1, "to": A, "callType": "call"},
            "traceAddress": [0],
        },
        {  # top-level: F -> R2
            "type": "call",
            "action": {
                "from": "0xfefefefefefefefefefefefefefefefefefefefe",
                "to": R2,
                "callType": "call",
            },
            "traceAddress": [],
        },
        {  # sub: R2 -> B
            "type": "call",
            "action": {"from": R2, "to": B, "callType": "call"},
            "traceAddress": [1],
        },
    ]

    # We request simulation targeting R2; edges should include B but not A
    edges = sim_collector.get_edges_from_simulation(
        {"from": "0x9999999999999999999999999999999999999999", "to": R2},
        block_tag="latest",
    )
    targets = {e.target.lower() for e in edges}
    assert B.lower() in targets
    assert A.lower() not in targets


def test_get_edges_from_simulation_delegatecall(sim_collector):
    """Mock trace_call to include a DELEGATECALL (proxy -> implementation) and ensure it is extracted."""
    mock_w3 = MagicMock()
    sim_collector.w3 = mock_w3

    EOA = "0x66F6F02a162243d8D4cAa7057dCCcC3D2C93673f"
    PROXY = "0xb300000b72DEAEb607a12d5f54773D1C19c7028d"
    IMPL = "0xC92652fC42602772438EbD66411F05E7CB617D3A"
    USDC = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    OTHER = "0x28561B8A2360F463011c16b6Cc0B0cbEF8dbBcad"

    # Mimic provider returning flat traces with traceAddress paths
    mock_w3.tracing.trace_call.return_value = [
        {  # Top-level EOA -> Proxy
            "type": "call",
            "action": {"from": EOA, "to": PROXY, "callType": "call"},
            "traceAddress": [],
        },
        {  # Proxy -> Impl via DELEGATECALL
            "type": "call",
            "action": {"from": PROXY, "to": IMPL, "callType": "delegatecall"},
            "traceAddress": [0],
        },
        {  # Proxy staticcall to USDC (path under first child)
            "type": "call",
            "action": {"from": PROXY, "to": USDC, "callType": "staticcall"},
            "traceAddress": [0, 0],
        },
        {  # Proxy staticcall to OTHER
            "type": "call",
            "action": {"from": PROXY, "to": OTHER, "callType": "staticcall"},
            "traceAddress": [0, 1],
        },
    ]

    # Avoid real bytecode queries; treat all targets as contracts
    sim_collector._validate_contract = MagicMock(return_value=True)

    edges = sim_collector.get_edges_from_simulation(
        {"from": EOA, "to": PROXY}, block_tag="latest"
    )
    targets = {e.target.lower() for e in edges}
    assert IMPL.lower() in targets  # delegatecall impl
    assert USDC.lower() in targets
    assert OTHER.lower() in targets


@patch("web3.Web3.is_connected", return_value=True)
def test_wrapper_simulate_and_check(mock_is_connected):
    cc = CrystalClear(
        url="http://mock.node", etherscan_api_key=None, allium_api_key="key"
    )

    # Mock edges from simulation
    e1 = CallEdge(
        source="0x1111111111111111111111111111111111111111",
        target="0x4444444444444444444444444444444444444444",
        types={"CALL": 1},
    )
    e2 = CallEdge(
        source="0x1111111111111111111111111111111111111111",
        target="0x5555555555555555555555555555555555555555",
        types={"CALL": 1},
    )
    cc.simulation_collector.get_edges_from_simulation = MagicMock(
        return_value=[e1, e2]
    )
    cc._batch_first_time = MagicMock(
        return_value={
            "0x1111111111111111111111111111111111111111": True,
            "0x4444444444444444444444444444444444444444": True,
            "0x5555555555555555555555555555555555555555": True,
        }
    )
    # Always say verified via Sourcify
    cc.sourcify_client.check_contract_verified = MagicMock(
        side_effect=lambda addr: VerificationDetails(
            address=addr,
            verification="verified",
            verifiedAt="N/A",
            source="sourcify",
        )
    )

    res = cc.simulate_and_check(
        {
            "from": "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "to": "0x1111111111111111111111111111111111111111",
        },
        block_tag="latest",
    )
    # Ensure both targets are present and carry flags
    assert "0x4444444444444444444444444444444444444444" in res
    assert (
        res["0x4444444444444444444444444444444444444444"]["first_time"] is True
    )
    assert (
        res["0x4444444444444444444444444444444444444444"]["verification"][
            "verification"
        ]
        == "verified"
    )
    assert "0x5555555555555555555555555555555555555555" in res
