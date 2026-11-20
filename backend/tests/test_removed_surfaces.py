"""Surfaces taken out of the app stay out."""
from __future__ import annotations

import importlib

from app.main import app


def _defines_pca_2d() -> bool:
    try:
        module = importlib.import_module("app.utils.math")
    except ModuleNotFoundError:
        return False
    return hasattr(module, "pca_2d")


def test_vector_projection_route_is_gone():
    paths = {getattr(route, "path", None) for route in app.routes}

    assert "/api/v1/vectors/projection" not in paths
    assert not _defines_pca_2d()
