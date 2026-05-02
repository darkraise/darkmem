import uuid
from datetime import datetime

from pydantic import BaseModel


class RepoCreate(BaseModel):
    name: str
    url: str | None = None
    local_path: str | None = None
    provider: str = "local"
    default_branch: str = "main"
    auth_token: str | None = None
    auto_sync: bool = True


class RepoUpdate(BaseModel):
    name: str | None = None
    auto_sync: bool | None = None
    auth_token: str | None = None
    default_branch: str | None = None


class RepoResponse(BaseModel):
    id: uuid.UUID
    name: str
    url: str | None
    local_path: str | None
    provider: str
    default_branch: str
    last_indexed_commit: str | None
    last_indexed_at: datetime | None
    status: str = "pending"
    status_message: str | None = None
    auto_sync: bool
    file_count: int = 0
    symbol_count: int = 0
    created_at: datetime
    updated_at: datetime


class CodeFileResponse(BaseModel):
    id: uuid.UUID
    file_path: str
    language: str | None
    last_commit_sha: str | None
    indexed_at: datetime


class CodeSymbolResponse(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    file_path: str
    line_start: int
    line_end: int
    signature: str | None
    docstring: str | None
    visibility: str | None
    source_code: str
    summary: str | None
    enrichment_status: str


class CodeSearchRequest(BaseModel):
    query: str
    repo_id: uuid.UUID | None = None
    language: str | None = None
    limit: int = 20


class CodeSearchResult(BaseModel):
    chunk_content: str
    file_path: str
    repo_id: uuid.UUID
    language: str | None
    symbol_name: str | None
    line_start: int
    line_end: int
    score: float


class BlastRadiusRequest(BaseModel):
    symbol_id: str
    max_depth: int = 10
