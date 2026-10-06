import logging
import re
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.api.deps import get_analytics_service, refuse_when_read_only
from app.utils.background import spawn
from app.config import FEATURE_FLAGS_DEFAULTS
from app.database import get_session
from app.models.config import Config
from app.models.llm_config import LLMPurposeConfigRow
from app.models.llm_provider import LLMProviderRow
from app.schemas.config import (
    LLMConfigResponse,
    LLMConfigUpdate,
    LLMConfigUpdateResponse,
)
from app.services.config import (
    PURPOSES,
    cfg_to_schema,
)
from app.services import research_rerun
from app.services.backup_config import (
    BACKUP_DESTINATIONS_KEY,
    DestinationConfig,
    DestinationInvalid,
    load_destinations as load_backup_destinations,
    mask_destination as _mask_destination,
    save_destinations as save_backup_destinations,
)
from app.services.analytics import AnalyticsService
from app.services.research_config import (
    MAX_CONTENT_CHARS_CEILING,
    MAX_FINDINGS_CEILING,
    load_budget as load_research_budget,
    write_auto_research_config,
)
from app.services.config import get_llm_config as fetch_llm_config
from app.services.llm_provider_guard import (
    assert_not_verification_provider,
    verification_provider,
)
from app.services.feature_flags import (
    FEATURE_FLAGS_KEY,
    MEASURABLE_FLAGS,
    get_feature_flags_dict,
    get_measured_flags,
)
from app.services.rank_fusion import GRAPH_CHANNELS, RANK_ARMS
# The verification ladder's thresholds, imported from the config module
# rather than from `verification_ladder` itself. Invariant 15's tree-wide scan
# matches that module's name on any line, and allowlisting a settings route
# past it would also buy the route the ability to reach the decision; see
# `ladder_config`'s docstring.
from app.services.ladder_config import (
    LADDER_FLOORS,
    LADDER_CONFIG_KEY,
    MEASUREMENT_TASK,
    resolve_ladder,
)
from app.services.repo_allowlist import (
    REPO_ALLOWLIST_KEY,
    load_allowlist,
    validate_pattern,
)

# Above every shipped default with headroom, so an operator can copy a
# default, edit it and save it - the extraction prompt alone is ~35k, and
# a cap below it made the editing feature unusable for the one prompt most
# worth tuning. Still bounded: the guard is against storing blobs that
# would blow the system-prompt budget on a small-context model.
PROMPT_OVERRIDE_MAX_CHARS = 60_000


router = APIRouter(prefix="/api/v1/config", tags=["config"])

logger = logging.getLogger(__name__)


def _swap_pipeline_llm(pipeline, new_llm) -> None:
    """Replace every LLM reference the pipeline holds.

    The ``ExtractionService`` / ``ClassificationService`` instances pin
    their own copy via ``self.llm = llm`` at construction time, so a bare
    ``pipeline.llm = new_llm`` would leave the call sites firing against
    the stale orchestrator (e.g. still OpenAI after the user pointed
    extraction at Ollama).
    """
    pipeline.llm = new_llm
    extraction_svc = getattr(pipeline, "extraction", None)
    if extraction_svc is not None:
        extraction_svc.llm = new_llm
    classification_svc = getattr(pipeline, "classification", None)
    if classification_svc is not None:
        classification_svc.llm = new_llm
    # The pipeline caches its per-batch classifier resolution (LLM vs in-process
    # ML, keyed on the classification purpose's classifier_kind) for a short
    # TTL. A config save can flip that field, so drop the cache here — the same
    # place the LLM references are swapped — to honor the per-batch contract
    # instead of serving the stale classifier until the TTL lapses.
    if hasattr(pipeline, "_classifier_cache"):
        pipeline._classifier_cache = None


async def _close_orchestrator_safely(old_llm) -> None:
    """Close the previous orchestrator's httpx client without raising.

    The orchestrator drains acquisition leases before closing its pool.
    Swallows close-time exceptions to a warning — the new
    orchestrator is already live so a failed close is just a leaked
    socket, not a user-visible error.
    """
    try:
        await old_llm.close()
    except Exception:
        logger.warning("Failed to close replaced LLM orchestrator", exc_info=True)


def _replace_orchestrator(request: Request, new_llm) -> None:
    """Atomically install ``new_llm`` as the active orchestrator.

    Updates ``app.state.llm``, swaps every reference inside the
    pipeline, and schedules the previous orchestrator's client to be
    closed as a background task so its keep-alive connections don't
    leak. Without this teardown, every Save on the LLM Providers page
    leaked an ``httpx.AsyncClient``; under load that produced sporadic
    Bad Gateway responses on the *first* save (stale pool) followed by
    a clean second save (fresh pool warmed up).
    """
    old_llm = getattr(request.app.state, "llm", None)
    request.app.state.llm = new_llm
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is not None:
        _swap_pipeline_llm(pipeline, new_llm)
    if old_llm is not None and old_llm is not new_llm:
        spawn(_close_orchestrator_safely(old_llm), name="close-orchestrator")


