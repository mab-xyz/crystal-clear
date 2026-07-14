from eth_graph_indexer.rpc import JsonRpcError, MultiJsonRpcClient, RpcCall


class FakeClient:
    def __init__(self, url: str, *, fail: bool = False) -> None:
        self.url = url
        self.fail = fail
        self.calls = []
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def call(self, method: str, params=None):
        self.calls.append((method, params))
        if self.fail:
            raise JsonRpcError("failed")
        return self.url

    def batch_call(self, calls):
        pending = list(calls)
        self.calls.append(("batch", pending))
        if self.fail:
            raise JsonRpcError("failed")
        return [self.url for _ in pending]


def test_multi_rpc_client_round_robins_calls() -> None:
    first = FakeClient("http://a:8545")
    second = FakeClient("http://b:8545")
    client = MultiJsonRpcClient([first, second])

    assert client.call("eth_blockNumber") == "http://a:8545"
    assert client.call("eth_blockNumber") == "http://b:8545"
    assert client.batch_call([RpcCall("eth_chainId", [])]) == [
        "http://a:8545"
    ]


def test_multi_rpc_client_fails_over_to_next_endpoint() -> None:
    first = FakeClient("http://a:8545", fail=True)
    second = FakeClient("http://b:8545")
    client = MultiJsonRpcClient([first, second])

    assert client.call("eth_blockNumber") == "http://b:8545"


def test_multi_rpc_client_closes_all_clients() -> None:
    first = FakeClient("http://a:8545")
    second = FakeClient("http://b:8545")
    client = MultiJsonRpcClient([first, second])

    client.close()

    assert first.closed
    assert second.closed
