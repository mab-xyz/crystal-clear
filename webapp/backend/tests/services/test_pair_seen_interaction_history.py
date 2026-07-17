import json

import pytest

from src.api.services import pair_seen_interaction_history as history_module
from src.api.services.pair_seen_interaction_history import (
    PairSeenInteractionHistory,
)


class _Response:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self._payload


def test_has_pairs_seen_batches_and_normalizes(monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        payload = json.loads(request.data)
        requests.append((payload, timeout))
        return _Response(
            {
                "results": [
                    {
                        **pair,
                        "seenAtOrBeforeBlock": pair["source"].endswith("1"),
                    }
                    for pair in payload["pairs"]
                ]
            }
        )

    monkeypatch.setattr(history_module, "urlopen", fake_urlopen)
    client = PairSeenInteractionHistory(
        base_url="http://history.test",
        timeout_seconds=3.5,
        batch_size=1,
    )
    address_1 = "0x" + "0" * 39 + "1"
    address_2 = "0x" + "0" * 39 + "2"
    address_3 = "0x" + "0" * 39 + "3"

    result = client.has_pairs_seen(
        {
            (address_1.upper().replace("0X", "0x"), address_2),
            (address_2, address_3),
        },
        block=123,
    )

    assert result == {
        (address_1, address_2): True,
        (address_2, address_3): False,
    }
    assert len(requests) == 2
    assert all(payload["block"] == 123 for payload, _ in requests)
    assert all(timeout == 3.5 for _, timeout in requests)


def test_has_pairs_seen_rejects_partial_response(monkeypatch):
    monkeypatch.setattr(
        history_module,
        "urlopen",
        lambda *_args, **_kwargs: _Response({"results": []}),
    )
    client = PairSeenInteractionHistory(base_url="http://history.test")

    with pytest.raises(RuntimeError, match="omitted 1 requested pair"):
        client.has_pairs_seen(
            {("0x" + "1" * 40, "0x" + "2" * 40)},
            block=123,
        )
