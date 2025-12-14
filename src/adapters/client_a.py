from typing import Dict, Any
from .base import ScheduleAdapter
from ..models.cdm import ScheduleRequest


class ClientAAdapter(ScheduleAdapter):
    """
    Adapter for Client A (original format).

    Client A already sends data in a format very close to our CDM,
    so this adapter mostly just validates and passes through.
    """

    @property
    def client_id(self) -> str:
        return "client_a"

    def to_cdm(self, raw_input: Dict[str, Any]) -> ScheduleRequest:
        """
        Client A format is already compatible with CDM.
        Just validate and construct the model.
        """
        return ScheduleRequest(**raw_input)
