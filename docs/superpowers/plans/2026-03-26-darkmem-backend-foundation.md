# darkmem Backend Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Working FastAPI server with PostgreSQL storage, memory CRUD, tag management, API key auth, and REST endpoints.

**Architecture:** Layered monolith — API routes → services → repositories → PostgreSQL via async SQLAlchemy 2.0. Pydantic schemas separate from SQLAlchemy models.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (async/asyncpg), Alembic, Pydantic v2, pydantic-settings, pytest, pytest-asyncio, httpx

---

## Plan Decomposition

This project is split into 4 plans, each producing working, testable software:

1. **Backend Foundation** (this plan) — Postgres models, repositories, memory service, REST API, auth
2. **Storage & Intelligence** — Qdrant + Neo4j repos, LLM orchestrator, extraction pipeline, hybrid search
3. **MCP + WebSocket + Prompts** — MCP server, WebSocket events, system prompt profiles, analytics
4. **Frontend + Deployment** — React dashboard, Docker production compose, build scripts

---

## File Structure

```
darkmem/
├── docker-compose.dev.yml
├── .env.example
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── memory.py          # Memory, Tag, memory_tags
│   │   │   ├── api_key.py         # ApiKey
│   │   │   ├── audit.py           # AuditLog
│   │   │   └── config.py          # Config, SystemPromptProfile
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── memory.py
│   │   │   ├── tag.py
│   │   │   └── api_key.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # Abstract interfaces
│   │   │   └── relational.py      # Postgres implementations
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── memory.py
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── deps.py
│   │       └── routes/
│   │           ├── __init__.py
│   │           ├── memories.py
│   │           ├── tags.py
│   │           └── keys.py
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_models.py
│       ├── test_repositories.py
│       ├── test_services.py
│       └── test_api/
│           ├── __init__.py
│           ├── test_memories.py
│           ├── test_tags.py
│           └── test_keys.py
```

---

### Task 1: Project Scaffolding + Docker Compose Dev

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/Dockerfile`
- Create: `docker-compose.dev.yml`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.env
*.egg-info/
dist/
.venv/
node_modules/
.superpowers/
```

- [ ] **Step 2: Create `.env.example`**

```env
# PostgreSQL
DB_PASSWORD=darkmem
DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5432/darkmem
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5432/darkmem_test

# Neo4j
NEO4J_PASSWORD=darkmem

# Qdrant (no auth by default)
QDRANT_URL=http://localhost:6333

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
```

- [ ] **Step 3: Create `backend/pyproject.toml`**

```toml
[project]
name = "darkmem"
version = "0.1.0"
description = "Centralized memory system for AI agents"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 4: Create `backend/app/__init__.py`**

```python
```

(Empty file — marks `app` as a package.)

- [ ] **Step 5: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5432/darkmem"
    test_database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5432/darkmem_test"
    qdrant_url: str = "http://localhost:6333"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "darkmem"
    api_key_prefix: str = "dm_"


settings = Settings()
```

- [ ] **Step 6: Create `backend/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="darkmem", version="0.1.0", description="Centralized memory system for AI agents", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 8: Create `docker-compose.dev.yml`**

```yaml
services:
  darkmem-api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://darkmem:${DB_PASSWORD:-darkmem}@postgres:5432/darkmem
      - TEST_DATABASE_URL=postgresql+asyncpg://darkmem:${DB_PASSWORD:-darkmem}@postgres:5432/darkmem_test
      - QDRANT_URL=http://qdrant:6333
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD:-darkmem}
    volumes:
      - ./backend/app:/app/app
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_started
      neo4j:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: postgres:17-alpine
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=darkmem
      - POSTGRES_USER=darkmem
      - POSTGRES_PASSWORD=${DB_PASSWORD:-darkmem}
    healthcheck:
      test: ["CMD-ONLY", "pg_isready", "-U", "darkmem"]
      interval: 5s
      timeout: 3s
      retries: 5

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-darkmem}
    healthcheck:
      test: ["CMD", "neo4j", "status"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  qdrant_data:
  neo4j_data:
```

- [ ] **Step 9: Verify compose starts**

Run: `cp .env.example .env && docker compose -f docker-compose.dev.yml up -d postgres`
Expected: Postgres container starts and is healthy.

- [ ] **Step 10: Commit**

```bash
git add .gitignore .env.example docker-compose.dev.yml backend/pyproject.toml backend/Dockerfile backend/app/__init__.py backend/app/config.py backend/app/main.py
git commit -m "chore: scaffold project structure and docker compose dev"
```

---

### Task 2: Database Setup + SQLAlchemy Models

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/memory.py`
- Create: `backend/app/models/api_key.py`
- Create: `backend/app/models/audit.py`
- Create: `backend/app/models/config.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_models.py`

- [ ] **Step 1: Create `backend/app/database.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

- [ ] **Step 2: Create `backend/app/models/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 3: Create `backend/app/models/memory.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

memory_tags = Table(
    "memory_tags",
    Base.metadata,
    Column("memory_id", UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="api")
    source_agent: Mapped[str | None] = mapped_column(String(255))
    memory_type: Mapped[str | None] = mapped_column(String(50))
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    tags: Mapped[list["Tag"]] = relationship(secondary=memory_tags, back_populates="memories", lazy="selectin")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))

    memories: Mapped[list["Memory"]] = relationship(secondary=memory_tags, back_populates="tags", lazy="selectin")
```

- [ ] **Step 4: Create `backend/app/models/api_key.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    scopes: Mapped[list] = mapped_column(JSONB, default=lambda: ["read", "write"])
    profile: Mapped[str | None] = mapped_column(String(100), default="default")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

- [ ] **Step 5: Create `backend/app/models/audit.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    memory_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 6: Create `backend/app/models/config.py`**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class Config(Base):
    __tablename__ = "config"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)


