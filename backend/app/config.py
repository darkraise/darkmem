import logging
from typing import Literal
from urllib.parse import quote

from pydantic import AliasChoices, BaseModel, Field, model_validator
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

# The classification purpose's inline classifier selector. Two values only:
# `resolve_classifier` treats anything that is not "local" as the LLM, so a
# free-form third value would be silently misread rather than refused.
ClassifierKind = Literal["llm", "local"]

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
    # Which ``llm_providers`` row the three connection fields above were
    # resolved from. A label for the settings surface, never an input to a
    # call: both hashers over a resolved config fold a fixed list of named
    # behaviour-shaping fields and this is deliberately not among them, because
    # renaming a provider must invalidate neither a bench cache nor a judge
    # qualification. None when the purpose has no row and resolution fell back
    # to the ``Settings`` default.
    provider_name: str | None = None


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
    # The backup worker's app-side posture (spec §9.5 as redesigned after B1).
    # NOT the enforcement: that is the SELECT-only `darkmem_viewer` role
    # beneath every code path. This flag only (a) skips boot writers and never
    # arms the job registry, (b) makes known write-on-read paths no-op instead
    # of erroring under the role, (c) refuses the doors whose failure mode is
    # money or a broken viewer session rather than a clean database refusal.
    # A reader who takes away "the flag makes it read-only" has been misled.
    read_only: bool = Field(
        default=False,
        validation_alias=AliasChoices("DARKMEM_READ_ONLY", "READ_ONLY"),
    )
    environment: str = "development"
    embedding_dimensions: int = 1024
    cors_origins: list[str] = []
    # The app is the network edge: it serves the SPA, the API and /mcp itself,
    # with nothing trustworthy in front. So proxy headers are ignored and the
    # transport peer decides the login rate limiter's bucket — a client that
    # could name its own IP could rotate buckets per guess and never lock out.
    # Set true only when a trusted proxy really is in front (an operator's TLS
    # proxy; the nginx-in-image fallback is recorded and not taken). This is
    # the exposed-deployment switch, not only a limiter setting: it also
    # collapses the ``cookie_secure`` tri-state to enforced — see
    # ``session_cookie_secure`` and docs/runbook-exposed-deployment.md.
    trust_proxy_headers: bool = False
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
    # Directory holding the built SPA. Unset resolves the packaged location
    # (``web/`` beside the app package, i.e. /app/web in the image); set it to
    # frontend/dist to serve a host-side build.
    spa_dir: str | None = None
    # Page attachments on disk. Relative for host-side dev; the image mounts a
    # named volume at /app/data/attachments and sets ATTACHMENTS_DIR to it.
    attachments_dir: str = "./data/attachments"
    attachment_max_bytes: int = 52_428_800
    # Notion import ceilings. Operator-level limits rather than job config:
    # no job exists here, and FieldDescriptor.default is typed int anyway.
    # The measured real export is 34.5 MB / 2260 entries / 2193 pages.
    notion_import_max_bytes: int = 1_073_741_824
    notion_import_max_entries: int = 50_000
    notion_import_max_uncompressed_bytes: int = 5_368_709_120
    notion_import_max_pages: int = 10_000
    # Bounds the plan's peak memory, which is held entirely in the process.
    notion_import_max_blocks: int = 250_000
    notion_import_max_seconds: int = 900

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
    def _warn_cookie_secure_clamped(self):
        if self.trust_proxy_headers and self.cookie_secure is False:
            _config_logger.warning(
                "COOKIE_SECURE=false is clamped to true: TRUST_PROXY_HEADERS=true is "
                "the exposed posture, where the session cookie must not travel "
                "unprotected. A plain-HTTP LAN deployment leaves TRUST_PROXY_HEADERS off."
            )
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

        The tri-state collapses to enforced in the exposed posture (doc 18 §9).
        In this tree the only live reason to trust proxy headers is an operator
        TLS proxy in front — the nginx-in-image fallback is recorded and not
        taken (doc 03 (b)), and the app is the edge otherwise — so
        ``trust_proxy_headers`` *is* the "TLS exists" signal, and an explicit
        false is clamped rather than honoured: it would ship the session cookie
        unprotected on a deployment reachable beyond the LAN. The clamp is
        reported rather than silent — ``session_cookie_secure_clamped``, a
        boot warning, and ``GET /auth/security-posture``.
        """
        if self.trust_proxy_headers:
            return True
        if self.cookie_secure is not None:
            return self.cookie_secure
        return self.environment == "production"

    @property
    def session_cookie_secure_clamped(self) -> bool:
        """Whether the exposed posture overrode an explicit ``cookie_secure=false``."""
        return self.trust_proxy_headers and self.cookie_secure is False

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
    # Doc 07 §3: importance/heat/recency arms of rank_fusion_factor. Each is a
    # no-op at 0 (see app/services/rank_fusion.py RANK_ARMS); T2.30 activates
    # w_importance, T2.31 activates w_heat and w_recency once their signals
    # are wired.
    "w_importance": 0.0,
    "w_heat": 0.0,
    "w_recency": 0.0,
    # Doc 07 §6: the magnitude of the `applies_when` context boost. Zero is
    # the today-equivalent no-op — matching still labels every row and still
    # counts conflicts at zero, only the multiplier goes quiet. Tuned in
    # Phase 2 against the retrieval harness, never by intuition.
    "w_context_boost": 0.0,
    # Doc 07 §4: the graph arms. Each is the today-equivalent off, so with
    # them at these values retrieval is byte-identical to the vector+FTS
    # hybrid and the built entity graph stays unspent (invariant 23). The
    # `*_enabled` flags gate ranked-list producers; `w_ppr` / `w_dual` are
    # their RRF **list** weights, never per-row multipliers. T2.50 measures
    # all three before any of them moves. The dual-level channel itself is
    # T2.49's — its writer owns `relation_embeddings`, and its flag is
    # registered here so activation is one surface rather than two.
    "ppr_enabled": False,
    "w_ppr": 0.0,
    "dual_level_enabled": False,
    "w_dual": 0.0,
    "community_injection_enabled": False,
    # Doc 05 §2.2: how long an interactive `wait_process` capture may hold
    # Tier A driving its own buffer row's flush before degrading to the plain
    # 202 accept.
    "buffer_wait_timeout_seconds": 10,
}
