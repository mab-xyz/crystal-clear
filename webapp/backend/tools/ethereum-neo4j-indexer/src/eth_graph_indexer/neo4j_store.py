"""Neo4j schema, idempotent graph writes, and checkpoint storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from neo4j import Driver
else:
    Driver = Any

from .models import BlockWrite, InteractionEdge

ADDRESS_CONSTRAINT_QUERY = """
CREATE CONSTRAINT address_unique IF NOT EXISTS
FOR (a:Address) REQUIRE a.address IS UNIQUE
""".strip()

RELATIONSHIP_CONSTRAINT_QUERY = """
CREATE CONSTRAINT interaction_unique IF NOT EXISTS
FOR ()-[r:INTERACTION]-() REQUIRE r.id IS UNIQUE
""".strip()

INTERACTION_UPSERT_QUERY = """
UNWIND $edges AS edge
MATCH (source:Address {address: edge.from})
MATCH (target:Address {address: edge.to})
MERGE (source)-[rel:INTERACTION {id: edge.id}]->(target)
SET rel.blockNumber = edge.blockNumber
""".strip()

ADDRESS_UPSERT_QUERY = """
UNWIND $addresses AS address
MERGE (:Address {address: address})
""".strip()

CHECKPOINT_QUERY = """
MERGE (checkpoint:IndexerCheckpoint {id: $id})
SET checkpoint.lastProcessedBlock = $blockNumber,
    checkpoint.lastProcessedBlockHash = $blockHash,
    checkpoint.updatedAt = datetime()
""".strip()


@dataclass(frozen=True, slots=True)
class Checkpoint:
    last_processed_block: int
    last_processed_block_hash: str


class Neo4jStore:
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        *,
        driver: Driver | None = None,
    ) -> None:
        if driver is not None:
            self._driver = driver
            return
        try:
            from neo4j import GraphDatabase
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "neo4j package is required to use Neo4jStore; install the "
                "project dependencies with `python -m pip install -e .`"
            ) from exc
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> Neo4jStore:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def verify_connectivity(self) -> None:
        self._driver.verify_connectivity()

    def ensure_schema(self) -> None:
        self._driver.execute_query(ADDRESS_CONSTRAINT_QUERY)
        self._driver.execute_query(RELATIONSHIP_CONSTRAINT_QUERY)

    def get_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        records, _, _ = self._driver.execute_query(
            """
            MATCH (checkpoint:IndexerCheckpoint {id: $id})
            RETURN checkpoint.lastProcessedBlock AS block,
                   checkpoint.lastProcessedBlockHash AS hash
            """,
            id=checkpoint_id,
        )
        if not records:
            return None
        record = records[0]
        if record["block"] is None:
            return None
        return Checkpoint(int(record["block"]), str(record["hash"] or ""))

    def write_block(
        self,
        *,
        edges: list[InteractionEdge],
        block_number: int,
        block_hash: str,
        checkpoint_id: str,
        batch_size: int,
    ) -> tuple[int, int]:
        return self.write_blocks(
            [
                BlockWrite(
                    edges=edges,
                    block_number=block_number,
                    block_hash=block_hash,
                )
            ],
            checkpoint_id=checkpoint_id,
            batch_size=batch_size,
        )

    def write_blocks(
        self,
        blocks: list[BlockWrite],
        *,
        checkpoint_id: str,
        batch_size: int,
    ) -> tuple[int, int]:
        if not blocks:
            return 0, 0
        records_by_identity = {
            record["id"]: record
            for block in blocks
            for edge in block.edges
            if (record := edge.to_record())
        }
        records = list(records_by_identity.values())
        touched = sorted(
            {
                address
                for record in records
                for address in (record["from"], record["to"])
            }
        )
        checkpoint_block = blocks[-1]

        def write(tx: Any) -> None:
            for offset in range(0, len(touched), batch_size):
                tx.run(
                    ADDRESS_UPSERT_QUERY,
                    addresses=touched[offset : offset + batch_size],
                ).consume()
            for offset in range(0, len(records), batch_size):
                tx.run(
                    INTERACTION_UPSERT_QUERY,
                    edges=records[offset : offset + batch_size],
                ).consume()
            tx.run(
                CHECKPOINT_QUERY,
                id=checkpoint_id,
                blockNumber=checkpoint_block.block_number,
                blockHash=checkpoint_block.block_hash,
            ).consume()

        with self._driver.session() as session:
            session.execute_write(write)
        return len(touched), len(records)
