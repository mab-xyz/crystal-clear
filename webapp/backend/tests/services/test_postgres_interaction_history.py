import pytest

from src.api.services.postgres_interaction_history import (
    PostgresInteractionHistory,
)


class _Scalars:
    def __init__(self, values):
        self._values = values

    def __iter__(self):
        return iter(self._values)


class _Result:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _Scalars(self._values)


class _Session:
    def __init__(self):
        self.queries = []

    def execute(self, statement, params):
        self.queries.append((str(statement), params))
        return _Result([0] if params["source_0"][-1] == 1 else [])


def test_has_pairs_seen_batches_normalizes_and_binds_bytes():
    session = _Session()
    history = PostgresInteractionHistory(batch_size=1)
    address_1 = "0x" + "0" * 39 + "1"
    address_2 = "0x" + "0" * 39 + "2"
    address_3 = "0x" + "0" * 39 + "3"

    result = history.has_pairs_seen(
        session,
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
    assert len(session.queries) == 2
    assert all(params["block"] == 123 for _, params in session.queries)
    assert all(isinstance(params["source_0"], bytes) for _, params in session.queries)
    assert all("public.pair_ranges" in query for query, _ in session.queries)


def test_has_pairs_seen_rejects_invalid_input():
    history = PostgresInteractionHistory()

    with pytest.raises(ValueError, match="history block"):
        history.has_pairs_seen(_Session(), set(), block=-1)

    with pytest.raises(ValueError, match="invalid interaction pair"):
        history.has_pairs_seen(
            _Session(),
            {("invalid", "0x" + "2" * 40)},
            block=123,
        )
