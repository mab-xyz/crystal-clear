from fastapi import HTTPException, status


class ContractAnalysisError(HTTPException):
    """Exception raised when contract analysis fails."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST, detail=detail
        )


class ExternalServiceError(HTTPException):
    """Exception raised when an external service is unavailable."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail
        )


class InputValidationError(HTTPException):
    """Exception raised when input validation fails."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )
