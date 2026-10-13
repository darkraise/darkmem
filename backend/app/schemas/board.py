"""Wire shapes of the progress board (spec 2026-10-13 §2.2)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlanProgress(BaseModel):
    done: int
    total: int
    # "no_workstream" or "no_properties" when the plan's tasks are untracked.
    untracked: str | None


class RegisterRow(BaseModel):
    number: int
    item: str
    assigned: str
    acceptance: str
    state: str
    raw_state: str
    note: str
    note_blank: bool
    line: int


class BoardRegisterRow(RegisterRow):
    plan_uri: str | None
    plan_progress: PlanProgress | None


class MalformedRow(BaseModel):
    line: int
    text: str
    reason: str


class BoardRegister(BaseModel):
    document_id: str
    uri: str
    title: str | None
    covers: str | None
    content_hash: str | None
    block_first: bool
    rows: list[BoardRegisterRow]
    malformed: list[MalformedRow]
    error: str | None


class TaskStep(BaseModel):
    checked: bool
    text: str


class PlanTask(BaseModel):
    number: int
    label: str
    title: str
    line: int
    state: str
    raw_state: str | None
    untracked: str | None
    shared_number: bool
    blocked_reason: str | None
    commit: str | None
    last_activity: datetime | None
    steps: list[TaskStep]


class PlanWorkstream(BaseModel):
    id: str
    key: str
    state: str


class BoardPlan(BaseModel):
    document_id: str
    uri: str
    title: str | None
    content_hash: str | None
    workstream: PlanWorkstream | None
    other_workstreams: int
    spec_uri: str | None
    untracked: str | None
    tasks: list[PlanTask]
    orphans: list[int]
    error: str | None


class BoardRecordsResponse(BaseModel):
    project: str
    registers: list[BoardRegister]
    plans: list[BoardPlan]


class RegisterRowEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_hash: str = Field(min_length=1)
    state: str | None = None
    note: str | None = None
    assigned: str | None = None


class RegisterRowEditResponse(BaseModel):
    document_id: str
    content_hash: str
    row: RegisterRow
