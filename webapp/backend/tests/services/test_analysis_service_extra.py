import pytest

from src.api.schemas.analysis import AdditionalRisk, AdditionalRiskFactors
from src.api.services import analysis_service


class _Raw:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self):
        return self._payload


class _Engine:
    def __init__(self, payload):
        self._payload = payload

    def get_risk_factors(self, *_a, **_k):
        return _Raw(self._payload)


class _ContractService:
    def __init__(self, _session):
        pass

    async def get_contract_audits(self, _address):
        return {"audits": []}


@pytest.mark.asyncio
async def test_assess_contract_risk_and_finalize(monkeypatch):
    payload = {
        "root_address": "0x1111111111111111111111111111111111111111",
        "from_block": None,
        "to_block": None,
        "dependencies": [
            {
                "address": "0x2222222222222222222222222222222222222222",
                "dependency_depth": 1,
                "verified": True,
                "risk_factors": {"upgradeability": False, "permissioned": False},
                "details": {},
            }
        ],
        "aggregated_risks": {
            "verified": True,
            "risk_factors": {"upgradeability": False, "permissioned": False},
            "details": None,
        },
    }

    async def _score(_session, _address):
        return {"raw": {"score": 8.0}, "repo": "org/repo"}

    monkeypatch.setattr(analysis_service, "ContractService", _ContractService)
    monkeypatch.setattr(analysis_service, "get_scorecard_data", _score)

    out = await analysis_service.assess_contract_risk(
        session=object(),
        address="0x1111111111111111111111111111111111111111",
        risk_engine=_Engine(payload),
    )

    assert out.dependencies
    assert out.aggregated_risks.risk_factors.scorecard == 8.0


def test_assess_edge_risk_and_update_aggregated_risks():
    edges = [
        {"types": {"CALL": 1}},
        {"types": {"DELEGATECALL": 1}},
    ]
    scored = analysis_service.assess_edge_risk(edges)
    assert scored[0]["risk"] == "Low"
    assert scored[1]["risk"] == "High"

    agg = AdditionalRisk(
        verified=True,
        risk_factors=AdditionalRiskFactors(
            upgradeability=False,
            permissioned=False,
            repository=True,
            audits=True,
            scorecard=10.0,
        ),
        details=None,
    )
    dep = type(
        "Dep",
        (),
        {
            "risk_factors": type(
                "RF",
                (),
                {"repository": False, "audits": False, "scorecard": 2.0},
            )(),
        },
    )()

    analysis_service._update_aggregated_risks(agg, dep)
    assert agg.risk_factors.repository is False
    assert agg.risk_factors.audits is False
    assert agg.risk_factors.scorecard == 12.0


def test_finalize_scorecard_average_none_path():
    risk_analysis = type(
        "RA",
        (),
        {
            "aggregated_risks": AdditionalRisk(
                verified=True,
                risk_factors=AdditionalRiskFactors(
                    upgradeability=False,
                    permissioned=False,
                    repository=True,
                    audits=True,
                    scorecard=None,
                ),
                details=None,
            ),
            "dependencies": [1, 2],
        },
    )()

    analysis_service._finalize_scorecard_average(risk_analysis)
    assert risk_analysis.aggregated_risks.risk_factors.scorecard is None
