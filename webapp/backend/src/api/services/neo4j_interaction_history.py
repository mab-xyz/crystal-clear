from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterable, Literal

from src.api.core.config import settings

InteractionMode = Literal["direct", "transitive"]
InteractionKey = tuple[str, str, InteractionMode]


def _normalize_address(address: str | None) -> str | None:
    if not address:
        return None
    value = address.strip().lower()
    if value.startswith("0x"):
        value = value[2:]
    if len(value) != 40:
        return None
    try:
        bytes.fromhex(value)
    except ValueError:
        return None
    return "0x" + value


def _address_bytes(address: str) -> bytes:
    normalized = _normalize_address(address)
    if not normalized:
        raise ValueError(f"invalid Ethereum address: {address}")
    return bytes.fromhex(normalized[2:])


class Neo4jInteractionHistory:
    """Queries the pre-indexed interaction graph for prior interactions."""

    def __init__(self, *, driver: Any | None = None) -> None:
        if driver is not None:
            self._driver = driver
            return
        if not settings.neo4j_uri or not settings.neo4j_password:
            raise RuntimeError("Neo4j interaction history is not configured")
        try:
            from neo4j import GraphDatabase
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "neo4j package is required for Neo4j interaction history"
            ) from exc
        self._driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self) -> None:
        self._driver.close()

    def has_interactions_many(
        self,
        entries: Iterable[InteractionKey],
        *,
        to_block: int | None = None,
    ) -> dict[InteractionKey, bool]:
        direct_pairs: list[dict[str, Any]] = []
        transitive_pairs: list[dict[str, Any]] = []
        for from_address, to_address, mode in entries:
            from_norm = _normalize_address(from_address)
            to_norm = _normalize_address(to_address)
            if not from_norm or not to_norm:
                continue
            pair = {
                "from": _address_bytes(from_norm),
                "to": _address_bytes(to_norm),
                "from_hex": from_norm,
                "to_hex": to_norm,
            }
            if mode == "direct":
                direct_pairs.append(pair)
            else:
                transitive_pairs.append(pair)

        found: dict[InteractionKey, bool] = {}
        if direct_pairs:
            found.update(
                self._run_many(
                    direct_pairs,
                    mode="direct",
                    to_block=to_block,
                )
            )
        if transitive_pairs:
            found.update(
                self._run_many(
                    transitive_pairs,
                    mode="transitive",
                    to_block=to_block,
                )
            )
        return found

    def _run_many(
        self,
        pairs: list[dict[str, Any]],
        *,
        mode: InteractionMode,
        to_block: int | None,
    ) -> dict[InteractionKey, bool]:
        if mode == "direct":
            query = """
            UNWIND $pairs AS pair
            RETURN pair.from_hex AS from_address,
                   pair.to_hex AS to_address,
                   EXISTS {
                     MATCH (:Address {address: pair.from})-[r:INTERACTION]->(:Address {address: pair.to})
                     WHERE $to_block IS NULL OR r.blockNumber <= $to_block
                   } AS found
            """
        else:
            query = """
            UNWIND $pairs AS pair
            RETURN pair.from_hex AS from_address,
                   pair.to_hex AS to_address,
                   EXISTS {
                     MATCH p = (:Address {address: pair.from})-[:INTERACTION*1..]->(:Address {address: pair.to})
                     WHERE $to_block IS NULL
                        OR all(rel IN relationships(p) WHERE rel.blockNumber <= $to_block)
                   } AS found
            """

        kwargs = {}
        if settings.neo4j_database:
            kwargs["database"] = settings.neo4j_database
        with self._driver.session(**kwargs) as session:
            records = session.run(
                query,
                pairs=pairs,
                to_block=to_block,
            )
            return {
                (
                    record["from_address"],
                    record["to_address"],
                    mode,
                ): bool(record["found"])
                for record in records
            }


@lru_cache(maxsize=1)
def get_neo4j_interaction_history() -> Neo4jInteractionHistory:
    return Neo4jInteractionHistory()


__all__ = [
    "InteractionKey",
    "InteractionMode",
    "Neo4jInteractionHistory",
    "get_neo4j_interaction_history",
]
