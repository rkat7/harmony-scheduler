from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel, Field, field_validator


class Horizon(BaseModel):
    start: datetime
    end: datetime

    @field_validator('end')
    @classmethod
    def end_after_start(cls, v, info):
        if 'start' in info.data and v <= info.data['start']:
            raise ValueError('end must be after start')
        return v


class Resource(BaseModel):
    id: str
    capabilities: List[str]
    calendar: List[Tuple[datetime, datetime]]

    @field_validator('calendar')
    @classmethod
    def validate_calendar(cls, v):
        for start, end in v:
            if end <= start:
                raise ValueError(f'Calendar window end must be after start: {start} -> {end}')
        return v


class Operation(BaseModel):
    capability: str
    duration_minutes: int = Field(gt=0)


class Product(BaseModel):
    id: str
    family: str
    due: datetime
    route: List[Operation]

    @field_validator('route')
    @classmethod
    def route_not_empty(cls, v):
        if not v:
            raise ValueError('Product route cannot be empty')
        return v


class ChangeoverMatrix(BaseModel):
    values: Dict[str, int] = Field(default_factory=dict)

    def get_changeover_time(self, from_family: str, to_family: str) -> int:
        key = f"{from_family}->{to_family}"
        return self.values.get(key, 0)


class Settings(BaseModel):
    time_limit_seconds: int = Field(default=30, gt=0)


class ScheduleRequest(BaseModel):
    horizon: Horizon
    resources: List[Resource]
    products: List[Product]
    changeover_matrix_minutes: ChangeoverMatrix
    settings: Settings = Field(default_factory=Settings)


class Assignment(BaseModel):
    product: str
    op: str
    resource: str
    start: datetime
    end: datetime


class KPIs(BaseModel):
    tardiness_minutes: int
    changeovers: int
    makespan_minutes: int
    utilization: Dict[str, int]


class ScheduleResponse(BaseModel):
    assignments: List[Assignment]
    kpis: KPIs


class ScheduleError(BaseModel):
    error: str
    why: List[str]
