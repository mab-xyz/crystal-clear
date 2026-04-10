from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping, Optional

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, select

from src.api.core.config import settings
from src.api.core.contract_verification_allowlist import (
    get_contract_verification_allowlist,
)
from src.api.core.database import engine
from src.api.models.contract_verification import ContractVerification


class ContractVerificationCache:
    """Simple database-backed cache for contract verification metadata."""

    def __init__(self, ttl_seconds: Optional[int] = None) -> None:
        self._engine = engine
        self._ttl_seconds = (
            ttl_seconds
            if ttl_seconds is not None
            else int(settings.verification_cache_ttl_seconds)
        )

    @staticmethod
    def _normalize_address(address: str | None) -> Optional[str]:
        if not address:
            return None
        addr = address.strip().lower()
        if not addr.startswith("0x"):
            return None
        return addr

    @staticmethod
    def _now() -> datetime:
        return datetime.utcnow()

    def get_many(self, addresses: Iterable[str]) -> dict[str, dict]:
        """Fetch cached verifications for multiple addresses in a single query."""

        normalized: set[str] = set()
        for addr in addresses:
            key = self._normalize_address(addr)
            if key:
                normalized.add(key)
        if not normalized:
            return {}

        now = self._now()
        with Session(self._engine) as session:
            stmt = select(ContractVerification).where(
                ContractVerification.contract_address.in_(list(normalized))
            )
            rows = session.exec(stmt).all()

        cached: dict[str, dict] = {}
        for record in rows:
            if record.expires_at and record.expires_at <= now:
                continue
            payload = record.details or {
                "address": record.contract_address,
                "verification": record.verification_status,
                "source": record.source,
            }
            cached[record.contract_address] = dict(payload)
        return cached

    def get(self, address: str) -> Optional[dict]:
        key = self._normalize_address(address)
        if not key:
            return None
        return self.get_many([key]).get(key)

    def set(
        self,
        address: str,
        payload: Mapping[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Persist payload for address, refreshing expiry where applicable."""

        key = self._normalize_address(address)
        if not key or not payload:
            return

        now = self._now()
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl_seconds
        expires_at = (
            now + timedelta(seconds=ttl)
            if ttl is not None and ttl > 0
            else None
        )

        source = str(payload.get("source", "unknown"))
        verification_status = str(payload.get("verification", "not-verified"))
        details = dict(payload)

        with Session(self._engine) as session:
            stmt = insert(ContractVerification).values(
                contract_address=key,
                source=source,
                verification_status=verification_status,
                details=details,
                checked_at=now,
                expires_at=expires_at,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    ContractVerification.contract_address,
                    ContractVerification.source,
                ],
                set_={
                    "verification_status": verification_status,
                    "details": details,
                    "checked_at": now,
                    "expires_at": expires_at,
                },
            )
            session.execute(stmt)
            session.commit()


class AllowlistedContractVerificationCache:
    """Overlay hard-coded allowlist entries on top of verification cache."""

    def __init__(
        self,
        cache: ContractVerificationCache,
        allowlist: Iterable[str] | None = None,
    ) -> None:
        self._cache = cache
        self._allowlist = {
            key
            for address in (
                allowlist
                if allowlist is not None
                else get_contract_verification_allowlist()
            )
            if (key := ContractVerificationCache._normalize_address(address))
        }

    @staticmethod
    def _allowlisted_payload(address: str) -> dict:
        return {
            "address": address,
            "verification": "allowlisted",
            "verifiedAt": "N/A",
            "source": "allowlist",
        }

    def get_many(self, addresses: Iterable[str]) -> dict[str, dict]:
        normalized: set[str] = set()
        for addr in addresses:
            key = ContractVerificationCache._normalize_address(addr)
            if key:
                normalized.add(key)

        allowlisted = {
            key: self._allowlisted_payload(key)
            for key in normalized
            if key in self._allowlist
        }
        remaining = [key for key in normalized if key not in allowlisted]
        return {**self._cache.get_many(remaining), **allowlisted}

    def get(self, address: str) -> Optional[dict]:
        key = ContractVerificationCache._normalize_address(address)
        if not key:
            return None
        if key in self._allowlist:
            return self._allowlisted_payload(key)
        return self._cache.get(key)

    def set(
        self,
        address: str,
        payload: Mapping[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> None:
        key = ContractVerificationCache._normalize_address(address)
        if key and key in self._allowlist:
            return
        self._cache.set(address, payload, ttl_seconds=ttl_seconds)


__all__ = ["AllowlistedContractVerificationCache", "ContractVerificationCache"]