class SystemPromptProfile(Base):
    __tablename__ = "system_prompt_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    save_triggers: Mapped[dict] = mapped_column(JSONB, default=dict)
    search_behavior: Mapped[dict] = mapped_column(JSONB, default=dict)
    tagging_conventions: Mapped[dict] = mapped_column(JSONB, default=dict)
    extraction_depth: Mapped[str] = mapped_column(String(20), default="full")
    dedup_strategy: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 7: Create `backend/app/models/__init__.py`**

```python
from .api_key import ApiKey
from .audit import AuditLog
from .base import Base
from .config import Config, SystemPromptProfile
from .memory import Memory, Tag, memory_tags

__all__ = ["Base", "Memory", "Tag", "memory_tags", "ApiKey", "AuditLog", "Config", "SystemPromptProfile"]
```

- [ ] **Step 8: Create test fixtures — `backend/tests/__init__.py` and `backend/tests/conftest.py`**

`backend/tests/__init__.py` — empty file.

`backend/tests/conftest.py`:

```python
import hashlib
import secrets

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.database import get_session
from app.main import app
from app.models import Base
from app.models.api_key import ApiKey


def _generate_test_api_key() -> tuple[str, str]:
    raw = "dm_" + secrets.token_hex(24)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash

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
async def session():
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
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
async def api_key_raw(session):
    raw_key, key_hash = _generate_test_api_key()
    key = ApiKey(name="test-key", key_hash=key_hash, scopes=["read", "write", "admin"])
    session.add(key)
    await session.flush()
    return raw_key


@pytest_asyncio.fixture
async def auth_headers(api_key_raw):
    return {"Authorization": f"Bearer {api_key_raw}"}
```

- [ ] **Step 9: Write model tests — `backend/tests/test_models.py`**

```python
from app.models.api_key import ApiKey
from app.models.audit import AuditLog
from app.models.memory import Memory, Tag


async def test_create_memory(session):
    memory = Memory(content="Test memory", source="test")
    session.add(memory)
    await session.flush()

    assert memory.id is not None
    assert memory.content == "Test memory"
    assert memory.source == "test"
    assert memory.importance == 0.5
    assert memory.is_archived is False
    assert memory.metadata_ == {}


async def test_memory_with_tags(session):
    tag = Tag(name="project/test", category="project")
    session.add(tag)
    await session.flush()

    memory = Memory(content="Tagged memory", source="test", tags=[tag])
    session.add(memory)
    await session.flush()

    assert len(memory.tags) == 1
    assert memory.tags[0].name == "project/test"


async def test_create_api_key(session):
    key = ApiKey(name="my-key", key_hash="abc123", scopes=["read", "write"])
    session.add(key)
    await session.flush()

    assert key.id is not None
    assert key.scopes == ["read", "write"]


async def test_create_audit_log(session):
    entry = AuditLog(action="create", details={"test": True})
    session.add(entry)
    await session.flush()

    assert entry.id is not None
    assert entry.action == "create"
```

- [ ] **Step 10: Run model tests**

Run: `cd backend && pip install -e ".[dev]" && pytest tests/test_models.py -v`

Prerequisite: Postgres must be running with the test database created:
```bash
docker compose -f docker-compose.dev.yml up -d postgres
PGPASSWORD=darkmem psql -h localhost -U darkmem -c "CREATE DATABASE darkmem_test;" 2>/dev/null || true
```

Expected: All 4 tests PASS.

- [ ] **Step 11: Commit**

```bash
git add backend/app/database.py backend/app/models/ backend/tests/
git commit -m "feat: add database setup and SQLAlchemy models"
```

---

### Task 3: Alembic Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/` (auto-generated)

- [ ] **Step 1: Initialize Alembic**

Run: `cd backend && pip install alembic && alembic init migrations`
Expected: Creates `alembic.ini` and `migrations/` directory.

- [ ] **Step 2: Configure `backend/alembic.ini`**

Edit the `sqlalchemy.url` line:

```ini
sqlalchemy.url = postgresql+asyncpg://darkmem:darkmem@localhost:5432/darkmem
```

- [ ] **Step 3: Replace `backend/migrations/env.py`**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Generate initial migration**

Run: `cd backend && alembic revision --autogenerate -m "initial schema"`
Expected: Creates a migration file in `migrations/versions/`.

- [ ] **Step 5: Run migration**

Run: `cd backend && alembic upgrade head`
Expected: All tables created in the `darkmem` database.

- [ ] **Step 6: Commit**

```bash
git add backend/alembic.ini backend/migrations/
git commit -m "feat: add Alembic migrations with initial schema"
```

---

### Task 4: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/memory.py`
- Create: `backend/app/schemas/tag.py`
- Create: `backend/app/schemas/api_key.py`

- [ ] **Step 1: Create `backend/app/schemas/__init__.py`**

```python
```

- [ ] **Step 2: Create `backend/app/schemas/memory.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    content: str
    tags: list[str] = Field(default_factory=list)
    source: str = "api"
    source_agent: str | None = None
    memory_type: str | None = None
    importance: float = 0.5
    metadata: dict = Field(default_factory=dict)
    expires_at: datetime | None = None


class MemoryUpdate(BaseModel):
    content: str | None = None
    tags: list[str] | None = None
    memory_type: str | None = None
    importance: float | None = None
    metadata: dict | None = None
    expires_at: datetime | None = None
    is_archived: bool | None = None


class MemoryResponse(BaseModel):
    id: uuid.UUID
    content: str
    source: str
    source_agent: str | None
    memory_type: str | None
    importance: float
    metadata: dict
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    is_archived: bool


class MemorySearchRequest(BaseModel):
    query: str | None = None
    tags_any: list[str] | None = None
    tags_all: list[str] | None = None
    memory_type: str | None = None
    source: str | None = None
    limit: int = 20


class MemoryBatchCreate(BaseModel):
    entries: list[MemoryCreate]


class MemoryMergeRequest(BaseModel):
    target_id: uuid.UUID
```

