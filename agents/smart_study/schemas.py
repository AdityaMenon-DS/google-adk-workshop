"""The coordinator, writer and reviewer exchange these structured records."""

from typing import Literal
from pydantic import BaseModel


class Requirements(BaseModel):
    subject: str
    days: int
    level: str
    topics: list[str]
    hours_per_day: float
    missing_fields: list[str]


class StudyBlock(BaseModel):
    kind: Literal["concept", "practice", "revision", "mock", "break"]
    topics: list[str]
    minutes: int
    activity: str
    problems: int


class StudyDay(BaseModel):
    day: int
    blocks: list[StudyBlock]


class StudyPlan(BaseModel):
    title: str
    days: list[StudyDay]
    notes: list[str]


class Review(BaseModel):
    approved: bool
    feedback: list[str]
