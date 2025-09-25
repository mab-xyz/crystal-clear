from typing import Literal
from pydantic import BaseModel, Field

class VerificationDetails(BaseModel):
    address: str = Field(..., description="Contract address")
    verification: Literal["verified", "fully-verified", "not-verified"] = Field(
        ..., description="Verification status: verified, fully-verified, or not-verified"
    )
    verifiedAt: str = Field(..., description="Verification timestamp")