- [ ] **Step 3: Create `backend/app/schemas/tag.py`**

```python
from pydantic import BaseModel


class TagResponse(BaseModel):
    id: int
    name: str
    category: str | None
    memory_count: int = 0
```

- [ ] **Step 4: Create `backend/app/schemas/api_key.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreate(BaseModel):
    name: str
    scopes: list[str] = Field(default_factory=lambda: ["read", "write"])
    profile: str = "default"
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    scopes: list[str]
    profile: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add Pydantic request/response schemas"
```

---

### Task 5: Repository Layer

**Files:**
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/repositories/base.py`
- Create: `backend/app/repositories/relational.py`
- Create: `backend/tests/test_repositories.py`

- [ ] **Step 1: Write repository tests — `backend/tests/test_repositories.py`**

```python
from app.models.memory import Memory, Tag
from app.repositories.relational import PostgresApiKeyRepository, PostgresMemoryRepository, PostgresTagRepository


async def test_create_and_get_memory(session):
    repo = PostgresMemoryRepository(session)
    memory = await repo.create(content="Test content", source="test", source_agent=None, memory_type="fact", importance=0.8, metadata={})

    assert memory.id is not None
    assert memory.content == "Test content"

    fetched = await repo.get(memory.id)
    assert fetched is not None
    assert fetched.content == "Test content"


async def test_update_memory(session):
    repo = PostgresMemoryRepository(session)
    memory = await repo.create(content="Original", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})

    updated = await repo.update(memory.id, content="Updated")
    assert updated.content == "Updated"


async def test_delete_memory(session):
    repo = PostgresMemoryRepository(session)
    memory = await repo.create(content="To delete", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})

    assert await repo.delete(memory.id) is True
    assert await repo.get(memory.id) is None
    assert await repo.delete(memory.id) is False


async def test_list_memories(session):
    repo = PostgresMemoryRepository(session)
    for i in range(3):
        await repo.create(content=f"Memory {i}", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})

    memories, total = await repo.list_memories(offset=0, limit=10)
    assert total == 3
    assert len(memories) == 3


async def test_set_and_search_tags(session):
    repo = PostgresMemoryRepository(session)
    memory = await repo.create(content="Tagged", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})
    await repo.set_tags(memory.id, ["project/test", "infra/services"])

    await session.refresh(memory, ["tags"])
    assert len(memory.tags) == 2

    results = await repo.search_by_tags(tags_any=["project/test"])
    assert len(results) == 1
    assert results[0].id == memory.id


async def test_search_by_tags_all(session):
    repo = PostgresMemoryRepository(session)
    m1 = await repo.create(content="Has both", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})
    await repo.set_tags(m1.id, ["tag-a", "tag-b"])

    m2 = await repo.create(content="Has one", source="test", source_agent=None, memory_type=None, importance=0.5, metadata={})
    await repo.set_tags(m2.id, ["tag-a"])

    results = await repo.search_by_tags(tags_all=["tag-a", "tag-b"])
    assert len(results) == 1
    assert results[0].id == m1.id


async def test_tag_get_or_create(session):
    repo = PostgresTagRepository(session)
    tag1 = await repo.get_or_create("project/test")
    tag2 = await repo.get_or_create("project/test")
    assert tag1.id == tag2.id
    assert tag1.category == "project"


async def test_api_key_crud(session):
    repo = PostgresApiKeyRepository(session)
    key = await repo.create(name="test", key_hash="hash123", scopes=["read"], profile="default")
    assert key.id is not None

    found = await repo.get_by_key_hash("hash123")
    assert found is not None
    assert found.name == "test"

    keys = await repo.list_all()
    assert len(keys) == 1

    assert await repo.delete(key.id) is True
    assert await repo.list_all() == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_repositories.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.repositories.relational'`

- [ ] **Step 3: Create `backend/app/repositories/__init__.py`**

```python
```

- [ ] **Step 4: Create `backend/app/repositories/base.py`**

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.models.api_key import ApiKey
    from app.models.memory import Memory, Tag


class MemoryRepositoryBase(ABC):
    @abstractmethod
    async def create(self, content: str, source: str, source_agent: str | None, memory_type: str | None, importance: float, metadata: dict, expires_at=None) -> Memory: ...

    @abstractmethod
    async def get(self, memory_id: UUID) -> Memory | None: ...

    @abstractmethod
    async def update(self, memory_id: UUID, **fields) -> Memory | None: ...

    @abstractmethod
    async def delete(self, memory_id: UUID) -> bool: ...

    @abstractmethod
    async def list_memories(self, offset: int = 0, limit: int = 50, is_archived: bool = False) -> tuple[list[Memory], int]: ...

    @abstractmethod
    async def search_by_tags(self, query: str | None = None, tags_any: list[str] | None = None, tags_all: list[str] | None = None, memory_type: str | None = None, source: str | None = None, limit: int = 20) -> list[Memory]: ...

    @abstractmethod
    async def set_tags(self, memory_id: UUID, tag_names: list[str]) -> None: ...


class TagRepositoryBase(ABC):
    @abstractmethod
    async def get_or_create(self, name: str, category: str | None = None) -> Tag: ...

    @abstractmethod
    async def list_all(self) -> list[Tag]: ...

    @abstractmethod
    async def get_with_counts(self) -> list[tuple[Tag, int]]: ...