async def apply_llm_config_change(
    request: Request, session: AsyncSession
) -> dict[str, int] | None:
    """Re-resolve config, install a fresh orchestrator, and count re-embed work.

    The caller must already hold ``app.state.llm_config_lock``. Both the
    purpose route and the provider routes change connection details, so both
    go through this; two copies would drift and one of them would keep
    calling the old endpoint until restart.
    """
    refuse_when_read_only()
    from app.database import async_session_factory
    from app.services.llm import LLMOrchestrator
    from app.services.usage_recorder import UsageRecorder

    updated_config = await fetch_llm_config(session)
    # Carry the recorder across the swap. Losing it here would turn metering
    # off on a settings save, and the symptom -- a cost graph that stops --
    # looks exactly like an absence of spend.
    new_llm = LLMOrchestrator(
        updated_config, recorder=UsageRecorder(async_session_factory),
    )
    _replace_orchestrator(request, new_llm)

    # Resolve the dimensions of the new embedder before updating the
    # fingerprint. Prefer the explicit user value; otherwise probe the
    # model; otherwise leave it unset and let the next embed call populate
    # the registry on demand.
    new_embedding_dims: int | None = updated_config["embedding"].dimensions
    if new_embedding_dims is None:
        try:
            probe, _ = await new_llm.embed("dimension probe")
            new_embedding_dims = len(probe)
        except Exception as exc:
            logger.warning("Could not probe new embedder dimensions: %s", exc)

    pipeline = getattr(request.app.state, "pipeline", None)

    obsolete_after_change = None
    if pipeline is not None and new_embedding_dims:
        from app.services.reembed import ReembedService
        reembed_svc = ReembedService(session)
        # Build the partition fingerprint with the canonical helper so the
        # ``model|dims`` format can never drift from what the embed methods
        # emit. ``new_embedding_dims`` is the probed/explicit dimension,
        # which may differ from the (possibly-unset) configured value.
        new_fp = LLMOrchestrator._fingerprint(
            updated_config["embedding"].model, new_embedding_dims
        )
        obsolete_after_change = await reembed_svc.count_missing(new_fp)

    return obsolete_after_change


@router.get("/llm", response_model=LLMConfigResponse)
async def get_llm_config(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    config = await fetch_llm_config(session)
    return LLMConfigResponse(**{p: cfg_to_schema(c) for p, c in config.items()})


# Known REST deviation: this is an idempotent full-replace of the writable
# purpose set, so for symmetry with its PUT siblings (llm-providers,
# feature-flags) it should be PUT /config/llm. Left as POST because changing it
# would break existing frontend clients. See docs/api-rest-conventions.md
# ("Known deviations").
@router.post("/llm", response_model=LLMConfigUpdateResponse, dependencies=[Depends(refuse_when_read_only)])
async def update_llm_config(
    body: LLMConfigUpdate,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    # Serialise concurrent config swaps so two admins saving at once can't
    # leave ``app.state.llm`` and ``app.state.pipeline`` wired to different
    # orchestrators.
    async with request.app.state.llm_config_lock:
        update_data = body.model_dump(exclude_unset=True)

        for purpose in PURPOSES:
            purpose_update = getattr(body, purpose, None)
            if purpose not in update_data or purpose_update is None:
                continue
            # Keep only the fields the client actually set, but preserve an
            # explicit ``null`` so a nullable field such as dimensions can be
            # CLEARED — an omitted field stays untouched, an explicit null
            # clears the column.
            incoming = {
                k: v
                for k, v in update_data[purpose].items()
                if k in purpose_update.model_fields_set
            }
            # The FK would refuse an unknown provider with an IntegrityError,
            # which reaches the caller as a 500 naming a constraint; a bad name
            # in a settings form is a client error, so say so.
            if "provider_name" in incoming:
                known = (await session.execute(
                    select(LLMProviderRow.name)
                    .where(LLMProviderRow.name == incoming["provider_name"])
                )).scalar_one_or_none()
                if known is None:
                    raise HTTPException(
                        status_code=422,
                        detail=f"unknown provider_name {incoming['provider_name']!r}",
                    )

            row = (await session.execute(
                select(LLMPurposeConfigRow).where(LLMPurposeConfigRow.purpose == purpose)
            )).scalar_one_or_none()
            if "provider_name" in incoming:
                # Read before the row below is created, so a brand-new purpose
                # cannot present the provider it is being pointed at as the one
                # it already used and slip past the refusal.
                assert_not_verification_provider(
                    incoming["provider_name"],
                    await verification_provider(session),
                    purpose,
                    row.provider_name if row is not None else None,
                )
            if row is None:
                if "provider_name" not in incoming:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"purpose {purpose!r} has no row yet; "
                            "provider_name is required"
                        ),
                    )
                row = LLMPurposeConfigRow(
                    purpose=purpose, model="",
                    provider_name=incoming["provider_name"],
                )
                session.add(row)

            for field in (
                "model", "provider_name", "dimensions", "reasoning",
                "params", "classifier_kind",
            ):
                if field in incoming:
                    setattr(row, field, incoming[field])
            row.updated_at = datetime.now(timezone.utc)

        await session.flush()

        obsolete_after_change = await apply_llm_config_change(request, session)

        # Re-read through ``fetch_llm_config`` for the response payload: a
        # purpose row carries no connection of its own, so the base URL, key
        # and api_kind the client sees only come from resolving the provider
        # join again.
        updated_config = await fetch_llm_config(session)

        # Commit before releasing the lock, not in ``get_session``'s teardown
        # after this handler returns: a flushed-but-uncommitted write is
        # invisible to the next lock holder under READ COMMITTED, so
        # releasing the lock first only narrows the race it exists to close
        # rather than closing it. The provider routes commit inside their
        # own lock blocks for the same reason.
        await session.commit()

    purpose_payload = {p: cfg_to_schema(c) for p, c in updated_config.items()}
    return LLMConfigUpdateResponse(
        **purpose_payload,
        obsolete_after_change=obsolete_after_change,
    )


class RankArmInfo(BaseModel):
    """One ``rank_fusion_factor`` arm, read straight from ``RANK_ARMS`` so the
    UI's "inactive, activated by T2.30" label can never drift from the
    backend's own activation-id bookkeeping (doc 07 §3, T1.31)."""

    name: str
    flag: str
    value: float
    # None means the arm is already live (e.g. confidence) — no activation
    # task gates it.
    activation: str | None = None


