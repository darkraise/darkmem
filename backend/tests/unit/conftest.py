"""Isolated conftest for pure unit tests — no database, no async fixtures."""

import pytest_asyncio


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    """Override the parent conftest's database fixture with a no-op."""
    yield
