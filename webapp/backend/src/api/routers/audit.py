from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

import src.api.crud.audit as crud
from src.api.core.database import get_session
from src.api.core.security import require_admin_if_enabled
from src.api.models.audit import (
    AuditCreate,
    AuditListResponse,
    AuditResponse,
    AuditUpdate,
)
from src.api.schemas.response import ErrorResponse

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
)


@router.post(
    "/",
    response_model=AuditResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid input or duplicate audit",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Create a new audit entry",
    dependencies=[Depends(require_admin_if_enabled)],
)
async def create_audit(
    audit_data: AuditCreate,
    session: Session = Depends(get_session),
) -> AuditResponse:
    """Create new audit entry"""
    try:
        return crud.create_audit(session, audit_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create audit: {str(e)}"
        ) from e


@router.get(
    "/{protocol}/{company}",
    response_model=AuditResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Audit not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get audit by protocol and company",
)
async def get_audit(
    protocol: str,
    company: str,
    version: str | None = Query(
        default=None, description="Optional version filter"
    ),
    session: Session = Depends(get_session),
) -> AuditResponse:
    """Get specific audit entry"""
    audit = crud.get_audit(session, protocol, company, version)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return audit


@router.get(
    "/",
    response_model=AuditListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="List audit entries",
    dependencies=[Depends(require_admin_if_enabled)],
)
async def list_audits(
    protocol: str | None = None,
    company: str | None = None,
    version: str | None = Query(
        default=None, description="Optional version filter"
    ),
    session: Session = Depends(get_session),
) -> AuditListResponse:
    """List audit entries with optional filters"""
    audits = crud.get_audits(
        session, protocol=protocol, version=version, company=company
    )
    return AuditListResponse(total=len(audits), items=audits)


@router.put(
    "/{protocol}/{company}",
    response_model=AuditResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Audit not found"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Update audit url",
    dependencies=[Depends(require_admin_if_enabled)],
)
async def update_audit(
    protocol: str,
    company: str,
    audit_data: AuditUpdate,
    version: str | None = Query(
        default=None, description="Optional version filter"
    ),
    session: Session = Depends(get_session),
) -> AuditResponse:
    """Update audit URL"""
    try:
        audit = crud.update_audit(
            session, audit_data, protocol, company, version
        )
        if not audit:
            raise HTTPException(
                status_code=404, detail="Audit not found"
            ) from None
        return audit
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete(
    "/{protocol}/{company}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Audit not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Delete audit entry",
    dependencies=[Depends(require_admin_if_enabled)],
)
async def delete_audit(
    protocol: str,
    company: str,
    version: str | None = Query(
        default=None, description="Optional version filter"
    ),
    session: Session = Depends(get_session),
) -> None:
    """Delete audit entry"""
    if not crud.delete_audit(session, protocol, company, version):
        raise HTTPException(status_code=404, detail="Audit not found")
