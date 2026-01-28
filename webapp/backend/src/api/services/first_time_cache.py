from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional, Tuple

from sqlalchemy import tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select

from src.api.core.config import settings
from src.api.core.database import engine
from src.api.models.first_interaction import FirstInteraction


class FirstInteractionCache:
    """Database-backed cache for first-time interaction checks."""

    def __init__(self, ttl_seconds: Optional[int] = None) -> None:
        self._engine = engine
        self._ttl_seconds = (
            ttl_seconds
            if ttl_seconds is not None
            else int(settings.first_time_cache_ttl_seconds)
        )

    @staticmethod
    def _normalize_address(address: str | None) -> Optional[str]:
        if not address:
            return None
        addr = address.strip().lower()
        if not addr.startswith("0x"):
            return None
        return addr

    def _now(self) -> datetime:
        return datetime.utcnow()

    def get_many(
        self,
        entries: Iterable[Tuple[str, str, int, int, Optional[int]]],
    ) -> dict[Tuple[str, str, int, int, Optional[int]], bool]:
        normalized_entries = []
        for from_address, to_address, from_block, to_block, latest_offset in entries:
            f_addr = self._normalize_address(from_address)
            t_addr = self._normalize_address(to_address)
            if not f_addr or not t_addr:
                continue
            normalized_entries.append(
                (f_addr, t_addr, from_block, to_block, latest_offset)
            )

        if not normalized_entries:
            return {}

        now = self._now()
        with Session(self._engine) as session:
            stmt = select(FirstInteraction).where(
                tuple_(
                    FirstInteraction.from_address,
                    FirstInteraction.to_address,
                    FirstInteraction.from_block,
                    FirstInteraction.to_block,
                    FirstInteraction.latest_offset,
                ).in_(normalized_entries)
            )
            rows = session.exec(stmt).all()

        results: dict[
            Tuple[str, str, int, int, Optional[int]], bool
        ] = {}
        for record in rows:
            if record.expires_at and record.expires_at <= now:
                continue
            key = (
                record.from_address,
                record.to_address,
                record.from_block,
                record.to_block,
                record.latest_offset,
            )
            results[key] = bool(record.is_first_time)
        return results

    def get(
        self,
        from_address: str,
        to_address: str,
        from_block: int,
        to_block: int,
        latest_offset: Optional[int],
    ) -> Optional[bool]:
        f_addr = self._normalize_address(from_address)
        t_addr = self._normalize_address(to_address)
        if not f_addr or not t_addr:
            return None
        key = (f_addr, t_addr, from_block, to_block, latest_offset)
        entries = self.get_many([key])
        return entries.get(key)

    def set(
        self,
        from_address: str,
        to_address: str,
        from_block: int,
        to_block: int,
        latest_offset: Optional[int],
        is_first_time: bool,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        f_addr = self._normalize_address(from_address)
        t_addr = self._normalize_address(to_address)
        if not f_addr or not t_addr:
            return

        now = self._now()
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        expires_at = (
            now + timedelta(seconds=ttl)
            if ttl is not None and ttl > 0
            else None
        )

        with Session(self._engine) as session:
            stmt = insert(FirstInteraction).values(
                from_address=f_addr,
                to_address=t_addr,
                from_block=from_block,
                to_block=to_block,
                latest_offset=latest_offset,
                is_first_time=is_first_time,
                checked_at=now,
                expires_at=expires_at,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    FirstInteraction.from_address,
                    FirstInteraction.to_address,
                    FirstInteraction.from_block,
                    FirstInteraction.to_block,
                    FirstInteraction.latest_offset,
                ],
                set_={
                    "is_first_time": is_first_time,
                    "checked_at": now,
                    "expires_at": expires_at,
                },
            )
            session.execute(stmt)
            session.commit()


__all__ = ["FirstInteractionCache"]
