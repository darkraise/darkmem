"""Authenticated system utility endpoints.

Mirrors the wizard-only ``/api/v1/setup/fs/*`` shapes for use after the
install has been initialised — the wizard endpoints 403 once the password
is set, so the Settings page (and any future operator-tools UI) needs an
auth-gated mirror.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_auth
from app.api.routes.setup import (
    FsListResponse,
    FsRootsResponse,
    _enumerate_roots,
    _list_directory,
)
from app.services.repo_manager import validate_local_path

router = APIRouter(prefix="/api/v1/system", tags=["system"])


@router.get("/fs/roots", response_model=FsRootsResponse)
async def system_fs_roots(_user=Depends(require_auth)) -> FsRootsResponse:
    return FsRootsResponse(roots=_enumerate_roots())


@router.get("/fs/list", response_model=FsListResponse)
async def system_fs_list(
    path: str,
    detect_repos: bool = False,
    _user=Depends(require_auth),
) -> FsListResponse:
    try:
        resolved = validate_local_path(path, must_not_be_repo=detect_repos)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    parent = str(resolved.parent) if resolved.parent != resolved else None
    entries = _list_directory(resolved, detect_repos=detect_repos)
    is_git = (resolved / ".git").is_dir()
    return FsListResponse(
        path=str(resolved),
        parent=parent,
        entries=entries,
        is_git=is_git,
    )
