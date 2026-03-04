from sqlmodel import Session

from src.api.crud.audit import (
    create_audit,
    delete_audit,
    get_audit,
    get_audits,
    update_audit,
)
from src.api.models.audit import AuditCreate, AuditUpdate


def test_create_and_get_audit(session: Session):
    audit_data = AuditCreate(
        protocol="uniswap-v4",
        company="trail-of-bits",
        url="http://example.com",
    )

    # Create audit
    created = create_audit(session, audit_data)
    assert created.id is not None
    assert created.protocol == "uniswap-v4"

    # Get audit
    fetched = get_audit(session, "uniswap-v4", "trail-of-bits")
    assert fetched is not None
    assert fetched.url == "http://example.com"


def test_update_audit(session: Session):
    audit_data = AuditCreate(
        protocol="uniswap-v4",
        company="trail-of-bits",
        url="http://example.com",
    )
    create_audit(session, audit_data)

    update_data = AuditUpdate(url="http://new-url.com")
    updated = update_audit(session, update_data, "uniswap-v4", "trail-of-bits")

    assert updated.url == "http://new-url.com"


def test_delete_audit(session: Session):
    audit_data = AuditCreate(
        protocol="uniswap-v4",
        company="trail-of-bits",
        url="http://example.com",
    )
    create_audit(session, audit_data)

    deleted = delete_audit(session, "uniswap-v4", "trail-of-bits")
    assert deleted is True

    # Ensure it's gone
    assert get_audit(session, "uniswap-v4", "trail-of-bits") is None


def test_get_audits(session):
    # Create multiple audit entries
    audits_data = [
        AuditCreate(
            protocol="uniswap",
            company="trail-of-bits",
            url="http://example1.com",
            version="4.0",
        ),
        AuditCreate(
            protocol="lido",
            company="trail-of-bits",
            url="http://example2.com",
            version="3.0",
        ),
        AuditCreate(
            protocol="sushiswap",
            company="chain-security",
            url="http://example3.com",
            version=None,
        ),
    ]

    for audit_data in audits_data:
        create_audit(session, audit_data)

    # 1. Get all audits (no filter)
    all_audits = get_audits(session)
    assert len(all_audits) == 3

    # 2. Filter by protocol
    uniswap_audits = get_audits(session, protocol="uniswap")
    assert len(uniswap_audits) == 1
    assert uniswap_audits[0].protocol == "uniswap"
    assert uniswap_audits[0].company == "trail-of-bits"
    assert uniswap_audits[0].version == "4.0"
    assert uniswap_audits[0].url == "http://example1.com"

    # 3. Filter by company
    trail_of_bits = get_audits(session, company="trail-of-bits")
    assert len(trail_of_bits) == 2
    assert all(a.company == "trail-of-bits" for a in trail_of_bits)

    # 4. Filter by version
    version_4_audits = get_audits(session, version="4.0")
    assert len(version_4_audits) == 1
    assert version_4_audits[0].version == "4.0"

    # 5. Filter by multiple fields
    filtered = get_audits(
        session, protocol="uniswap", company="trail-of-bits", version="4.0"
    )
    assert len(filtered) == 1
    assert filtered[0].url == "http://example1.com"

    # 6. Filter that returns nothing
    no_match = get_audits(session, protocol="NONEXISTENT")
    assert len(no_match) == 0
