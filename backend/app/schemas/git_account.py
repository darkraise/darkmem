import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.services.git_forges import FORGES, get_forge


def _validate_provider(v: str) -> str:
    get_forge(v)
    return v


# A host lands inside an f-string that builds the verification URL, so anything
# that can end the authority component or start a new one has to be refused
# here: `@` would redirect the request (and the token with it) to a host after
# the userinfo, and `/ ? #` would let a crafted value reach a path or query of
# the caller's choosing on a host of their choosing.
_HOST_FORBIDDEN = frozenset("@/?#\\")


def _validate_host(v: str) -> str:
    # The trailing dot of a fully-qualified name resolves to the same host but
    # compares unequal, which would let `github.com.` sidestep any check keyed
    # on the string.
    host = v.strip().rstrip(".").lower()
    if not host or any(c in _HOST_FORBIDDEN or c.isspace() for c in host):
        raise ValueError("host must be a bare hostname, e.g. github.com")
    return host


class GitAccountCreate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    token: str = Field(min_length=1, max_length=1024)
    provider: str = "github"
    host: str | None = None
    is_default: bool = False

    _check_provider = field_validator("provider")(_validate_provider)

    @field_validator("host")
    @classmethod
    def _check_host(cls, v: str | None) -> str | None:
        return _validate_host(v) if v else v

    @field_validator("label")
    @classmethod
    def _strip_label(cls, v: str) -> str:
        label = v.strip()
        if not label:
            raise ValueError("label must not be blank")
        return label


class GitAccountUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=100)
    token: str | None = Field(default=None, min_length=1, max_length=1024)
    is_default: bool | None = None


class GitAccountOut(BaseModel):
    """The wire shape. ``token`` is deliberately absent — only the hint ships."""

    id: uuid.UUID
    label: str
    provider: str
    host: str
    username: str
    token_hint: str
    scopes: str | None = None
    is_default: bool = False
    last_verified_at: datetime | None = None
    repo_count: int = 0
    created_at: datetime
    updated_at: datetime


class GitAccountListResponse(BaseModel):
    accounts: list[GitAccountOut] = Field(default_factory=list)
    providers: list[dict[str, str]] = Field(
        default_factory=lambda: [
            {"provider": f.provider, "label": f.label, "default_host": f.default_host}
            for f in FORGES.values()
        ]
    )


class GitAccountVerifyRequest(BaseModel):
    token: str = Field(min_length=1, max_length=1024)
    provider: str = "github"
    host: str | None = None

    _check_provider = field_validator("provider")(_validate_provider)

    @field_validator("host")
    @classmethod
    def _check_host(cls, v: str | None) -> str | None:
        return _validate_host(v) if v else v


class GitAccountVerifyResponse(BaseModel):
    username: str
    scopes: str | None = None
    host: str
    provider: str