class ClassificationLabel(BaseModel):
    """One label the classifier may emit under the current mode + areas."""

    name: str
    description: str
    # The area that contributed it, or null when no area is responsible: the
    # `fact` fallback, and every label in simple mode. Served rather than
    # intersected client-side because the answer depends on the merge order —
    # two areas may define the same name and the later one wins.
    area: str | None = None


class GraphChannelInfo(BaseModel):
    """One doc 07 §4 graph channel, read straight from ``GRAPH_CHANNELS``.

    Same discipline as ``RankArmInfo``: the "activated by T2.50" label and the
    enabled/weight pairing come off the backend's own registry, so a settings
    surface cannot pair a flag with the wrong weight or outlive a renumbered
    task. ``weight_flag`` is null for a channel that injects context rather
    than a ranked list — the UI renders the absence, never a zero it invented.
    """

    name: str
    flag: str
    enabled: bool
    weight_flag: str | None = None
    weight: float | None = None
    activation: str | None = None


class FeatureFlagsResponse(BaseModel):
    hybrid_search_enabled: bool
    reranker_enabled: bool
    pipeline_concurrency: int
    classification_areas: list[str]
    classification_mode: str
    embedding_batch_size: int
    embedding_concurrency: int
    entity_cache_ttl_minutes: int
    relation_rescue: bool = True
    confidence_rank_gamma: float = 0.0
    # Doc 07 §3 rank_fusion_factor arms wired at zero by T1.31 — present in
    # FEATURE_FLAGS_DEFAULTS well before this response model carried them.
    w_importance: float = 0.0
    w_heat: float = 0.0
    w_recency: float = 0.0
    w_context_boost: float = 0.0
    # Doc 07 §4's graph arms, in FEATURE_FLAGS_DEFAULTS since T2.32 but absent
    # from this response model until the Flags tab wiring — which is why the UI
    # rendered them as "no config row exists yet". The row existed; the field
    # did not, and the two are not the same absence.
    ppr_enabled: bool = False
    w_ppr: float = 0.0
    dual_level_enabled: bool = False
    w_dual: float = 0.0
    community_injection_enabled: bool = False
    rank_arms: list[RankArmInfo] = Field(default_factory=list)
    graph_channels: list[GraphChannelInfo] = Field(default_factory=list)
    # The label space the classifier actually works in, resolved by
    # ``get_merged_llm_types`` itself rather than re-derived by the client. The
    # simple/expanded split and the always-present ``fact`` fallback are that
    # function's rules, and a UI copy of them would drift the first time either
    # moved.
    classification_labels: list[ClassificationLabel] = Field(default_factory=list)
    # Whether ``classification_areas`` has any effect right now. It does NOT in
    # simple mode: ``get_merged_llm_types`` returns ``SIMPLE_TYPES`` and never
    # looks at the enabled areas. A surface that renders 11 area checkboxes
    # without saying so is offering controls that do nothing.
    classification_areas_apply: bool = False
    # Which of these are subject to the gate-ledger's "flip only on a
    # measured win" rule, and which of those have actually cleared one.
    measurable_flags: list[str] = Field(default_factory=list)
    measured_flags: list[str] = Field(default_factory=list)
    # The range the PUT accepts for every numeric flag, read off
    # FeatureFlagsUpdate's own Field(ge=, le=) so the form shows and enforces
    # the bounds the server applies rather than a copy of them.
    numeric_bounds: dict[str, "FlagBound"] = Field(default_factory=dict)


class FlagBound(BaseModel):
    min: float
    max: float


class FeatureFlagsUpdate(BaseModel):
    hybrid_search_enabled: bool | None = None
    reranker_enabled: bool | None = None
    pipeline_concurrency: int | None = Field(default=None, ge=1, le=20)
    classification_areas: list[str] | None = None
    classification_mode: Literal["simple", "expanded"] | None = None
    embedding_batch_size: int | None = Field(default=None, ge=1, le=200)
    embedding_concurrency: int | None = Field(default=None, ge=1, le=10)
    entity_cache_ttl_minutes: int | None = Field(default=None, ge=1, le=1440)
    relation_rescue: bool | None = None
    confidence_rank_gamma: float | None = Field(default=None, ge=0, le=5)
    w_importance: float | None = Field(default=None, ge=0, le=5)
    w_heat: float | None = Field(default=None, ge=0, le=5)
    w_recency: float | None = Field(default=None, ge=0, le=5)
    w_context_boost: float | None = Field(default=None, ge=0, le=5)
    ppr_enabled: bool | None = None
    # `w_ppr` / `w_dual` are RRF *list* weights, not per-row multipliers, but
    # they share the arms' 0..5 range: 0 is the today-equivalent no-op and the
    # ceiling exists so a typo cannot drown every other list in the fusion.
    w_ppr: float | None = Field(default=None, ge=0, le=5)
    dual_level_enabled: bool | None = None
    w_dual: float | None = Field(default=None, ge=0, le=5)
    community_injection_enabled: bool | None = None


def _numeric_flag_bounds() -> dict[str, FlagBound]:
    bounds: dict[str, FlagBound] = {}
    for name, field in FeatureFlagsUpdate.model_fields.items():
        lower = next((m.ge for m in field.metadata if hasattr(m, "ge")), None)
        upper = next((m.le for m in field.metadata if hasattr(m, "le")), None)
        if lower is not None and upper is not None:
            bounds[name] = FlagBound(min=lower, max=upper)
    return bounds


FeatureFlagsResponse.model_rebuild()