class ApiKeyRepositoryBase(ABC):
    @abstractmethod
    async def create(self, name: str, key_hash: str, scopes: list[str], profile: str, expires_at=None) -> ApiKey: ...

    @abstractmethod
    async def get_by_key_hash(self, key_hash: str) -> ApiKey | None: ...

    @abstractmethod
    async def list_all(self) -> list[ApiKey]: ...

    @abstractmethod
    async def delete(self, key_id: UUID) -> bool: ...

    @abstractmethod
    async def update_last_used(self, key_id: UUID) -> None: ...


class AuditRepositoryBase(ABC):
    @abstractmethod
    async def log(self, action: str, memory_id: UUID | None = None, api_key_id: UUID | None = None, details: dict | None = None) -> None: ...
```

- [ ] **Step 5: Create `backend/app/repositories/relational.py`**

```python
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.api_key import ApiKey
from app.models.audit import AuditLog
from app.models.memory import Memory, Tag, memory_tags

from .base import ApiKeyRepositoryBase, AuditRepositoryBase, MemoryRepositoryBase, TagRepositoryBase


class PostgresMemoryRepository(MemoryRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, content, source, source_agent, memory_type, importance, metadata, expires_at=None):
        memory = Memory(
            content=content,
            source=source,
            source_agent=source_agent,
            memory_type=memory_type,
            importance=importance,
            metadata_=metadata,
            expires_at=expires_at,
        )
        self.session.add(memory)
        await self.session.flush()
        await self.session.refresh(memory, ["tags"])
        return memory

    async def get(self, memory_id):
        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.id == memory_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, memory_id, **fields):
        memory = await self.get(memory_id)
        if not memory:
            return None
        for key, value in fields.items():
            if key == "metadata":
                setattr(memory, "metadata_", value)
            elif hasattr(memory, key):
                setattr(memory, key, value)
        await self.session.flush()
        await self.session.refresh(memory, ["tags"])
        return memory

    async def delete(self, memory_id):
        memory = await self.get(memory_id)
        if not memory:
            return False
        await self.session.delete(memory)
        await self.session.flush()
        return True

    async def list_memories(self, offset=0, limit=50, is_archived=False):
        count_stmt = select(func.count()).select_from(Memory).where(Memory.is_archived == is_archived)
        total = (await self.session.execute(count_stmt)).scalar()

        stmt = (
            select(Memory)
            .options(selectinload(Memory.tags))
            .where(Memory.is_archived == is_archived)
            .order_by(Memory.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def search_by_tags(self, query=None, tags_any=None, tags_all=None, memory_type=None, source=None, limit=20):
        stmt = select(Memory).options(selectinload(Memory.tags)).where(Memory.is_archived == False)  # noqa: E712

        if query:
            stmt = stmt.where(Memory.content.ilike(f"%{query}%"))

        if tags_any:
            stmt = stmt.where(Memory.tags.any(Tag.name.in_(tags_any)))

        if tags_all:
            for tag_name in tags_all:
                stmt = stmt.where(Memory.tags.any(Tag.name == tag_name))

        if memory_type:
            stmt = stmt.where(Memory.memory_type == memory_type)

        if source:
            stmt = stmt.where(Memory.source == source)

        stmt = stmt.order_by(Memory.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def set_tags(self, memory_id, tag_names):
        memory = await self.get(memory_id)
        if not memory:
            return

        tags = []
        for name in tag_names:
            category = name.split("/")[0] if "/" in name else None
            result = await self.session.execute(select(Tag).where(Tag.name == name))
            tag = result.scalar_one_or_none()
            if not tag:
                tag = Tag(name=name, category=category)
                self.session.add(tag)
                await self.session.flush()
            tags.append(tag)

        memory.tags = tags
        await self.session.flush()


class PostgresTagRepository(TagRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, name, category=None):
        if category is None and "/" in name:
            category = name.split("/")[0]

        result = await self.session.execute(select(Tag).where(Tag.name == name))
        tag = result.scalar_one_or_none()

        if not tag:
            tag = Tag(name=name, category=category)
            self.session.add(tag)
            await self.session.flush()

        return tag

    async def list_all(self):
        result = await self.session.execute(select(Tag).order_by(Tag.name))
        return list(result.scalars().all())

    async def get_with_counts(self):
        stmt = (
            select(Tag, func.count(memory_tags.c.memory_id).label("count"))
            .outerjoin(memory_tags)
            .group_by(Tag.id)
            .order_by(Tag.name)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]


class PostgresApiKeyRepository(ApiKeyRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, name, key_hash, scopes, profile, expires_at=None):
        api_key = ApiKey(name=name, key_hash=key_hash, scopes=scopes, profile=profile, expires_at=expires_at)
        self.session.add(api_key)
        await self.session.flush()
        return api_key

    async def get_by_key_hash(self, key_hash):
        result = await self.session.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
        return result.scalar_one_or_none()

    async def list_all(self):
        result = await self.session.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
        return list(result.scalars().all())

    async def delete(self, key_id):
        result = await self.session.execute(select(ApiKey).where(ApiKey.id == key_id))
        key = result.scalar_one_or_none()
        if not key:
            return False
        await self.session.delete(key)
        await self.session.flush()
        return True

    async def update_last_used(self, key_id):
        result = await self.session.execute(select(ApiKey).where(ApiKey.id == key_id))
        key = result.scalar_one_or_none()
        if key:
            key.last_used_at = datetime.now(timezone.utc)
            await self.session.flush()


class PostgresAuditRepository(AuditRepositoryBase):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(self, action, memory_id=None, api_key_id=None, details=None):
        entry = AuditLog(action=action, memory_id=memory_id, api_key_id=api_key_id, details=details or {})
        self.session.add(entry)
        await self.session.flush()
```

- [ ] **Step 6: Run repository tests**

Run: `cd backend && pytest tests/test_repositories.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/repositories/
git commit -m "feat: add repository layer with Postgres implementations"
```

---

### Task 6: Memory Service

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/memory.py`
- Create: `backend/tests/test_services.py`

- [ ] **Step 1: Write service tests — `backend/tests/test_services.py`**

```python
from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryUpdate
from app.services.memory import MemoryService


async def test_create_memory(session):
    svc = MemoryService(session)
    data = MemoryCreate(content="Service test", tags=["project/test"], source="test")
    memory = await svc.create_memory(data, api_key_id=None)

    assert memory.content == "Service test"
    assert len(memory.tags) == 1
    assert memory.tags[0].name == "project/test"


async def test_get_memory(session):
    svc = MemoryService(session)
    created = await svc.create_memory(MemoryCreate(content="Get me", source="test"), api_key_id=None)
    fetched = await svc.get_memory(created.id)

    assert fetched is not None
    assert fetched.id == created.id


async def test_update_memory(session):
    svc = MemoryService(session)
    created = await svc.create_memory(MemoryCreate(content="Original", source="test"), api_key_id=None)
    updated = await svc.update_memory(created.id, MemoryUpdate(content="Updated"), api_key_id=None)

    assert updated.content == "Updated"


async def test_update_tags(session):
    svc = MemoryService(session)
    created = await svc.create_memory(MemoryCreate(content="Tag test", tags=["tag-a"], source="test"), api_key_id=None)
    updated = await svc.update_memory(created.id, MemoryUpdate(tags=["tag-b", "tag-c"]), api_key_id=None)

    tag_names = [t.name for t in updated.tags]
    assert "tag-b" in tag_names
    assert "tag-c" in tag_names
    assert "tag-a" not in tag_names


async def test_delete_memory(session):
    svc = MemoryService(session)
    created = await svc.create_memory(MemoryCreate(content="Delete me", source="test"), api_key_id=None)

    assert await svc.delete_memory(created.id, api_key_id=None) is True
    assert await svc.get_memory(created.id) is None


async def test_search_memories(session):
    svc = MemoryService(session)
    await svc.create_memory(MemoryCreate(content="Alpha", tags=["scope/a"], source="test"), api_key_id=None)
    await svc.create_memory(MemoryCreate(content="Beta", tags=["scope/b"], source="test"), api_key_id=None)

    results = await svc.search_memories(MemorySearchRequest(tags_any=["scope/a"]))
    assert len(results) == 1
    assert results[0].content == "Alpha"


async def test_search_by_text_query(session):
    svc = MemoryService(session)
    await svc.create_memory(MemoryCreate(content="PostgreSQL is the best database", source="test"), api_key_id=None)
    await svc.create_memory(MemoryCreate(content="Redis is a cache", source="test"), api_key_id=None)

    results = await svc.search_memories(MemorySearchRequest(query="PostgreSQL"))
    assert len(results) == 1
    assert "PostgreSQL" in results[0].content


async def test_list_memories(session):
    svc = MemoryService(session)
    for i in range(3):
        await svc.create_memory(MemoryCreate(content=f"Item {i}", source="test"), api_key_id=None)

    memories, total = await svc.list_memories(offset=0, limit=10)
    assert total == 3
    assert len(memories) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_services.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.memory'`

- [ ] **Step 3: Create `backend/app/services/__init__.py`**

```python
```

- [ ] **Step 4: Create `backend/app/services/memory.py`**

```python
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory
from app.repositories.relational import PostgresAuditRepository, PostgresMemoryRepository
from app.schemas.memory import MemoryCreate, MemorySearchRequest, MemoryUpdate


class MemoryService:
    def __init__(self, session: AsyncSession):
        self.memory_repo = PostgresMemoryRepository(session)
        self.audit_repo = PostgresAuditRepository(session)
        self.session = session

    async def create_memory(self, data: MemoryCreate, api_key_id: UUID | None) -> Memory:
        memory = await self.memory_repo.create(
            content=data.content,
            source=data.source,
            source_agent=data.source_agent,
            memory_type=data.memory_type,
            importance=data.importance,
            metadata=data.metadata,
            expires_at=data.expires_at,
        )

        if data.tags:
            await self.memory_repo.set_tags(memory.id, data.tags)
            await self.session.refresh(memory, ["tags"])

        await self.audit_repo.log("create", memory.id, api_key_id, {"source": data.source})
        return memory

    async def get_memory(self, memory_id: UUID) -> Memory | None:
        return await self.memory_repo.get(memory_id)

    async def update_memory(self, memory_id: UUID, data: MemoryUpdate, api_key_id: UUID | None) -> Memory | None:
        update_fields = data.model_dump(exclude_unset=True, exclude={"tags"})
        memory = await self.memory_repo.update(memory_id, **update_fields)
        if not memory:
            return None

        if data.tags is not None:
            await self.memory_repo.set_tags(memory_id, data.tags)
            await self.session.refresh(memory, ["tags"])

        await self.audit_repo.log("update", memory_id, api_key_id, {"fields": list(update_fields.keys())})
        return memory

    async def delete_memory(self, memory_id: UUID, api_key_id: UUID | None) -> bool:
        result = await self.memory_repo.delete(memory_id)
        if result:
            await self.audit_repo.log("delete", memory_id, api_key_id, {})
        return result

    async def search_memories(self, params: MemorySearchRequest) -> list[Memory]:
        return await self.memory_repo.search_by_tags(
            query=params.query,
            tags_any=params.tags_any,
            tags_all=params.tags_all,
            memory_type=params.memory_type,
            source=params.source,
            limit=params.limit,
        )

    async def list_memories(self, offset: int = 0, limit: int = 50) -> tuple[list[Memory], int]:
        return await self.memory_repo.list_memories(offset=offset, limit=limit)
```

- [ ] **Step 5: Run service tests**

Run: `cd backend && pytest tests/test_services.py -v`
Expected: All 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/ backend/tests/test_services.py
git commit -m "feat: add memory service with CRUD and search"
```

---

### Task 7: Auth Middleware + Dependencies

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/routes/__init__.py`

- [ ] **Step 1: Create `backend/app/api/__init__.py` and `backend/app/api/routes/__init__.py`**

Both empty files.

- [ ] **Step 2: Create `backend/app/api/auth.py`**

```python
import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.api_key import ApiKey
from app.repositories.relational import PostgresApiKeyRepository

security = HTTPBearer()


def generate_api_key(prefix: str | None = None) -> tuple[str, str]:
    prefix = prefix or settings.api_key_prefix
    raw = prefix + secrets.token_hex(24)
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
    session: AsyncSession = Depends(get_session),
) -> ApiKey:
    key_hash = hash_api_key(credentials.credentials)
    repo = PostgresApiKeyRepository(session)
    api_key = await repo.get_by_key_hash(key_hash)

    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    await repo.update_last_used(api_key.id)
    return api_key


def require_scope(scope: str):
    async def _checker(api_key: ApiKey = Depends(get_current_api_key)) -> ApiKey:
        if scope not in api_key.scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Scope '{scope}' required")
        return api_key

    return _checker
```

- [ ] **Step 3: Create `backend/app/api/deps.py`**

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.repositories.relational import PostgresApiKeyRepository, PostgresTagRepository
from app.services.memory import MemoryService


async def get_memory_service(session: AsyncSession = Depends(get_session)) -> MemoryService:
    return MemoryService(session)


async def get_tag_repository(session: AsyncSession = Depends(get_session)) -> PostgresTagRepository:
    return PostgresTagRepository(session)


async def get_api_key_repository(session: AsyncSession = Depends(get_session)) -> PostgresApiKeyRepository:
    return PostgresApiKeyRepository(session)
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/
git commit -m "feat: add API key auth middleware and dependencies"
```

---

### Task 8: REST API — Memory Routes

**Files:**
- Create: `backend/app/api/routes/memories.py`
- Create: `backend/tests/test_api/__init__.py`
- Create: `backend/tests/test_api/test_memories.py`

- [ ] **Step 1: Write API tests — `backend/tests/test_api/__init__.py` and `backend/tests/test_api/test_memories.py`**

`backend/tests/test_api/__init__.py` — empty file.

`backend/tests/test_api/test_memories.py`:

```python
async def test_create_memory(client, auth_headers):
    response = await client.post(
        "/api/v1/memories",
        json={"content": "Test memory", "tags": ["project/test"], "source": "test"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Test memory"
    assert data["tags"] == ["project/test"]
    assert data["source"] == "test"
    assert "id" in data


async def test_create_memory_unauthorized(client):
    response = await client.post("/api/v1/memories", json={"content": "No auth"})
    assert response.status_code == 403


async def test_get_memory(client, auth_headers):
    create = await client.post("/api/v1/memories", json={"content": "Get this"}, headers=auth_headers)
    memory_id = create.json()["id"]

    response = await client.get(f"/api/v1/memories/{memory_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["content"] == "Get this"


async def test_get_memory_not_found(client, auth_headers):
    response = await client.get("/api/v1/memories/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert response.status_code == 404


async def test_update_memory(client, auth_headers):
    create = await client.post("/api/v1/memories", json={"content": "Original"}, headers=auth_headers)
    memory_id = create.json()["id"]

    response = await client.put(f"/api/v1/memories/{memory_id}", json={"content": "Updated"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["content"] == "Updated"


async def test_delete_memory(client, auth_headers):
    create = await client.post("/api/v1/memories", json={"content": "Delete me"}, headers=auth_headers)
    memory_id = create.json()["id"]

    response = await client.delete(f"/api/v1/memories/{memory_id}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get(f"/api/v1/memories/{memory_id}", headers=auth_headers)
    assert response.status_code == 404


async def test_search_memories(client, auth_headers):
    await client.post("/api/v1/memories", json={"content": "Alpha", "tags": ["scope/a"]}, headers=auth_headers)
    await client.post("/api/v1/memories", json={"content": "Beta", "tags": ["scope/b"]}, headers=auth_headers)

    response = await client.post("/api/v1/memories/search", json={"tags_any": ["scope/a"]}, headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["content"] == "Alpha"


async def test_search_by_text(client, auth_headers):
    await client.post("/api/v1/memories", json={"content": "PostgreSQL rocks"}, headers=auth_headers)
    await client.post("/api/v1/memories", json={"content": "Redis is fast"}, headers=auth_headers)

    response = await client.post("/api/v1/memories/search", json={"query": "PostgreSQL"}, headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_batch_create(client, auth_headers):
    response = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [{"content": "Batch 1"}, {"content": "Batch 2"}, {"content": "Batch 3"}]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert len(response.json()) == 3


async def test_scope_enforcement(client, session):
    from app.api.auth import generate_api_key
    from app.models.api_key import ApiKey

    raw_key, key_hash = generate_api_key()
    key = ApiKey(name="read-only", key_hash=key_hash, scopes=["read"])
    session.add(key)
    await session.flush()

    headers = {"Authorization": f"Bearer {raw_key}"}

    get_resp = await client.post("/api/v1/memories/search", json={}, headers=headers)
    assert get_resp.status_code == 200

    post_resp = await client.post("/api/v1/memories", json={"content": "Nope"}, headers=headers)
    assert post_resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_api/test_memories.py -v`
Expected: FAIL — route not found (404 for all requests).

- [ ] **Step 3: Create `backend/app/api/routes/memories.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import require_scope
from app.api.deps import get_memory_service
from app.models.api_key import ApiKey
from app.models.memory import Memory
from app.schemas.memory import MemoryBatchCreate, MemoryCreate, MemoryResponse, MemorySearchRequest, MemoryUpdate
from app.services.memory import MemoryService

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


def _to_response(memory: Memory) -> MemoryResponse:
    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        source=memory.source,
        source_agent=memory.source_agent,
        memory_type=memory.memory_type,
        importance=memory.importance,
        metadata=memory.metadata_,
        tags=[t.name for t in memory.tags],
        created_at=memory.created_at,
        updated_at=memory.updated_at,
        expires_at=memory.expires_at,
        is_archived=memory.is_archived,
    )


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    body: MemoryCreate,
    api_key: ApiKey = Depends(require_scope("write")),
    service: MemoryService = Depends(get_memory_service),
):
    memory = await service.create_memory(body, api_key.id)
    return _to_response(memory)


@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(
    memory_id: UUID,
    api_key: ApiKey = Depends(require_scope("read")),
    service: MemoryService = Depends(get_memory_service),
):
    memory = await service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return _to_response(memory)


@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: UUID,
    body: MemoryUpdate,
    api_key: ApiKey = Depends(require_scope("write")),
    service: MemoryService = Depends(get_memory_service),
):
    memory = await service.update_memory(memory_id, body, api_key.id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return _to_response(memory)


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: UUID,
    api_key: ApiKey = Depends(require_scope("write")),
    service: MemoryService = Depends(get_memory_service),
):
    if not await service.delete_memory(memory_id, api_key.id):
        raise HTTPException(status_code=404, detail="Memory not found")


@router.post("/search", response_model=list[MemoryResponse])
async def search_memories(
    body: MemorySearchRequest,
    api_key: ApiKey = Depends(require_scope("read")),
    service: MemoryService = Depends(get_memory_service),
):
    memories = await service.search_memories(body)
    return [_to_response(m) for m in memories]


@router.post("/batch", response_model=list[MemoryResponse], status_code=status.HTTP_201_CREATED)
async def batch_create(
    body: MemoryBatchCreate,
    api_key: ApiKey = Depends(require_scope("write")),
    service: MemoryService = Depends(get_memory_service),
):
    results = []
    for entry in body.entries:
        memory = await service.create_memory(entry, api_key.id)
        results.append(_to_response(memory))
    return results
```

- [ ] **Step 4: Wire routes into `backend/app/main.py`**

Replace the file content:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import keys, memories, tags


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="darkmem", version="0.1.0", description="Centralized memory system for AI agents", lifespan=lifespan)

app.include_router(memories.router)
app.include_router(tags.router)
app.include_router(keys.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

Note: `tags` and `keys` routes are created in the next task. For this step, create placeholder files so the import works:

`backend/app/api/routes/tags.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])
```

`backend/app/api/routes/keys.py`:
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/keys", tags=["api-keys"])
```

- [ ] **Step 5: Run API tests**

Run: `cd backend && pytest tests/test_api/test_memories.py -v`
Expected: All 10 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/memories.py backend/app/api/routes/tags.py backend/app/api/routes/keys.py backend/app/main.py backend/tests/test_api/
git commit -m "feat: add memory REST API routes with auth"
```

---

### Task 9: REST API — Tags + Keys Routes

**Files:**
- Modify: `backend/app/api/routes/tags.py`
- Modify: `backend/app/api/routes/keys.py`
- Create: `backend/tests/test_api/test_tags.py`
- Create: `backend/tests/test_api/test_keys.py`

- [ ] **Step 1: Write tag + key tests**

`backend/tests/test_api/test_tags.py`:

```python
async def test_list_tags_empty(client, auth_headers):
    response = await client.get("/api/v1/tags", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_list_tags_with_counts(client, auth_headers):
    await client.post("/api/v1/memories", json={"content": "A", "tags": ["project/test"]}, headers=auth_headers)
    await client.post("/api/v1/memories", json={"content": "B", "tags": ["project/test", "infra/db"]}, headers=auth_headers)

    response = await client.get("/api/v1/tags", headers=auth_headers)
    assert response.status_code == 200
    tags = response.json()
    assert len(tags) == 2

    test_tag = next(t for t in tags if t["name"] == "project/test")
    assert test_tag["memory_count"] == 2
    assert test_tag["category"] == "project"
```

`backend/tests/test_api/test_keys.py`:

```python
async def test_create_api_key(client, auth_headers):
    response = await client.post(
        "/api/v1/keys",
        json={"name": "new-key", "scopes": ["read"]},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "new-key"
    assert data["scopes"] == ["read"]
    assert data["raw_key"].startswith("dm_")


async def test_list_api_keys(client, auth_headers):
    response = await client.get("/api/v1/keys", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


async def test_delete_api_key(client, auth_headers):
    create = await client.post("/api/v1/keys", json={"name": "ephemeral"}, headers=auth_headers)
    key_id = create.json()["id"]

    response = await client.delete(f"/api/v1/keys/{key_id}", headers=auth_headers)
    assert response.status_code == 204


async def test_keys_require_admin_scope(client, session):
    from app.api.auth import generate_api_key
    from app.models.api_key import ApiKey

    raw_key, key_hash = generate_api_key()
    key = ApiKey(name="non-admin", key_hash=key_hash, scopes=["read", "write"])
    session.add(key)
    await session.flush()

    headers = {"Authorization": f"Bearer {raw_key}"}
    response = await client.get("/api/v1/keys", headers=headers)
    assert response.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_api/test_tags.py tests/test_api/test_keys.py -v`
Expected: FAIL — routes return 404 or empty responses.

- [ ] **Step 3: Implement `backend/app/api/routes/tags.py`**

```python
from fastapi import APIRouter, Depends

from app.api.auth import require_scope
from app.api.deps import get_tag_repository
from app.repositories.relational import PostgresTagRepository
from app.schemas.tag import TagResponse

router = APIRouter(prefix="/api/v1/tags", tags=["tags"])


@router.get("", response_model=list[TagResponse])
async def list_tags(
    _api_key=Depends(require_scope("read")),
    tag_repo: PostgresTagRepository = Depends(get_tag_repository),
):
    tags_with_counts = await tag_repo.get_with_counts()
    return [
        TagResponse(id=tag.id, name=tag.name, category=tag.category, memory_count=count)
        for tag, count in tags_with_counts
    ]
```

- [ ] **Step 4: Implement `backend/app/api/routes/keys.py`**

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import generate_api_key, require_scope
from app.api.deps import get_api_key_repository
from app.repositories.relational import PostgresApiKeyRepository
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse

router = APIRouter(prefix="/api/v1/keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: ApiKeyCreate,
    _api_key=Depends(require_scope("admin")),
    repo: PostgresApiKeyRepository = Depends(get_api_key_repository),
):
    raw_key, key_hash = generate_api_key()
    new_key = await repo.create(
        name=body.name,
        key_hash=key_hash,
        scopes=body.scopes,
        profile=body.profile,
        expires_at=body.expires_at,
    )
    return ApiKeyCreatedResponse(
        id=new_key.id,
        name=new_key.name,
        scopes=new_key.scopes,
        profile=new_key.profile,
        created_at=new_key.created_at,
        last_used_at=new_key.last_used_at,
        expires_at=new_key.expires_at,
        raw_key=raw_key,
    )


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    _api_key=Depends(require_scope("admin")),
    repo: PostgresApiKeyRepository = Depends(get_api_key_repository),
):
    keys = await repo.list_all()
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: UUID,
    _api_key=Depends(require_scope("admin")),
    repo: PostgresApiKeyRepository = Depends(get_api_key_repository),
):
    if not await repo.delete(key_id):
        raise HTTPException(status_code=404, detail="API key not found")
```

- [ ] **Step 5: Run all tests**

Run: `cd backend && pytest -v`
Expected: All tests PASS (models: 4, repositories: 8, services: 8, API memories: 10, API tags: 2, API keys: 4 = ~36 total).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/tags.py backend/app/api/routes/keys.py backend/tests/test_api/test_tags.py backend/tests/test_api/test_keys.py
git commit -m "feat: add tags and API keys REST routes"
```

---

### Task 10: End-to-End Verification

**Files:** None new — verification only.

- [ ] **Step 1: Start full dev stack**

```bash
docker compose -f docker-compose.dev.yml up -d
```

Expected: All 4 containers start (darkmem-api, postgres, qdrant, neo4j).

- [ ] **Step 2: Create first API key via startup seed**

Since the API requires auth and there's no key yet, create one directly:

```bash
docker compose -f docker-compose.dev.yml exec darkmem-api python -c "
import asyncio
from app.database import async_session_factory
from app.api.auth import generate_api_key
from app.models.api_key import ApiKey

async def seed():
    async with async_session_factory() as session:
        raw_key, key_hash = generate_api_key()
        key = ApiKey(name='admin', key_hash=key_hash, scopes=['read', 'write', 'admin'])
        session.add(key)
        await session.commit()
        print(f'API Key: {raw_key}')

asyncio.run(seed())
"
```

Save the printed API key.

- [ ] **Step 3: Test endpoints with curl**

```bash
# Health check
curl http://localhost:8000/health

# Create memory
curl -X POST http://localhost:8000/api/v1/memories \
  -H "Authorization: Bearer <YOUR_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"content": "darkmem is running!", "tags": ["project/darkmem", "milestone/v1"]}'

# Search
curl -X POST http://localhost:8000/api/v1/memories/search \
  -H "Authorization: Bearer <YOUR_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"tags_any": ["project/darkmem"]}'

# List tags
curl http://localhost:8000/api/v1/tags \
  -H "Authorization: Bearer <YOUR_KEY>"
```

Expected: All return valid JSON responses with correct data.

- [ ] **Step 4: Run full test suite one final time**

```bash
cd backend && pytest -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "chore: end-to-end verification complete"
```

---

## Limitations of Plan 1

The following are **not** implemented in this plan and will be addressed in subsequent plans:

- **Semantic search** — `query` field does ILIKE text match, not vector similarity (Plan 2)
- **Entity extraction** — no LLM processing on memory creation (Plan 2)
- **Knowledge graph** — Neo4j is running but unused (Plan 2)
- **Vector embeddings** — Qdrant is running but unused (Plan 2)
- **MCP server** — no MCP interface yet (Plan 3)
- **WebSocket** — no live events (Plan 3)
- **System prompt profiles** — table exists but no API/seed data (Plan 3)
- **Frontend dashboard** — no UI (Plan 4)
- **Production compose** — no `docker-compose.yml` or build scripts (Plan 4)
- **Merge/duplicate endpoints** — `/memories/{id}/merge` and `/memories/duplicates` (Plan 2, needs vector similarity)
