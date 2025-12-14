from abc import ABC, abstractmethod
from typing import Dict, Any
from ..models.cdm import ScheduleRequest


class ScheduleAdapter(ABC):
    """
    Base adapter for transforming client-specific input formats
    into the canonical data model (CDM).

    Each client's data format is handled by a concrete adapter that
    implements the to_cdm() method. This keeps client-specific logic
    isolated from the core solver.
    """

    @abstractmethod
    def to_cdm(self, raw_input: Dict[str, Any]) -> ScheduleRequest:
        """
        Transform client-specific input into canonical format.

        Args:
            raw_input: Client-specific JSON structure

        Returns:
            ScheduleRequest in canonical format

        Raises:
            ValueError: If input is malformed or missing required fields
        """
        pass

    @property
    @abstractmethod
    def client_id(self) -> str:
        """Unique identifier for this client/adapter."""
        pass
