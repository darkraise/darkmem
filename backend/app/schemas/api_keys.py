"""Wire shapes for the key management surface (doc 18 §5).

``ApiKeyResponse`` carries no ``key_hash`` and no plaintext. The plaintext
appears on exactly one shape, ``ApiKeyCreated``, returned by exactly one call —
which is what "shown once at issue and never again" means on the wire.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    # Untyped members on purpose: `parse_scopes` owns the rejection, and it
    # rejects with a message naming the offending value and the closed set. A
    # pydantic `list[Literal[...]]` here would answer a bad scope with a schema
    # error that names neither, and would leave the service-layer guard
    # untested by the door that matters.
    scopes: list = Field(min_length=1)
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_id: str
    scopes: list[str]
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None


class ApiKeyCreated(ApiKeyResponse):
    """The issue response. ``token`` is the only copy that will ever exist."""

    token: str
