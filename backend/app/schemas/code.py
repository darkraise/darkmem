import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

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
    # Omitted entirely, the forge's default account is stamped at create time.
    # Sent explicitly — including as null — the caller's choice wins.
    git_account_id: uuid.UUID | None = None
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
    git_account_id: uuid.UUID | None = None
    default_branch: str | None = None

    @field_validator("default_branch")
    @classmethod
    def _check_branch(cls, v: str | None) -> str | None:
        return validate_git_ref(v) if v else v


class ReindexRequest(BaseModel):
    full: bool = False
    enrich_symbols: bool = False
    generate_wiki: bool = False


class IndexDebtDrain(BaseModel):
    at: str = ""
    count: int = 0
    commit: str = ""
    vanished: int = 0


class IndexDebtStatus(BaseModel):
    """The re-trace debt signal (doc 10 §3 T2).

    ``queued`` on its own reads the same whether the queue is draining or
    wedged, so the lifetime totals and the two timestamped records ship with it:
    a consumer showing "queued, draining" rather than "queued" needs the
    difference to be readable from one response.
    """

    queued: int = 0
    deferred_total: int = 0
    drained_total: int = 0
    last_defer: IndexDebtDrain | None = None
    last_drain: IndexDebtDrain | None = None


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
    git_account_id: uuid.UUID | None = None
    # Denormalised for display: the picker has to render a repo's current
    # account without a second round-trip per row.
    git_account_label: str | None = None
    has_custom_token: bool = False
    index_debt: IndexDebtStatus = IndexDebtStatus()
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
    limit: int = Field(default=20, ge=1, le=200)


class CodeSearchResult(BaseModel):
    chunk_content: str
    file_path: str
    repo_id: uuid.UUID | None
    language: str | None
    symbol_name: str | None
    line_start: int
    line_end: int
    score: float


class BlastRadiusRequest(BaseModel):
    symbol_id: str
    max_depth: int = Field(default=10, ge=1, le=25)