async def _lock_config_row(session: AsyncSession, key: str) -> None:
    """Serialise the read-modify-write on one ``config`` row.

    Both PUTs below read a JSON blob, patch it in Python and write the whole
    blob back. Two concurrent requests each read before the other commits, so
    the second write drops the first's change entirely -- measured on the Flags
    tab, where saving two controls inside one round-trip left one of them
    silently un-saved and the row holding only the other. The operator sees a
    control they set sitting at its old value with no error anywhere.

    A transaction-scoped advisory lock is enough and is the cheapest thing that
    is actually correct: it serialises writers on this key, needs no schema
    change, and releases on commit or rollback. ``SELECT ... FOR UPDATE`` would
    not do -- it locks no row when the row does not exist yet, which is exactly
    the first-save case both of these doors have.
    """
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key}
    )


def _flags_response(
    flags: dict, measured: list[str]
) -> FeatureFlagsResponse:
    """Build the wire response from a resolved flags dict.

    One builder for both verbs. GET and PUT used to assemble this twice, and
    the second copy is where a newly added field goes missing on exactly one of
    them — a PUT that answers with a stale shape reads as a failed save.
    """
    from app.services.classification_areas import (
        AREAS,
        get_label_sources,
        get_merged_llm_types,
    )

    mode = str(flags.get("classification_mode", "simple"))
    areas = list(flags.get("classification_areas", []) or [])
    labels = get_merged_llm_types(areas, mode)
    label_areas = get_label_sources(areas, mode)

    rank_arms = [
        RankArmInfo(
            name=arm.name,
            flag=arm.flag,
            value=float(flags.get(arm.flag, 0.0) or 0.0),
            activation=arm.activation,
        )
        for arm in RANK_ARMS
    ]
    graph_channels = [
        GraphChannelInfo(
            name=channel.name,
            flag=channel.flag,
            enabled=bool(flags.get(channel.flag, False)),
            weight_flag=channel.weight_flag,
            weight=(
                None
                if channel.weight_flag is None
                else float(flags.get(channel.weight_flag, 0.0) or 0.0)
            ),
            activation=channel.activation,
        )
        for channel in GRAPH_CHANNELS
    ]
    return FeatureFlagsResponse(
        **flags,
        rank_arms=rank_arms,
        graph_channels=graph_channels,
        classification_labels=[
            ClassificationLabel(
                name=name, description=desc, area=label_areas.get(name)
            )
            for name, desc in sorted(labels.items())
        ],
        # Derived from the one rule that decides it, not restated: ask the
        # resolver whether the areas changed anything.
        classification_areas_apply=(
            get_merged_llm_types([], mode) != get_merged_llm_types(
                list(AREAS), mode
            )
        ),
        measurable_flags=list(MEASURABLE_FLAGS),
        measured_flags=measured,
        numeric_bounds=_numeric_flag_bounds(),
    )


