import pytest
from pydantic import ValidationError

from src.api.schemas.analysis import (
    AdditionalRiskFactors,
    CallEdge,
    CallGraph,
    Risk,
    RiskAnalysis,
    RiskFactors,
)


def test_risk_factors_to_dict_and_str():
    rf = RiskFactors(upgradeability=True, permissioned=True)
    assert rf.to_dict()["upgradeability"] is True
    assert "upgradeable" in str(rf)

    empty = RiskFactors()
    assert str(empty) == "No risk factors identified."


def test_call_edge_and_call_graph_validation_and_to_dict():
    edge = CallEdge(
        source="0x1111111111111111111111111111111111111111",
        target="0x2222222222222222222222222222222222222222",
        types={"CALL": 1},
    )
    assert edge.to_dict()["types"]["CALL"] == 1

    graph = CallGraph(
        address="0x1111111111111111111111111111111111111111",
        from_block=1,
        to_block=2,
        n_nodes=2,
        nodes={
            "0x1111111111111111111111111111111111111111": "A",
            "0x2222222222222222222222222222222222222222": "B",
        },
        edges=[edge],
        dependency_depths={"0x2222222222222222222222222222222222222222": 1},
        n_matching_transactions=1,
    )
    out = graph.to_dict()
    assert out["n_nodes"] == 2
    assert out["edges"][0]["source"].startswith("0x")


@pytest.mark.parametrize("field", ["source", "target"])
def test_call_edge_rejects_invalid_address(field):
    payload = {
        "source": "0x1111111111111111111111111111111111111111",
        "target": "0x2222222222222222222222222222222222222222",
        "types": {"CALL": 1},
    }
    payload[field] = "bad"

    with pytest.raises(ValidationError):
        CallEdge(**payload)


def test_additional_risk_factors_str_variants():
    arf = AdditionalRiskFactors(
        upgradeability=False,
        permissioned=False,
        repository=False,
        audits=False,
        scorecard=4.1,
    )
    s = str(arf)
    assert "not linked to a repository" in s
    assert "no associated audits" in s
    assert "low scorecard" in s


def test_risk_analysis_to_dict():
    risk = Risk(verified=True, risk_factors=RiskFactors(), details=None)
    analysis = RiskAnalysis(
        root_address="0x1111111111111111111111111111111111111111",
        from_block=1,
        to_block=2,
        dependencies=[
            {
                "address": "0x2222222222222222222222222222222222222222",
                "dependency_depth": 1,
                "verified": True,
                "risk_factors": {"upgradeability": False, "permissioned": False},
                "details": None,
            }
        ],
        aggregated_risks=risk,
    )

    out = analysis.to_dict()
    assert out["root_address"].startswith("0x")
    assert len(out["dependencies"]) == 1
