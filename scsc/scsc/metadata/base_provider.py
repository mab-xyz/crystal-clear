from abc import ABC, abstractmethod
from typing import Dict, Optional


class BaseProvider(ABC):
    """Abstract base class for collecting labels from various sources."""

    @abstractmethod
    def get_label(self, address: str) -> Optional[str]:
        """
        Get a label for a given address.

        Args:
            address: The address to get the label for

        Returns:
            Optional[str]: The label if found, None otherwise
        """
        pass

    @abstractmethod
    def get_labels(self, addresses: list[str]) -> Dict[str, str]:
        """
        Get labels for multiple addresses.

        Args:
            addresses: List of addresses to get labels for

        Returns:
            Dict[str, str]: Dictionary mapping addresses to their labels
        """
        pass
