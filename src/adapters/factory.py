from typing import Dict, Any
from .base import ScheduleAdapter
from .client_a import ClientAAdapter
from .client_b import ClientBAdapter


class AdapterFactory:
    """
    Factory for selecting the appropriate adapter based on input format.

    Supports two strategies:
    1. Explicit client_id field in the payload
    2. Schema fingerprinting (detect format automatically)
    """

    def __init__(self):
        self._adapters = {
            "client_a": ClientAAdapter(),
            "client_b": ClientBAdapter(),
        }

    def get_adapter(self, raw_input: Dict[str, Any]) -> ScheduleAdapter:
        """
        Select adapter based on input structure.

        Args:
            raw_input: Raw JSON payload from client

        Returns:
            Appropriate adapter instance

        Raises:
            ValueError: If client format cannot be determined
        """
        # Strategy 1: Explicit client_id
        if "client_id" in raw_input:
            client_id = raw_input["client_id"]
            if client_id not in self._adapters:
                raise ValueError(f"Unknown client_id: {client_id}")
            return self._adapters[client_id]

        # Strategy 2: Schema fingerprinting
        return self._detect_adapter(raw_input)

    def _detect_adapter(self, raw_input: Dict[str, Any]) -> ScheduleAdapter:
        """
        Auto-detect client format based on schema characteristics.

        Client A indicators:
        - Has "horizon" field with "start"/"end"
        - Has "products" field
        - Has "resources" field

        Client B indicators:
        - Has "shift_window" field
        - Has "orders" field
        - Has "machines" field
        """
        # Check for Client B indicators
        if "shift_window" in raw_input and "orders" in raw_input:
            return self._adapters["client_b"]

        # Check for Client A indicators
        if "horizon" in raw_input and "products" in raw_input:
            return self._adapters["client_a"]

        # Cannot determine
        raise ValueError(
            "Unable to detect client format. "
            "Ensure input has either (horizon + products) or (shift_window + orders)"
        )

    def register_adapter(self, adapter: ScheduleAdapter):
        """
        Register a new client adapter.

        Useful for adding Client C, D, etc. without modifying this class.
        """
        self._adapters[adapter.client_id] = adapter
