from fastapi import HTTPException, status


class InternalServerError(HTTPException):
    """Exception raised when contract analysis fails."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
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

class NotFoundError(HTTPException):
    """Exception raised when a resource is not found."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND, detail=detail
        )

