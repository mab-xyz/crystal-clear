from eth_graph_indexer.models import InteractionEdge
from eth_graph_indexer.neo4j_store import (
    ADDRESS_CONSTRAINT_QUERY,
    ADDRESS_UPSERT_QUERY,
    INTERACTION_UPSERT_QUERY,
    RELATIONSHIP_CONSTRAINT_QUERY,
    Neo4jStore,
)


def test_address_constraint_is_unique() -> None:
    assert "a.address IS UNIQUE" in ADDRESS_CONSTRAINT_QUERY


def test_relationship_merge_uses_unique_relationship_id() -> None:
    query = " ".join(INTERACTION_UPSERT_QUERY.split())
    assert "MATCH (source:Address {address: edge.from})" in query
    assert "MATCH (target:Address {address: edge.to})" in query
    assert "MERGE (source)-[rel:INTERACTION {id: edge.id}]" in query
    assert "SET rel.blockNumber = edge.blockNumber" in query
    assert "txHash" not in query
    assert "fromAddress" not in query
    assert "toAddress" not in query
    assert "interactionType" not in query
    assert "valueWei" not in query


def test_relationship_constraint_is_unique() -> None:
    assert "r.id IS UNIQUE" in RELATIONSHIP_CONSTRAINT_QUERY


def test_addresses_are_upserted_separately() -> None:
    query = " ".join(ADDRESS_UPSERT_QUERY.split())
    assert "UNWIND $addresses AS address" in query
    assert "MERGE (:Address {address: address})" in query


def test_relationship_only_stores_block_number() -> None:
    merge_section = INTERACTION_UPSERT_QUERY.split(
        "MERGE (source)-[rel:INTERACTION", 1
    )[1].split("]->(target)", 1)[0]
    assert "id" in merge_section
    assert "txHash" not in merge_section
    assert "fromAddress" not in merge_section
    assert "toAddress" not in merge_section


class FakeResult:
    def consume(self) -> None:
        pass


class FakeTx:
    def __init__(self) -> None:
        self.runs = []

    def run(self, query, **kwargs):
        self.runs.append((query, kwargs))
        return FakeResult()


class FakeSession:
    def __init__(self, tx: FakeTx) -> None:
        self.tx = tx

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        pass

    def execute_write(self, callback) -> None:
        callback(self.tx)


class FakeDriver:
    def __init__(self) -> None:
        self.tx = FakeTx()

    def session(self):
        return FakeSession(self.tx)

    def close(self) -> None:
        pass


def test_store_collapses_repeated_same_block_interactions() -> None:
    source = "0x" + "a" * 40
    target = "0x" + "b" * 40
    edges = [
        InteractionEdge("0x01", 123, source, target, "external", "1"),
        InteractionEdge("0x02", 123, source, target, "external", "2"),
    ]
    driver = FakeDriver()
    store = Neo4jStore(
        "bolt://localhost:7687", "neo4j", "secret", driver=driver
    )

    nodes, relationships = store.write_block(
        edges=edges,
        block_number=123,
        block_hash="0xblock",
        checkpoint_id="default",
        batch_size=100,
    )

    address_run = driver.tx.runs[0]
    interaction_run = driver.tx.runs[1]
    assert len(address_run[1]["addresses"]) == 2
    assert len(interaction_run[1]["edges"]) == 1
    assert interaction_run[1]["edges"][0]["id"] == f"{source}:{target}:123"
    assert nodes == 2
    assert relationships == 1
