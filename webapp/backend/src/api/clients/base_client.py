import requests
from typing import Dict, Any, Optional
from src.api.core.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

class BaseClient:
    """Base client for handling HTTP requests."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make an HTTP request with error handling."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"X-API-Key": self.api_key}

        try:
            logger.debug(f"Making {method} request to {url} with {kwargs}")
            response = requests.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed: {e}")
            return None

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Make a GET request."""
        return self._make_request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a POST request."""
        return self._make_request("POST", endpoint, json=data)
