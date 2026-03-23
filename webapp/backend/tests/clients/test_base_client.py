import requests

from src.api.clients.base_client import BaseClient


class _Resp:
    def __init__(self, payload=None, should_raise=False):
        self._payload = payload or {}
        self._raise = should_raise

    def raise_for_status(self):
        if self._raise:
            raise requests.exceptions.RequestException("boom")

    def json(self):
        return self._payload


def test_make_request_success(monkeypatch):
    monkeypatch.setattr(
        "src.api.clients.base_client.requests.request",
        lambda *_a, **_k: _Resp({"ok": True}),
    )
    client = BaseClient("https://example.com/", "k")

    out = client._make_request("GET", "/v1/test")

    assert out == {"ok": True}


def test_make_request_failure_returns_none(monkeypatch):
    monkeypatch.setattr(
        "src.api.clients.base_client.requests.request",
        lambda *_a, **_k: _Resp(should_raise=True),
    )
    client = BaseClient("https://example.com", "k")

    out = client._make_request("GET", "v1/test")

    assert out is None


def test_get_and_post_wrappers(monkeypatch):
    calls = []

    def _fake(self, method, endpoint, **kwargs):
        calls.append((method, endpoint, kwargs))
        return {"ok": True}

    monkeypatch.setattr(BaseClient, "_make_request", _fake)

    client = BaseClient("https://example.com", "k")

    assert client.get("/a", params={"x": 1}) == {"ok": True}
    assert client.post("/b", {"y": 2}) == {"ok": True}

    assert calls[0][0] == "GET"
    assert calls[1][0] == "POST"
