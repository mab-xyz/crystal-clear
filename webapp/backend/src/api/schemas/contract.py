from typing import List

from pydantic import BaseModel

from api.models.audit import AuditResponse
from api.models.contract import ContractResponse
from api.models.repository import RepositoryResponse


class ContractAuditCheckResponse(BaseModel):
    """Response model for contract audit check endpoint"""

    contract: ContractResponse
    audits: List[AuditResponse]


class ContractRepositoryResponse(BaseModel):
    """Response model for contract repository endpoint"""

    contract: ContractResponse
    repository: RepositoryResponse


class ContractAuditCreate(BaseModel):
    """Request model for adding audit to contract"""

    company: str
    url: str


class ContractRepositoryCreate(BaseModel):
    """Request model for adding repository to contract"""

    url: str
