from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="darkmem", version="0.1.0", description="Centralized memory system for AI agents", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}
