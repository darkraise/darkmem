import logging
import os
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_config_logger = logging.getLogger(__name__)

_DEFAULT_MODELS_DIR = Path(__file__).resolve().parents[2] / "fine-tuning" / "models"


class LLMPurposeConfig(BaseModel):
    provider: str = "ollama"
    base_url: str = "http://localhost:11434/v1"
    model: str = "nomic-embed-text"
    api_key: str | None = None
    dimensions: int | None = None
    reasoning: bool = False
    tool_call_mode: str = "json"
    params: dict = Field(default_factory=dict)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem"
    test_database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test"
    jwt_secret: str = "darkmem-jwt-secret-change-me"
    environment: str = "development"
    embedding_dimensions: int = 1024
    cors_origins: list[str] = []
    setup_secret: str | None = None
    db_pool_size: int = 20
    db_max_overflow: int = 10

    @model_validator(mode="after")
    def _check_jwt_secret(self):
        is_default = self.jwt_secret == "darkmem-jwt-secret-change-me"
        is_short = len(self.jwt_secret) < 32
        is_prod = self.environment == "production" or os.path.exists("/.dockerenv")
        if is_prod and (is_default or is_short):
            raise ValueError("JWT_SECRET must be at least 32 characters and not the default in production")
        if is_default or is_short:
            _config_logger.warning("JWT_SECRET is weak — set a 32+ character secret for production")
        return self

    @model_validator(mode="after")
    def _check_cors_origins(self):
        if self.cors_origins and "*" in self.cors_origins:
            _config_logger.warning(
                "Removed '*' from CORS_ORIGINS — incompatible with allow_credentials=True"
            )
            self.cors_origins = [o for o in self.cors_origins if o != "*"]
        return self

    llm_embedding: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen3-embedding:0.6b", dimensions=1024,
    )
    llm_extraction: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0},
    )
    llm_classification: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0},
    )
    llm_reasoning: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0.7},
    )
    llm_summarization: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0.3},
    )
    llm_reranker: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0},
    )


class MLPipelineSettings(BaseSettings):
    """Settings for the local ML extraction/classification/retrieval pipeline.

    These govern the fine-tuned head loader at startup and runtime inference.
    Feature flags in the DB (ml_extraction, ml_classification, ml_retrieval)
    decide whether the ML path is used per request; these settings decide
    how the models are loaded and where they live.

    Each head can be sourced either from a local directory (``models_dir``)
    or from a HuggingFace Hub repo (``hub_*_repo``). When a ``hub_*_repo`` is
    set, the Hub wins and the model is fetched via ``from_pretrained`` with
    ``cache_dir`` pointing at ``hub_cache_dir`` (HF default when None). Leave
    every ``hub_*_repo`` unset to stay on local files (dev default).
    """

    model_config = SettingsConfigDict(env_prefix="ML_PIPELINE_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    enabled: bool = True
    device: str = "auto"
    models_dir: Path = _DEFAULT_MODELS_DIR
    cpu_fallback: bool = True

    hub_token: str | None = None
    hub_cache_dir: Path | None = None
    hub_span_repo: str | None = None
    hub_span_revision: str = "main"
    hub_typer_repo: str | None = None
    hub_typer_revision: str = "main"
    hub_relation_repo: str | None = None
    hub_relation_revision: str = "main"
    hub_classifier_repo: str | None = None
    hub_classifier_revision: str = "main"
    hub_retriever_repo: str | None = None
    hub_retriever_revision: str = "main"

    span_threshold: float = 0.4
    span_nms_iou: float = 0.3
    span_max_length: int = 384

    typer_batch_size: int = 16
    typer_max_length: int = 256
    typer_abstain_margin: float = 0.0

    relation_num_beams: int = 4
    relation_max_source_length: int = 256
    relation_max_target_length: int = 128

    classifier_max_length: int = 256

    retriever_batch_size: int = 32
    retriever_max_length: int = 256
    retriever_query_prefix: str = "Represent this sentence for searching relevant passages: "


settings = Settings()
ml_pipeline_settings = MLPipelineSettings()

FEATURE_FLAGS_DEFAULTS: dict[str, object] = {
    "llm_enrichment_enabled": False,
    "hybrid_search_enabled": True,
    "reranker_enabled": False,
    "pipeline_concurrency": 5,
    "classification_areas": ["general", "technical", "debugging", "infrastructure"],
    "classification_mode": "simple",
    "embedding_batch_size": 20,
    "embedding_concurrency": 1,
    "entity_cache_ttl_minutes": 60,
    "ml_extraction": False,
    "ml_classification": False,
    "ml_retrieval": False,
    "ml_shadow_mode": False,
    "confidence_rank_gamma": 0.0,
    "ml_device": "auto",  # one of: "auto", "cpu", "cuda"
    "ml_cuda_index": 0,   # applied when ml_device in {"auto", "cuda"} and CUDA is available
    # Minutes of inactivity after which a loaded ML group is evicted from
    # memory. 0 disables eviction (keep loaded forever). Groups are loaded
    # lazily on first use; this knob only controls how long they stay hot.
    "ml_idle_ttl_minutes": 30,
    "ml_eviction_check_interval_seconds": 60,
}
