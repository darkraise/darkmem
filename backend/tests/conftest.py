import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.auth import create_access_token, hash_password
from app.config import settings
from app.database import get_session
from app.main import app
from app.models import Base
from app.models.config import Config

test_engine = create_async_engine(settings.test_database_url)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session(setup_database):
    connection = await test_engine.connect()
    transaction = await connection.begin()
    async_session = AsyncSession(bind=connection, expire_on_commit=False)

    await connection.begin_nested()

    @event.listens_for(async_session.sync_session, "after_transaction_end")
    def restart_savepoint(session, trans):
        if trans.nested and not trans._parent.nested:
            session.begin_nested()

    yield async_session

    await async_session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client(session):
    async def override():
        yield session

    app.dependency_overrides[get_session] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_headers(session):
    hashed = hash_password("test-admin-password")
    session.add(Config(key="admin_password_hash", value={"hash": hashed}))
    await session.flush()

    token = create_access_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}
