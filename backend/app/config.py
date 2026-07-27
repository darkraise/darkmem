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


class LLMPurposeConfig(BaseModel):
    base_url: str = "http://localhost:11434/v1"
    model: str = "nomic-embed-text"
    api_key: str | None = None
    dimensions: int | None = None
    reasoning: bool = False
    # Which API surface to call, and the sole axis a vendor difference is
    # expressed on: auth scheme, reasoning-disable knob, structured-output
    # caveat, and missing endpoints all resolve through the quirk table in
    # ``app/services/llm_quirks.py`` (doc 11 §4).
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
        base_url="http://localhost:11434/v1",
        model="qwen3-embedding:0.6b", dimensions=1024,
    )
    llm_extraction: LLMPurposeConfig = LLMPurposeConfig(
        base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0},
    )
    llm_classification: LLMPurposeConfig = LLMPurposeConfig(
        base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0},
    )
    llm_reasoning: LLMPurposeConfig = LLMPurposeConfig(
        base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0.7},
    )
    llm_summarization: LLMPurposeConfig = LLMPurposeConfig(
        base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0.3},
    )
    llm_reranker: LLMPurposeConfig = LLMPurposeConfig(
        base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0},
    )
    # Tier-C purposes, seeded inert (doc 11 §6). No consumer dispatches on
    # either yet: `synthesis` gets its first writer in T3.02 (Layer-3 article
    # write-ups), `verification` in T2.26 (the contradiction check behind the
    # dispute veto, and article claim-level entailment). They are resolvable
    # from day one because doc 11 §6 requires the seed and the PURPOSES sweep to
    # land BEFORE any consumer dispatches — a consumer reaching an unseeded
    # purpose is the same class of bug as a feature emitting an untabled type.
    llm_synthesis: LLMPurposeConfig = LLMPurposeConfig(
        base_url="http://localhost:11434/v1",
        model="qwen2.5:3b", params={"temperature": 0.3},
    )
    llm_verification: LLMPurposeConfig = LLMPurposeConfig(
        base_url="http://localhost:11434/v1",
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
