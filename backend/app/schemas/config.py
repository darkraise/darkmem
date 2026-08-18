from pydantic import BaseModel, Field

from app.config import ClassifierKind, LLMApiKind


class LLMPurposeConfigSchema(BaseModel):
    base_url: str
    model: str
    api_key: str | None = None
    dimensions: int | None = None
    reasoning: bool = False
    api_kind: LLMApiKind = "openai"
    params: dict = Field(default_factory=dict)
    # Only the classification purpose carries one; null everywhere else.
    # It was absent here while the column and `resolve_classifier` both
    # existed, so the settings UI had nothing to render and fell back to
    # "llm" whatever the database said.
    classifier_kind: ClassifierKind | None = None


class LLMPurposeConfigUpdate(BaseModel):
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    dimensions: int | None = None
    reasoning: bool | None = None
    api_kind: LLMApiKind | None = None
    params: dict | None = None
    # Declared so it can appear in `model_fields_set`. Without it the write
    # loop's `classifier_kind` entry was unreachable: the field was stripped
    # before the route saw it, so the POST returned 200 and wrote nothing.
    classifier_kind: ClassifierKind | None = None


class LLMProviderModelsResponse(BaseModel):
    """Models the configured Provider exposes, used by the UI to populate
    a model-selection dropdown after the user picks a Provider."""

    models: list[str] = Field(default_factory=list)
    fetched_via: str = ""  # e.g. "openai_compat:/v1/models" or "ollama_native:/api/tags"
    error: str | None = None


class LLMConfigResponse(BaseModel):
    embedding: LLMPurposeConfigSchema
    extraction: LLMPurposeConfigSchema
    classification: LLMPurposeConfigSchema
    reasoning: LLMPurposeConfigSchema
    summarization: LLMPurposeConfigSchema
    reranker: LLMPurposeConfigSchema
    # T2.104: `app.services.config.PURPOSES` has always resolved eight
    # purposes and both `/config/llm` routes have always built a payload
    # keyed on all eight (`{p: cfg_to_schema(c) for p, c in config.items()}`)
    # — this model declared only six, so pydantic's default extra="ignore"
    # silently dropped these two. `verification` is live: doc 04 §8's judge
    # service resolves and dispatches on it since T2.26. `synthesis` stays
    # seeded inert (first consumer T3.02).
    #
    # T2.106 decided the write side per purpose (see `LLMConfigUpdate`
    # below): `synthesis` is now writable, `verification` stays read-only.
    synthesis: LLMPurposeConfigSchema
    verification: LLMPurposeConfigSchema


class LLMConfigUpdateResponse(LLMConfigResponse):
    """Returned by POST /api/v1/config/llm. Extends LLMConfigResponse with
    computed obsolete counts for the new embedding model."""
    obsolete_after_change: dict[str, int] | None = None


class LLMConfigUpdate(BaseModel):
    """T2.106 — the write side is not symmetric with `LLMConfigResponse`'s
    eight-purpose read side, and that asymmetry is deliberate, not an
    oversight left for a later task:

    `synthesis` is seeded inert (no consumer until T3.02), so widening its
    write is cheap: a mis-set connection fails the day someone finally
    dispatches on it, not before, and nothing today reads this row.

    `verification` stays unreachable from this route. `VerificationJudge`
    (`app/services/`, T2.26) is live and dispatches on this
    purpose, and its qualification record is G-D's gate
    evidence (doc 17 §6) — a precision/recall measurement pinned to one
    resolved model identity (`judge_identity`: model, base_url, api_kind,
    dimensions, reasoning, params). Repointing that identity through a
    settings form is a real capability with a real failure mode: the
    judge's gated door already re-derives the identity hash and refuses
    with `JudgeNotQualifiedError` the moment it no longer matches the
    recorded one (`qualification_state`, fail-closed, checked on every
    call) — so a repoint cannot silently keep serving stale verdicts —
    but building the *write-time* half of that story (warning the operator
    before the save, or explicitly invalidating the on-disk qualification
    record at the moment of a repoint) means touching the verification
    ladder's enforcement path, which this task's own scope excludes
    ("do not change what any purpose does, or touch the judge") and which
    is Opus/Fable-tier work by the runbook's escalation rule, not a wire
    contract fix. Until that follow-on task exists, read-only here is the
    complete and correct answer, and the settings UI says so explicitly
    rather than rendering an editable-looking field that silently drops
    its write (`TIER_C_LLM_PURPOSES` / `TierCPurposeCard`,
    `frontend/src/features/settings`).
    """

    embedding: LLMPurposeConfigUpdate | None = None
    extraction: LLMPurposeConfigUpdate | None = None
    classification: LLMPurposeConfigUpdate | None = None
    reasoning: LLMPurposeConfigUpdate | None = None
    summarization: LLMPurposeConfigUpdate | None = None
    reranker: LLMPurposeConfigUpdate | None = None
    synthesis: LLMPurposeConfigUpdate | None = None


class StatsResponse(BaseModel):
    memories: int
    tags: int
    entities: int | None = None
    relationships: int | None = None
    sources: list[str] = []
