export interface PipelineStatus {
  memory_id: string
  embed: string
  extract: string
  vector: string
  graph: string
  entities_count: number
  relations_count: number
  error: string | null
}

export interface MemoryDeleted {
  memory_id: string
}

export interface RepoCloneStarted {
  repo_id: string
  name: string
}

export interface RepoCloneCompleted {
  repo_id: string
  name: string
}

export interface RepoCloneFailed {
  repo_id: string
  error: string
}

export interface RepoIndexingStarted {
  repo_id: string
  total_files: number
}

export interface RepoIndexingProgress {
  repo_id: string
  phase: number
  current: number
  total: number
}

export interface RepoIndexingCompleted {
  repo_id: string
  files_changed: number
  symbols_indexed: number
}

export interface RepoIndexingFailed {
  repo_id: string
  error: string
}

export interface EnrichmentBatchCompleted {
  processed: number
  pending_remaining: number
}

export interface PipelineFailureUpdated {
  failure_id: string
  entity_type: string
  entity_id: string
  pipeline_name: string
  state: "recorded" | "resolved" | "forgotten"
  failed_step: string | null
  attempts: number
  error_message: string | null
}

export interface PipelineRetryBatchProgress {
  batch_id: string
  current: number
  total: number
  processed: number
  errors: number
  entity_type: string | null
  entity_id: string | null
  state: "started" | "progress" | "done"
}

export interface PipelineReembedBatchProgress {
  batch_id: string
  category: "memories" | "code_chunks" | "entities"
  current: number
  total: number
  processed: number
  errors: number
  state: "started" | "progress" | "done"
  error_message: string | null
}

export type WebSocketEventMap = {
  "pipeline.completed": PipelineStatus
  "pipeline.partial": PipelineStatus
  "pipeline.failed": PipelineStatus
  "pipeline.failure.updated": PipelineFailureUpdated
  "pipeline.retry_batch.progress": PipelineRetryBatchProgress
  "pipeline.reembed_batch.progress": PipelineReembedBatchProgress
  "memory.deleted": MemoryDeleted
  "repo.clone_started": RepoCloneStarted
  "repo.clone_completed": RepoCloneCompleted
  "repo.clone_failed": RepoCloneFailed
  "repo.indexing_started": RepoIndexingStarted
  "repo.indexing_progress": RepoIndexingProgress
  "repo.indexing_completed": RepoIndexingCompleted
  "repo.indexing_failed": RepoIndexingFailed
  "enrichment.batch_completed": EnrichmentBatchCompleted
}
