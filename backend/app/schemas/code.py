import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

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
    fetch_enabled: bool = False
    fetch_interval_seconds: int = Field(default=300, ge=30)
    index_on_commit_enabled: bool = False
    commit_poll_seconds: int = Field(default=60, ge=15)
    index_uncommitted: bool = False

    @field_validator("url")
    @classmethod
    def _check_url(cls, v: str | None) -> str | None:
        return validate_repo_url(v) if v else v

    @field_validator("default_branch")
    @classmethod
    def _check_branch(cls, v: str) -> str:
        return validate_git_ref(v)


# Each is backed by a NOT NULL column, so an explicit JSON `null` is a bad
# request rather than a clear. `RepoManager.update` dumps with
# `exclude_unset=True`, which counts an explicit null as set, so without this
# the null reaches the column and surfaces as a 500.
REPO_UPDATE_NON_NULLABLE = (
    "name",
    "default_branch",
    "fetch_enabled",
    "fetch_interval_seconds",
    "index_on_commit_enabled",
    "commit_poll_seconds",
    "index_uncommitted",
)


class RepoUpdate(BaseModel):
    name: str | None = None
    fetch_enabled: bool | None = None
    fetch_interval_seconds: int | None = Field(default=None, ge=30)
    index_on_commit_enabled: bool | None = None
    commit_poll_seconds: int | None = Field(default=None, ge=15)
    index_uncommitted: bool | None = None
    auth_token: str | None = None
    git_account_id: uuid.UUID | None = None
    default_branch: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _reject_explicit_nulls(cls, data):
        if isinstance(data, dict):
            nulled = sorted(
                f for f in REPO_UPDATE_NON_NULLABLE if f in data and data[f] is None
            )
            if nulled:
                raise ValueError(
                    f"{', '.join(nulled)} cannot be null; omit the field to leave it unchanged"
                )
        return data

    @field_validator("default_branch")
    @classmethod
    def _check_branch(cls, v: str | None) -> str | None:
        return validate_git_ref(v) if v else v


class ReindexRequest(BaseModel):
    full: bool = False
    enrich_symbols: bool = False
    generate_wiki: bool = False


class ReindexFilesRequest(BaseModel):
    files: list[str] = []
    commit: str | None = None
    enrich_symbols: bool = False


class ReindexFilesResponse(BaseModel):
    status: str
    repo_id: str
    commit: str | None = None
    accepted: int


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
    fetch_enabled: bool
    fetch_interval_seconds: int
    index_on_commit_enabled: bool
    commit_poll_seconds: int
    index_uncommitted: bool
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
    repo_id: uuid.UUID
    max_depth: int = Field(default=10, ge=1, le=25)
