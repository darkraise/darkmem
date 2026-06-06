import logging
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMApiKind = Literal[
    "openai",     # Generic OpenAI-compatible /chat/completions, /embeddings.
    "ollama",     # Ollama native /api/chat, /api/embed (think:false support).
    "anthropic",  # Anthropic native /v1/messages — currently dispatches via the
                  # OpenAI-compatible path; plug a native adapter into
                  # ``LLMOrchestrator`` to start using /v1/messages directly.
    "google",     # Google Gemini native — currently dispatches via the
                  # OpenAI-compatible path under /v1beta/openai. Future native
                  # adapter will use the generativelanguage REST surface.
    "deepseek",   # DeepSeek native — currently dispatches via OpenAI compat.
    "zai",        # z.ai (Zhipu / GLM) native — currently dispatches via OpenAI
                  # compat at /api/paas/v4. Native adapter to be added.
]

_config_logger = logging.getLogger(__name__)


class LLMProviderProfile(BaseModel):
    """Reusable connection profile for an LLM provider.

    A purpose (extraction, reasoning, ...) can reference a profile by name
    via ``LLMPurposeConfig.provider_ref``; the resolution step in
    ``get_llm_config`` then overlays this profile's connection fields onto
    the per-purpose row so callers downstream see a fully populated config.
    Lets the user rotate the API key in one place instead of six.

    ``api_kind`` selects the wire protocol. ``"openai"`` posts to the
    standard ``/chat/completions`` and ``/embeddings`` endpoints, working
    against any vendor's OpenAI-compatible surface. ``"ollama"`` posts to
    Ollama's native ``/api/chat`` and ``/api/embed`` and adds the
    ``think: false`` flag to disable qwen3-style internal reasoning that
    the compat shim cannot turn off. The vendor-specific kinds
    (``"anthropic"``, ``"google"``, ``"deepseek"``, ``"zai"``) reserve a
    slot for a future native adapter; today they dispatch through the
    OpenAI-compatible path so cloud profiles keep working with their
    vendor's compat endpoint.
    """

    provider: str = "openai"
    base_url: str = "http://localhost:11434/v1"
    api_key: str | None = None
    api_kind: LLMApiKind = "openai"
    # Some vendors (Anthropic, DeepSeek today) only expose chat completions
    # on their OpenAI-compat layer and have no embeddings endpoint. The UI
    # consults this flag to grey out the embedding purpose's profile picker
    # so a user can't link an unsupported profile and silently 404 on every
    # embed call.
    supports_embedding: bool = True


class LLMProfile(BaseModel):
    """Reusable preset for one purpose's full LLM config.

    A profile bundles a Provider reference with default model + params +
    purpose-style flags. The UI picks a profile in the LLM purpose card
    to populate the form fields with sensible starting values; the
    purpose row stores the resolved values directly so changing a
    profile after the fact doesn't silently retune already-saved
    purposes.

    Use ``is_embedding=True`` for embedding-only purposes (the
    ``reasoning`` flag is meaningless there). Use ``reasoning=True`` to
    flag chat-style purposes whose model supports internal reasoning
    (qwen3 family, gpt-5 family, etc.).
    """

    provider_ref: str
    model: str
    params: dict = Field(default_factory=dict)
    is_embedding: bool = False
    reasoning: bool = False


class LLMPurposeConfig(BaseModel):
    provider: str = "ollama"
    base_url: str = "http://localhost:11434/v1"
    model: str = "nomic-embed-text"
    api_key: str | None = None
    dimensions: int | None = None
    reasoning: bool = False
    # Which API surface to call. ``openai`` uses the OpenAI-compatible
    # ``/v1/chat/completions`` and ``/v1/embeddings`` endpoints (works with
    # OpenAI itself, Anthropic via translation layers, vLLM, and Ollama's
    # compat mode). ``ollama`` uses Ollama's native ``/api/chat`` and
    # ``/api/embed`` endpoints, which expose ``think: false`` to disable
    # qwen3-style internal reasoning that the OpenAI compat shim ignores.
    api_kind: LLMApiKind = "openai"
    params: dict = Field(default_factory=dict)
    # Optional reference to an entry in the ``llm_providers`` table.
    # When set, the resolution step overlays that provider's
    # provider/base_url/api_key/api_kind onto this purpose, leaving model,
    # params, and per-purpose toggles intact. ``None`` means this purpose
    # carries its own connection details inline.
    provider_ref: str | None = None
    # Optional reference to an entry in the ``llm_profiles`` table — the
    # explicit "selected profile" link the UI dropdown reads. Cleared
    # when the user manually edits a field that diverges from the
    # profile's preset.
    profile_ref: str | None = None
    # Optional reference to an entry in the ``ml_profiles`` table —
    # when set, the classifier purpose dispatches to the in-process
    # MLClassificationService instead of the LLM-backed one.
    ml_profile_ref: str | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem"
    test_database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test"
    jwt_secret: str = "darkmem-jwt-secret-change-me"
    environment: str = "development"
    embedding_dimensions: int = 1024
    cors_origins: list[str] = []
    # Only honor X-Forwarded-For (e.g. for the login rate limiter) when fronted by
    # a trusted reverse proxy; otherwise a client could spoof the header.
    trust_proxy_headers: bool = False
    setup_secret: str | None = None
    db_pool_size: int = 20
    db_max_overflow: int = 10

    @model_validator(mode="after")
    def _check_jwt_secret(self):
        is_default = self.jwt_secret == "darkmem-jwt-secret-change-me"
        is_short = len(self.jwt_secret) < 32
        is_prod = self.environment == "production"
        if is_prod and (is_default or is_short):
            raise ValueError("JWT_SECRET must be at least 32 characters and not the default in production")
        if is_default or is_short:
            _config_logger.warning("JWT_SECRET is weak — set a 32+ character secret for production")
        return self

    @model_validator(mode="after")
    def _check_setup_secret(self):
        # /setup is a one-shot admin-bootstrap endpoint that becomes inert
        # once the admin password row exists. The window between server
        # start and the operator running setup is real on a shared local
        # network — anyone reachable can claim admin first if the secret
        # guard is unset. Require a non-empty secret in production.
        is_prod = self.environment == "production"
        if is_prod and not self.setup_secret:
            raise ValueError(
                "SETUP_SECRET must be set in production so /setup cannot be called "
                "by anyone reaching the server before the operator runs setup"
            )
        if not self.setup_secret:
            _config_logger.warning(
                "SETUP_SECRET is unset — /setup is unauthenticated until the admin password is set"
            )
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


settings = Settings()

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
    # Pattern-based relation rescue (adjacency + subject-tracking + REPLACES).
    # Adds inferred triples for connector phrases the model misses. Disable
    # to evaluate raw recall or when the heuristics over-fire.
    "relation_rescue": True,
    "confidence_rank_gamma": 0.0,
}
