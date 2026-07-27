import logging
from typing import Literal
from urllib.parse import quote

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
    # ``llm`` | ``local`` on the classification purpose: which classifier
    # serves it. ``local`` selects the in-process classifier, anything else
    # (including None) the LLM-backed one. This replaced the deleted
    # ``ml_profiles`` reference in T0.12c (doc 04 §7); T1.04 owns wiring the
    # dispatch to read it, T1.18 the narrowing path.
    classifier_kind: str | None = None
    # Inert on the wire, not in the resolution path: the provider/profile
    # indirection is gone (doc 04 §7), but these three keys still appear in
    # the config API response the frontend reads. Retiring them from the
    # contract is T1.42b's.
    provider_ref: str | None = None
    profile_ref: str | None = None
    ml_profile_ref: str | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Postgres connection, each piece overridable via its own env var
    # (DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME). DATABASE_URL is
    # derived from these when not set explicitly; set DATABASE_URL directly to
    # point at any other Postgres. The default host is 'localhost' (host-side
    # dev / pytest) — the compose files pass DB_HOST so the API reaches the
    # bundled service over the container network.
    db_user: str = "darkmem"
    db_password: str = "darkmem"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "darkmem"
    database_url: str | None = None
    test_database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test"
    jwt_secret: str = "darkmem-jwt-secret-change-me"
    environment: str = "development"
    embedding_dimensions: int = 1024
    cors_origins: list[str] = []
    # The API is always fronted by the bundled nginx, a trusted reverse proxy,
    # so honoring X-Forwarded-For (for the login rate limiter) is the default.
    # Set false only if the API is exposed with no trusted proxy in front.
    trust_proxy_headers: bool = True
    # Session-cookie Secure flag. None derives it from ``environment`` (Secure
    # in production). Set false to allow login over plain HTTP on a trusted LAN.
    cookie_secure: bool | None = None
    db_pool_size: int = 30
    db_max_overflow: int = 20
    log_level: str = "INFO"
    # Comma-separated Host values allowed to reach the MCP endpoint (DNS-rebinding
    # protection). Empty → localhost only; LAN agents must be added, e.g.
    # "192.168.0.195:8000" or "192.168.0.195:*". Set to "*" to disable the check.
    mcp_allowed_hosts: str = ""

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
    def _check_cors_origins(self):
        if self.cors_origins and "*" in self.cors_origins:
            _config_logger.warning(
                "Removed '*' from CORS_ORIGINS — incompatible with allow_credentials=True"
            )
            self.cors_origins = [o for o in self.cors_origins if o != "*"]
        return self

    @model_validator(mode="after")
    def _derive_database_url(self):
        if not self.database_url:
            # Percent-encode the credentials so URL-significant characters in a
            # password (e.g. '@', ':', '/') don't corrupt URL parsing — an
            # unescaped '@' otherwise gets read as the start of the host.
            user = quote(self.db_user, safe="")
            password = quote(self.db_password, safe="")
            self.database_url = (
                f"postgresql+asyncpg://{user}:{password}"
                f"@{self.db_host}:{self.db_port}/{self.db_name}"
            )
        return self

    @property
    def session_cookie_secure(self) -> bool:
        """Whether the session cookie carries the Secure (HTTPS-only) flag.

        Decoupled from ``environment`` so a deployment can keep the production
        security validators while still serving login over plain HTTP on a
        trusted LAN. ``None`` (the default) preserves the historical behavior:
        Secure only in production.
        """
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.environment == "production"

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