@router.get("/feature-flags", response_model=FeatureFlagsResponse)
async def get_feature_flags(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    flags = await get_feature_flags_dict(session)
    measured = await get_measured_flags(session)
    return _flags_response(flags, measured)


@router.put("/feature-flags", response_model=FeatureFlagsResponse)
async def update_feature_flags(
    body: FeatureFlagsUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    await _lock_config_row(session, FEATURE_FLAGS_KEY)
    current = await get_feature_flags_dict(session)
    updates = body.model_dump(exclude_unset=True)

    if "classification_areas" in updates:
        from app.services.classification_areas import AREAS
        invalid = [a for a in updates["classification_areas"] if a not in AREAS]
        if invalid:
            raise HTTPException(status_code=422, detail=f"Unknown classification areas: {invalid}")
        # `general` is the always-on fallback — enforce it server-side so
        # classification can never be left without at least the base area.
        if "general" not in updates["classification_areas"]:
            updates["classification_areas"] = ["general", *updates["classification_areas"]]

    current.update(updates)

    # Drop any keys that aren't part of the current schema so deprecated flags
    # don't linger in the DB row forever.
    stored = {k: current[k] for k in FEATURE_FLAGS_DEFAULTS if k in current}

    result = await session.execute(select(Config).where(Config.key == FEATURE_FLAGS_KEY))
    config = result.scalar_one_or_none()
    if config:
        config.value = stored
    else:
        session.add(Config(key=FEATURE_FLAGS_KEY, value=stored))
    await session.flush()

    measured = await get_measured_flags(session)
    # Commit before answering, rather than leaving it to the session
    # dependency's teardown. The teardown runs after the response is on its
    # way, so a client that re-reads the moment it sees the 200 can open its
    # transaction before this one commits and get the pre-write snapshot back.
    # Measured on the Flags tab: every save landed in the database, and the
    # invalidation refetch that followed painted the OLD value over it -- the
    # classification_mode control read as completely dead while writing
    # correctly every time.
    await session.commit()
    return _flags_response(stored, measured)


# ── Verification ladder thresholds (doc 08 §4.1, T2.03) ───────────────
#
# The promotion gate's three numbers had a `config` row, floors, a clamp and a
# measurement licence long before they had a door: the only way to tighten one
# was writing `verification_ladder` directly in Postgres. This is that door.
#
# It answers with the *resolved* report, never an echo of the request, for the
# reason `AutoResearchResponse` below gives and one more specific to this row:
# a below-floor value is clamped rather than refused, and a clamp that speaks
# only through `logging` renders exactly like a save that worked. An operator
# who types 1 and is shown 1 has been told the ladder runs at 1. It does not.


class LadderParamResponse(BaseModel):
    """One threshold, with the distance between what was asked and what runs."""

    name: str
    # What the config row holds. Null when nothing is committed, and also when
    # the row holds a value of the wrong type — there is no integer to report.
    committed: int | None
    # What the decision actually uses. This is the number that matters.
    effective: int
    floor: int
    # Whether `ladder_measurements` names this parameter, which is the only
    # thing that lets `effective` sit below `floor`.
    measured: bool
    state: Literal["default", "honoured", "clamped"]
    # Operator-facing reason, present only when the state is "clamped".
    note: str | None = None


class VerificationLadderResponse(BaseModel):
    params: list[LadderParamResponse]
    measured: list[str]
    # Whether a `verification_ladder` config row exists at all. "No row" and
    # "a row that happens to hold the defaults" are different states, and only
    # one of them means an operator has been here.
    row_present: bool
    # The task id whose recorded measurement is the only thing that may loosen
    # a floor — served rather than hardcoded in the UI, so a renumbered task
    # cannot leave the settings form naming a gate that no longer exists.
    measurement_task: str = MEASUREMENT_TASK


class VerificationLadderUpdate(BaseModel):
    """A partial update. Every field omitted is a field left alone.

    Deliberately *not* bounded with `ge=` at the schema. The floors are not a
    validation range: a value below one is legal the moment a recorded
    measurement names that parameter, and refusing it here would put a second,
    dumber copy of that rule in front of the real one. The resolver clamps and
    the response reports — one authority, and the operator sees its output.
    """

    n_default: int | None = None
    n_diverse: int | None = None
    time_gap_days: int | None = None


def _ladder_response(report) -> VerificationLadderResponse:
    return VerificationLadderResponse(
        params=[
            LadderParamResponse(
                name=param.name,
                committed=param.committed,
                effective=param.effective,
                floor=param.floor,
                measured=param.measured,
                state=param.state,
                note=param.note,
            )
            for param in report.params
        ],
        measured=list(report.measured),
        row_present=report.row_present,
    )


@router.get("/verification-ladder", response_model=VerificationLadderResponse)
async def get_verification_ladder(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    return _ladder_response(await resolve_ladder(session))


@router.put("/verification-ladder", response_model=VerificationLadderResponse)
async def update_verification_ladder(
    body: VerificationLadderUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Write the committed thresholds, then answer with what they resolve to.

    An integer is the only shape this door writes, so the resolver's
    wrong-type branch stays reachable only from a hand-edited row. A value that
    clamps is still written: the row is what an operator *asked for*, and
    keeping it means a later `ladder_measurements` entry licenses the value
    they already chose rather than requiring them to type it again.
    """
    await _lock_config_row(session, LADDER_CONFIG_KEY)
    result = await session.execute(select(Config).where(Config.key == LADDER_CONFIG_KEY))
    row = result.scalar_one_or_none()
    current = dict(row.value) if row and isinstance(row.value, dict) else {}

    updates = body.model_dump(exclude_unset=True)
    for name, value in updates.items():
        if value is None:
            # An explicit null clears the commitment and returns the parameter
            # to its shipped floor — the only way back out of an override.
            current.pop(name, None)
        else:
            current[name] = value

    # Drop anything that is not a known threshold, so a key the resolver would
    # only warn about cannot accumulate in the row forever.
    stored = {k: v for k, v in current.items() if k in LADDER_FLOORS}

    if row:
        row.value = stored
    else:
        session.add(Config(key=LADDER_CONFIG_KEY, value=stored))
    await session.flush()
    # Same reason as the feature-flags door above: a 200 must mean committed,
    # or the client's own refetch can read around it.
    await session.commit()

    return _ladder_response(await resolve_ladder(session))


# ── Repo auto-provision allowlist (doc 18 §6, T1.15) ──────────────────
#
# T1.15 shipped the SSRF gate itself (evaluate_hint / load_allowlist) with no
# editing surface: the only way to opt in was writing the `repo_allowlist`
# config row directly in Postgres. This is that surface. Validation MUST go
# through `validate_pattern` — the same parse `evaluate_hint` runs a stored
# pattern through at clone time — never a second, hand-rolled check that
# could silently define "allowed" differently from the gate it feeds.


class RepoAllowlistResponse(BaseModel):
    patterns: list[str] = Field(default_factory=list)


class RepoAllowlistUpdate(BaseModel):
    patterns: list[str] = Field(default_factory=list)


class AutoResearchResponse(BaseModel):
    """The budget as the *reader* resolves it, never an echo of the request.

    A response built from what was sent could disagree with what a run will
    actually do — the clamps and the fail-closed parse live on the read path,
    so the operator must see their output rather than their own input.
    """

    enabled: bool
    max_findings_per_run: int
    max_content_chars: int
    # The default is False and stays False: this surface makes arming an
    # explicit operator act, which is a different thing from arming it.
    default_enabled: bool = False
    # The largest value each budget accepts (the smallest is 1), so the
    # settings form can show and enforce the range the writer enforces.
    max_findings_per_run_ceiling: int = MAX_FINDINGS_CEILING
    max_content_chars_ceiling: int = MAX_CONTENT_CHARS_CEILING


class AutoResearchUpdate(BaseModel):
    # All optional: a partial update must not silently reset the fields it
    # omits. `enabled` is typed `bool | None` rather than `bool` so a string
    # reaches the writer's strict check with its shape intact instead of being
    # coerced by pydantic on the way in.
    enabled: bool | None = None
    max_findings_per_run: int | None = None
    max_content_chars: int | None = None


@router.get("/auto-research", response_model=AutoResearchResponse)
async def get_auto_research(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """The live budget. A never-configured install reads disarmed, which is an
    honest state rather than an error — the loop refuses every run until an
    operator arms it."""
    budget = await load_research_budget(session)
    return AutoResearchResponse(
        enabled=budget.enabled,
        max_findings_per_run=budget.max_findings_per_run,
        max_content_chars=budget.max_content_chars,
    )


@router.put("/auto-research", response_model=AutoResearchResponse)
async def update_auto_research(
    body: AutoResearchUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        budget = await write_auto_research_config(session, patch)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return AutoResearchResponse(
        enabled=budget.enabled,
        max_findings_per_run=budget.max_findings_per_run,
        max_content_chars=budget.max_content_chars,
    )


class BackupDestinationsResponse(BaseModel):
    """The destination list as stored, with every secret replaced by the mask.

    The response is built from what `save_destinations` actually persisted
    rather than from the request body, so a mask the writer resolved against
    the stored row reads back as a mask instead of echoing the secret it
    resolved to.
    """

    destinations: list[DestinationConfig]


class BackupDestinationsUpdate(BaseModel):
    destinations: list[DestinationConfig] = Field(default_factory=list)


@router.get("/backup-destinations", response_model=BackupDestinationsResponse)
async def get_backup_destinations(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Where this instance ships its own encrypted snapshots. A never-configured
    install reads empty, which is honest rather than an error -- the job simply
    has nowhere to ship and says so in its run summary."""
    return BackupDestinationsResponse(
        destinations=await load_backup_destinations(session, masked=True)
    )


@router.put("/backup-destinations", response_model=BackupDestinationsResponse)
async def update_backup_destinations(
    body: BackupDestinationsUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    await _lock_config_row(session, BACKUP_DESTINATIONS_KEY)
    try:
        saved = await save_backup_destinations(session, body.model_dump())
    except DestinationInvalid as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return BackupDestinationsResponse(destinations=[_mask_destination(d) for d in saved])


class ResearchRunSummaryResponse(BaseModel):
    """One filed run. `occurred_at` rides back to the re-run deliberately —
    `events` is partitioned by month under a composite `(id, created_at)` key,
    so the caller returning the bound it was given is what prunes the lookup to
    one partition instead of scanning every month (T2.13's undo discipline)."""

    event_id: int
    occurred_at: datetime
    run_id: str | None
    subject: str
    project: str
    filed: int
    live: int


class ResearchRunListResponse(BaseModel):
    items: list[ResearchRunSummaryResponse]
    total: int


class ResearchRerunRequest(BaseModel):
    occurred_at: datetime


class ResearchRerunResponse(BaseModel):
    """What the re-derivation touched, including what it could not.

    `filed` versus `reprocessed` is reported rather than reconciled: a run
    whose memories were deleted re-derives fewer than it filed, and the
    operator sees that instead of a clean line."""

    event_id: int
    subject: str
    project: str
    filed: int
    reprocessed: int
    missing: int
    #: Of the missing, those still in the capture buffer rather than deleted.
    pending: int
    errors: int


@router.get("/auto-research/runs", response_model=ResearchRunListResponse)
async def list_auto_research_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Research runs already filed. Read-only, and available whether or not the
    loop is armed — what a past run did is history, not a switch."""
    runs, total = await research_rerun.list_research_runs(
        session, limit=limit, offset=offset
    )
    return ResearchRunListResponse(
        items=[
            ResearchRunSummaryResponse(
                event_id=run.event_id,
                occurred_at=run.occurred_at,
                run_id=run.run_id,
                subject=run.subject,
                project=run.project,
                filed=run.filed,
                live=run.live,
            )
            for run in runs
        ],
        total=total,
    )


@router.post("/auto-research/runs/{event_id}/rerun", response_model=ResearchRerunResponse)
async def rerun_auto_research_run(
    event_id: int,
    body: ResearchRerunRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
    analytics: AnalyticsService = Depends(get_analytics_service),
):
    """Re-derive the run's surviving evidence.

    **This files nothing and gathers nothing**, which is what lets it sit on
    REST at all: doc 09 §6 keeps `research_run` on MCP because the caller must
    be the gatherer, and a re-derivation has no gatherer to be. Nothing here
    reaches `app.services.auto_research`, so invariant 15's scan needs no
    second exemption and is given none.
    """
    try:
        outcome = await research_rerun.rerun_research_run(
            session,
            event_id=event_id,
            occurred_at=body.occurred_at,
            reprocess=analytics.reprocess_selected,
        )
    except research_rerun.RerunUnavailable as exc:
        # 503, matching the sibling `POST /analytics/reprocess`. A pipeline-less
        # boot must not answer 200 with a zero tally, which reads to an
        # operator as "there was nothing to do".
        raise HTTPException(status_code=503, detail=str(exc))
    except research_rerun.RerunRefused as exc:
        # 409 when the run exists and its evidence is gone — that is a state,
        # not a missing resource, and a 404 would tell the operator the run
        # they are looking at does not exist.
        status = 409 if exc.reason in ("no_evidence", "not_yet_materialised") else 404
        raise HTTPException(status_code=status, detail=str(exc))
    return ResearchRerunResponse(
        event_id=outcome.event_id,
        subject=outcome.subject,
        project=outcome.project,
        filed=outcome.filed,
        reprocessed=outcome.reprocessed,
        missing=outcome.missing,
        pending=outcome.pending,
        errors=outcome.errors,
    )


@router.get("/repo-allowlist", response_model=RepoAllowlistResponse)
async def get_repo_allowlist(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    return RepoAllowlistResponse(patterns=await load_allowlist(session))


@router.put("/repo-allowlist", response_model=RepoAllowlistResponse)
async def update_repo_allowlist(
    body: RepoAllowlistUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    cleaned: list[str] = []
    invalid: list[str] = []
    for pattern in body.patterns:
        canonical = validate_pattern(pattern)
        if canonical is None:
            invalid.append(pattern)
        elif canonical not in cleaned:
            cleaned.append(canonical)
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid allowlist patterns (host[/path-prefix] or *.host only): {invalid}",
        )

    result = await session.execute(
        select(Config).where(Config.key == REPO_ALLOWLIST_KEY)
    )
    config = result.scalar_one_or_none()
    stored = {"patterns": cleaned}
    if config:
        config.value = stored
    else:
        session.add(Config(key=REPO_ALLOWLIST_KEY, value=stored))
    await session.flush()

    return RepoAllowlistResponse(patterns=cleaned)


@router.get("/classification-areas")
async def list_classification_areas(
    _user=Depends(require_auth),
):
    from app.services.classification_areas import AREAS
    return [
        {
            "key": area.key,
            "display_name": area.display_name,
            "types": list(area.llm_types.keys()),
            "type_descriptions": area.llm_types,
        }
        for area in AREAS.values()
    ]


# ── System prompts (UI-editable) ─────────────────────────────────────


class SystemPromptsResponse(BaseModel):
    defaults: dict[str, str]
    overrides: dict[str, str]
    effective: dict[str, str]


class SystemPromptsUpdate(BaseModel):
    """Partial update. Keys map to the prompt body.

    - A non-empty string installs / replaces the override for that purpose.
    - An empty string clears the override (falls back to the in-code default).
    - Omitted keys are left unchanged.
    """

    overrides: dict[str, str] = Field(default_factory=dict)


class NotificationsUpdate(BaseModel):
    telegram: dict | None = None
    notify_on: dict | None = None


@router.get("/notifications")
async def get_notifications(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Current notification settings, with the bot token masked.

    The token never travels back to the client; a client that echoes the mask
    on save is understood to mean "leave it alone".
    """
    from app.services.notifications import get_settings, masked

    return masked(await get_settings(session))


@router.put("/notifications")
async def update_notifications(
    body: NotificationsUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services.notifications import masked, save_settings

    saved = await save_settings(session, body.model_dump(exclude_none=True))
    await session.commit()
    return masked(saved)


@router.post("/notifications/test", dependencies=[Depends(refuse_when_read_only)])
async def test_notification(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Send one message with the stored settings and report what happened.

    A configuration screen that cannot prove the credential works is one that
    discovers it is wrong during the incident it was meant to report.
    """
    from app.services.notifications import get_settings, send_telegram

    settings = await get_settings(session)
    sent, error = await send_telegram(
        settings, "darkmem — test notification. If you can read this, alerts work."
    )
    return {"sent": sent, "error": error}


@router.get("/system-prompts", response_model=SystemPromptsResponse)
async def get_system_prompts(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services import prompt as _prompt_mod  # noqa: PLC0415

    await _prompt_mod.refresh_from_db(session)
    defaults = dict(_prompt_mod.PROMPTS)
    overrides = _prompt_mod.get_overrides()
    effective = {k: overrides.get(k, defaults.get(k, "")) for k in defaults}
    return SystemPromptsResponse(defaults=defaults, overrides=overrides, effective=effective)


@router.put("/system-prompts", response_model=SystemPromptsResponse)
async def update_system_prompts(
    body: SystemPromptsUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services import prompt as _prompt_mod  # noqa: PLC0415

    row = (
        await session.execute(select(Config).where(Config.key == _prompt_mod.SYSTEM_PROMPTS_KEY))
    ).scalar_one_or_none()
    stored: dict[str, str] = {}
    if row and isinstance(row.value, dict):
        for k, v in row.value.items():
            if isinstance(k, str) and isinstance(v, str):
                stored[k] = v

    for key, value in body.overrides.items():
        if not isinstance(key, str) or key not in _prompt_mod.PROMPTS:
            raise HTTPException(status_code=422, detail=f"Unknown prompt purpose: {key!r}")
        if not isinstance(value, str):
            raise HTTPException(status_code=422, detail=f"Prompt for {key!r} must be a string")
        if value == "":
            stored.pop(key, None)
        else:
            if len(value) > PROMPT_OVERRIDE_MAX_CHARS:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Prompt for {key!r} exceeds "
                        f"{PROMPT_OVERRIDE_MAX_CHARS:,} characters"
                    ),
                )
            stored[key] = value

    if row:
        row.value = stored
    else:
        session.add(Config(key=_prompt_mod.SYSTEM_PROMPTS_KEY, value=stored))
    await session.flush()

    await _prompt_mod.refresh_from_db(session)

    # The MCP server captures its served instructions once; re-push so an
    # agent_instructions edit takes effect without a restart.
    from app.api.mcp.server import refresh_mcp_instructions  # noqa: PLC0415
    refresh_mcp_instructions()

    defaults = dict(_prompt_mod.PROMPTS)
    overrides = _prompt_mod.get_overrides()
    effective = {k: overrides.get(k, defaults.get(k, "")) for k in defaults}
    return SystemPromptsResponse(defaults=defaults, overrides=overrides, effective=effective)


class ReposPathResponse(BaseModel):
    path: str | None


class ReposPathUpdate(BaseModel):
    path: str


@router.get("/repos-path", response_model=ReposPathResponse)
async def get_repos_path(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    row = (await session.execute(
        select(Config).where(Config.key == "repos_default_local_path")
    )).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return ReposPathResponse(path=None)
    return ReposPathResponse(path=row.value.get("path"))


@router.put("/repos-path", response_model=ReposPathResponse)
async def update_repos_path(
    body: ReposPathUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    from app.services.repo_manager import validate_local_path

    try:
        resolved = validate_local_path(body.path, must_not_be_repo=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    row = (await session.execute(
        select(Config).where(Config.key == "repos_default_local_path")
    )).scalar_one_or_none()
    if row is None:
        session.add(Config(key="repos_default_local_path", value={"path": str(resolved)}))
    else:
        row.value = {"path": str(resolved)}
    await session.flush()
    return ReposPathResponse(path=str(resolved))


# ── Theme settings (frontend theme-switcher persistence) ─────────────


THEME_SETTINGS_KEY = "theme_settings"

# Axis values are darkraise-ui design-token slugs ("indigo", "cozy",
# "blobs"). The pattern constrains shape rather than enumerating values so a
# library upgrade that adds a color doesn't start rejecting saves.
_AXIS_VALUE = r"^[a-z][a-z0-9-]{0,31}$"


class ThemeSettingsPayload(BaseModel):
    """Mirrors darkraise-ui's ThemeSettings; stored and served verbatim in
    its camelCase wire form so the frontend round-trips without mapping.

    Every axis the theme provider can emit needs a field here: it sends the
    whole settings object on each change and `extra="forbid"` turns one
    missing axis into a 422 on every save, which localStorage then masks
    into a silent loss of cross-browser persistence. That is what the v6
    upgrade did with `fontSize`; keep this in step with the axis list in
    frontend/src/theme.config.ts.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    accent_color: str = Field(alias="accentColor", pattern=_AXIS_VALUE)
    surface_color: str = Field(alias="surfaceColor", pattern=_AXIS_VALUE)
    preset: str = Field(pattern=_AXIS_VALUE)
    background_style: str = Field(alias="backgroundStyle", pattern=_AXIS_VALUE)
    background_intensity: str | None = Field(
        default=None, alias="backgroundIntensity", pattern=_AXIS_VALUE
    )
    gradient_pattern: str | None = Field(
        default=None, alias="gradientPattern", pattern=_AXIS_VALUE
    )
    mode: str = Field(pattern=_AXIS_VALUE)
    density: str | None = Field(default=None, pattern=_AXIS_VALUE)
    elevation: str | None = Field(default=None, pattern=_AXIS_VALUE)
    button_elevation: str | None = Field(
        default=None, alias="buttonElevation", pattern=_AXIS_VALUE
    )
    radius: str | None = Field(default=None, pattern=_AXIS_VALUE)
    font_size: str | None = Field(
        default=None, alias="fontSize", pattern=_AXIS_VALUE
    )
    surface_intensity: str | None = Field(
        default=None, alias="surfaceIntensity", pattern=_AXIS_VALUE
    )
    accent_intensity: str | None = Field(
        default=None, alias="accentIntensity", pattern=_AXIS_VALUE
    )
    control_depth: str | None = Field(
        default=None, alias="controlDepth", pattern=_AXIS_VALUE
    )
    outer_glow: str | None = Field(
        default=None, alias="outerGlow", pattern=_AXIS_VALUE
    )
    inner_glow: str | None = Field(
        default=None, alias="innerGlow", pattern=_AXIS_VALUE
    )
    preset_axis_values: dict[str, dict[str, str]] | None = Field(
        default=None, alias="presetAxisValues"
    )

    @field_validator("preset_axis_values")
    @classmethod
    def _validate_preset_axis_values(
        cls, value: dict[str, dict[str, str]] | None
    ) -> dict[str, dict[str, str]] | None:
        if value is None:
            return value
        if len(value) > 16:
            raise ValueError("too many presets")
        for preset_name, axes in value.items():
            if not re.fullmatch(_AXIS_VALUE, preset_name):
                raise ValueError(f"invalid preset name: {preset_name!r}")
            if len(axes) > 16:
                raise ValueError(f"too many axes for preset {preset_name!r}")
            for axis_name, axis_value in axes.items():
                if not re.fullmatch(_AXIS_VALUE, axis_name):
                    raise ValueError(f"invalid axis name: {axis_name!r}")
                if not re.fullmatch(_AXIS_VALUE, axis_value):
                    raise ValueError(f"invalid axis value: {axis_value!r}")
        return value


class ThemeSettingsResponse(BaseModel):
    settings: ThemeSettingsPayload | None = None


class ThemeSettingsUpdate(BaseModel):
    settings: ThemeSettingsPayload


@router.get("/theme", response_model=ThemeSettingsResponse)
async def get_theme_settings(
    session: AsyncSession = Depends(get_session),
):
    """Deliberately unauthenticated: the ThemeProvider loads once at app
    boot (above the router, possibly on the login screen), and the payload
    is pure UI cosmetics. Writes stay auth-gated below."""
    row = (await session.execute(
        select(Config).where(Config.key == THEME_SETTINGS_KEY)
    )).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return ThemeSettingsResponse(settings=None)
    try:
        settings = ThemeSettingsPayload.model_validate(row.value)
    except ValidationError:
        # A row written under an older schema shouldn't break boot; the
        # client falls back to its defaults and the next save heals it.
        return ThemeSettingsResponse(settings=None)
    return ThemeSettingsResponse(settings=settings)


@router.put("/theme", response_model=ThemeSettingsResponse)
async def update_theme_settings(
    body: ThemeSettingsUpdate,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    stored = body.settings.model_dump(by_alias=True, exclude_none=True)
    # Saves are debounce-fired by every browser session, so concurrent
    # first-ever writes are plausible; select-then-insert would 500 the loser.
    await session.execute(
        pg_insert(Config)
        .values(key=THEME_SETTINGS_KEY, value=stored)
        .on_conflict_do_update(
            index_elements=[Config.key], set_={"value": stored}
        )
    )
    return ThemeSettingsResponse(settings=body.settings)
