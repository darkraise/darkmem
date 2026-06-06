import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator

# git accepts transport helpers (`ext::sh -c ...` = arbitrary command execution)
# and `file://` / bare local paths (local-file read / SSRF). Only allow real
# network transports for a clone URL.
ALLOWED_REPO_URL_SCHEMES = {"https", "http", "ssh", "git"}


def validate_repo_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_REPO_URL_SCHEMES:
        raise ValueError(
            "repo url must use one of "
            f"{sorted(ALLOWED_REPO_URL_SCHEMES)} (e.g. https://… or ssh://git@host/repo); "
            "scp-style and ext::/file:// targets are rejected"
        )
    if not parsed.netloc:
        raise ValueError("repo url must include a host")
    return url


def validate_git_ref(ref: str) -> str:
    # A branch starting with '-' is an argument-injection vector into the git
    # clone/fetch/reset argv; whitespace/control chars are never valid refs.
    if ref.startswith("-") or any(c.isspace() for c in ref):
        raise ValueError("invalid branch name")
    return ref


class RepoCreate(BaseModel):
    name: str
    url: str | None = None
    local_path: str | None = None
    provider: str = "local"
    default_branch: str = "main"
    auth_token: str | None = None
    auto_sync: bool = True

    @field_validator("url")
    @classmethod
    def _check_url(cls, v: str | None) -> str | None:
        return validate_repo_url(v) if v else v

    @field_validator("default_branch")
    @classmethod
    def _check_branch(cls, v: str) -> str:
        return validate_git_ref(v)


class RepoUpdate(BaseModel):
    name: str | None = None
    auto_sync: bool | None = None
    auth_token: str | None = None
    default_branch: str | None = None

    @field_validator("default_branch")
    @classmethod
    def _check_branch(cls, v: str | None) -> str | None:
        return validate_git_ref(v) if v else v


class ReindexRequest(BaseModel):
    full: bool = False
    enrich_symbols: bool = False
    generate_wiki: bool = False


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
