from src.api.integrations import crystal_clear_adapter as adapter


class _Raw:
    def __init__(self, payload):
        self._payload = payload

    def model_dump(self):
        return self._payload


class _FakeCrystalClear:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_risk_factors(self, *args, **kwargs):
        _ = (args, kwargs)
        return _Raw(
            {
                "root_address": "0x1111111111111111111111111111111111111111",
                "from_block": None,
                "to_block": None,
                "dependencies": [],
                "aggregated_risks": {
                    "verified": True,
                    "risk_factors": {
                        "upgradeability": False,
                        "permissioned": False,
                    },
                    "details": None,
                },
            }
        )

    def simulate_and_check(self, call_object, **kwargs):
        return {"echo": call_object, "opts": kwargs}

    def simulate_from_tx(self, tx_hash, **kwargs):
        return {"tx_hash": tx_hash, "opts": kwargs}


def test_crystal_clear_risk_engine_methods(monkeypatch):
    monkeypatch.setattr(adapter, "CrystalClear", _FakeCrystalClear)

    engine = adapter.CrystalClearRiskEngine()

    assert "verification_allowlist" not in engine._client.kwargs

    risk = engine.get_risk_factors("0xabc", scope="supply-chain")
    assert risk.root_address == "0x1111111111111111111111111111111111111111"

    simulated = engine.simulate_and_check({"from": "0xabc"}, block_tag="latest")
    assert simulated["echo"]["from"] == "0xabc"

    by_tx = engine.simulate_from_tx("0xdeadbeef")
    assert by_tx["tx_hash"] == "0xdeadbeef"


def test_get_risk_engine_is_cached(monkeypatch):
    monkeypatch.setattr(adapter, "CrystalClear", _FakeCrystalClear)
    adapter.get_risk_engine.cache_clear()

    one = adapter.get_risk_engine()
    two = adapter.get_risk_engine()

    assert one is two
