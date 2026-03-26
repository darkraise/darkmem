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
