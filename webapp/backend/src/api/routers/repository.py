from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

import api.crud.repository as crud
from api.core.database import get_session
from api.core.security import require_admin_if_enabled
from api.models.repository import (
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryResponse,
    RepositoryUpdate,
)
from api.schemas.response import ErrorResponse

router = APIRouter(prefix="/repository", tags=["repository"])


@router.post(
    "/",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Invalid input or duplicate repository",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Create a new repository entry",
    dependencies=[Depends(require_admin_if_enabled)],
)
async def create_repository(
    repository_in: RepositoryCreate,
    session: Session = Depends(get_session),
) -> Any:
    """Create new repository entry"""
    try:
        return crud.create_repository(session, repository_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create repository: {str(e)}"
        ) from e


@router.get(
    "/{protocol}",
    response_model=RepositoryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Repository not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Get repository by protocol",
)
async def get_repository(
    protocol: str,
    version: str | None = Query(default=None, description="Optional version filter"),
    session: Session = Depends(get_session),
) -> Any:
    """Get repository entry"""
    repository = crud.get_repository(session, protocol, version)
    if not repository:
        raise HTTPException(status_code=404, detail="Repository not found") from None
    return repository


@router.get(
    "/",
    response_model=RepositoryListResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="List repository entries",
    dependencies=[Depends(require_admin_if_enabled)],
)
async def list_repositories(
    protocol: str | None = None,
    version: str | None = Query(default=None, description="Optional version filter"),
    skip: int = 0,
    limit: int = Query(default=100, lte=100),
    session: Session = Depends(get_session),
) -> Any:
    """List repository entries with optional filters"""
    repositories = crud.get_repositories(
        session=session, skip=skip, limit=limit, protocol=protocol, version=version
    )
    return RepositoryListResponse(total=len(repositories), items=repositories)


@router.put(
    "/{protocol}",
    response_model=RepositoryResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Repository not found"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Update repository URL",
    dependencies=[Depends(require_admin_if_enabled)],
)
async def update_repository(
    protocol: str,
    repository_in: RepositoryUpdate,
    version: str | None = Query(default=None, description="Optional version filter"),
    session: Session = Depends(get_session),
) -> Any:
    """Update repository URL"""
    try:
        repository = crud.update_repository(session, repository_in, protocol, version)
        if not repository:
            raise HTTPException(
                status_code=404, detail="Repository not found"
            ) from None
        return repository
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete(
    "/{protocol}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Repository not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Delete repository entry",
    dependencies=[Depends(require_admin_if_enabled)],
)
async def delete_repository(
    protocol: str,
    version: str | None = Query(default=None, description="Optional version filter"),
    session: Session = Depends(get_session),
) -> None:
    """Delete repository entry"""
    if not crud.delete_repository(session, protocol, version):
        raise HTTPException(status_code=404, detail="Repository not found") from None
