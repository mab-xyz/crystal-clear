from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error envelope returned for 4xx/5xx responses."""

    detail: str = Field(
        ..., description="Human-readable explanation of what went wrong"
    )
