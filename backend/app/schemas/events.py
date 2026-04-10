from typing import Literal

from pydantic import BaseModel


class PipelineStatus(BaseModel):
    memory_id: str
    embed: str
    extract: str
    vector: str
    graph: str
    entities_count: int
    relations_count: int
    error: str | None


class MemoryDeleted(BaseModel):
    memory_id: str


class RepoCloneStarted(BaseModel):
    repo_id: str
    name: str


class RepoCloneCompleted(BaseModel):
    repo_id: str
    name: str


class RepoCloneFailed(BaseModel):
    repo_id: str
    error: str


class RepoIndexingStarted(BaseModel):
    repo_id: str
    total_files: int


class RepoIndexingProgress(BaseModel):
    repo_id: str
    phase: int
    current: int
    total: int


class RepoIndexingCompleted(BaseModel):
    repo_id: str
    files_changed: int
    symbols_indexed: int


class RepoIndexingFailed(BaseModel):
    repo_id: str
    error: str


class EnrichmentBatchCompleted(BaseModel):
    processed: int
    pending_remaining: int


class PipelineFailureUpdated(BaseModel):
    failure_id: str
    entity_type: str
    entity_id: str
    pipeline_name: str
    state: Literal["recorded", "resolved", "forgotten"]
    failed_step: str | None
    attempts: int
    error_message: str | None


class PipelineRetryBatchProgress(BaseModel):
    batch_id: str
    current: int
    total: int
    processed: int
    errors: int
    entity_type: str | None
    entity_id: str | None
    state: Literal["started", "progress", "done"]


class PipelineReembedBatchProgress(BaseModel):
    batch_id: str
    category: Literal["memories", "code_chunks", "entities"]
    current: int
    total: int
    processed: int
    errors: int
    state: Literal["started", "progress", "done"]
    error_message: str | None = None


EVENT_SCHEMAS: dict[str, type[BaseModel]] = {
    "pipeline.completed": PipelineStatus,
    "pipeline.partial": PipelineStatus,
    "pipeline.failed": PipelineStatus,
    "pipeline.failure.updated": PipelineFailureUpdated,
    "pipeline.retry_batch.progress": PipelineRetryBatchProgress,
    "pipeline.reembed_batch.progress": PipelineReembedBatchProgress,
    "memory.deleted": MemoryDeleted,
    "repo.clone_started": RepoCloneStarted,
    "repo.clone_completed": RepoCloneCompleted,
    "repo.clone_failed": RepoCloneFailed,
    "repo.indexing_started": RepoIndexingStarted,
    "repo.indexing_progress": RepoIndexingProgress,
    "repo.indexing_completed": RepoIndexingCompleted,
    "repo.indexing_failed": RepoIndexingFailed,
    "enrichment.batch_completed": EnrichmentBatchCompleted,
}
