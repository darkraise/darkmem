import asyncio
import json
import logging
import random
import time
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar

import httpx

from app.config import LLMPurposeConfig
from app.utils.background import spawn as spawn_background
from app.services.llm_quirks import (
    assert_can_embed,
    assert_reasoning_effort,
    auth_headers,
    chat_url,
    embeddings_url,
    output_cap_keys,
    quirks_for,
)

logger = logging.getLogger(__name__)
_borrowed_llms: ContextVar[tuple] = ContextVar("borrowed_llms", default=())


def _retain_llm(llm):
    if not isinstance(llm, LLMOrchestrator):
        return lambda: None
    if llm._client.is_closed or (llm._retiring and llm not in _borrowed_llms.get()):
        raise RuntimeError("LLM orchestrator is retiring")
    llm._leases += 1
    llm._drained.clear()
    released = False

    def release():
        nonlocal released
        if released:
            return
        released = True
        llm._leases -= 1
        if not llm._leases:
            llm._drained.set()

    return release


def spawn_with_llm(llm, coroutine, *, spawn=asyncio.create_task, **kwargs):
    try:
        release = _retain_llm(llm)
    except BaseException:
        coroutine.close()
        raise
    started = False

    async def run():
        nonlocal started
        started = True
        token = _borrowed_llms.set((*_borrowed_llms.get(), llm))
        try:
            return await coroutine
        finally:
            _borrowed_llms.reset(token)

    wrapper = run()

    def finished(_task):
        if not started:
            coroutine.close()
        release()

    try:
        task = spawn(wrapper, **kwargs)
    except BaseException:
        wrapper.close()
        coroutine.close()
        release()
        raise
    task.add_done_callback(finished)
    return task


@contextmanager
def lease_llm(llm):
    if not isinstance(llm, LLMOrchestrator):
        yield llm
        return
    release = _retain_llm(llm)
    borrowed = _borrowed_llms.get()
    token = _borrowed_llms.set((*borrowed, llm))
    try:
        yield llm
    finally:
        _borrowed_llms.reset(token)
        release()

#: Indirection so tests can observe the backoff without serving it.
_sleep = asyncio.sleep

# Request-level retry. This sits above the transport `retries=` setting, which
# httpx applies to connection establishment only and therefore cannot see a
# response status or anything raised after the connection is up.
_RETRY_MAX_ATTEMPTS = 3
_RETRY_BASE_DELAY_SECONDS = 1.0
#: Also the ceiling applied to a vendor's own `Retry-After`, so a hostile or
#: mistaken header cannot park a flush worker past its claim visibility window.
_RETRY_MAX_DELAY_SECONDS = 20.0

#: Statuses where the same request may succeed later. 4xx is otherwise
#: permanent: retrying a malformed body or a bad key only triples the latency
#: before the identical failure.
_RETRYABLE_STATUS: frozenset[int] = frozenset({408, 429, 500, 502, 503, 504})

#: `ReadTimeout` is deliberately absent. The read budget is 300s and
#: `BUFFER_FLUSH_MAX_RUN_SECONDS` is also 300, so three attempts would outlive
#: the flush run holding the row and let the stale sweep reclaim it mid-flight.
#: Listing the sibling timeouts explicitly rather than catching
#: `httpx.TimeoutException` is what keeps that exclusion true.
_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.WriteError,
    httpx.RemoteProtocolError,
)


def _parse_retry_after(value: str | None) -> float | None:
    """Seconds from a `Retry-After` header, or None if it carries no number.

    Only the delta-seconds form is read. The HTTP-date form is legal but no
    vendor on the supported list emits it, and mis-parsing a date into a
    multi-hour sleep is a worse failure than ignoring the header.
    """
    if not value:
        return None
    try:
        seconds = float(value.strip())
    except (TypeError, ValueError):
        return None
    if seconds < 0:
        return None
    return min(seconds, _RETRY_MAX_DELAY_SECONDS)


def _backoff_delay(attempt: int) -> float:
    """Equal-jitter exponential backoff for `attempt` (1-based).

    Half the window is fixed and half is random: the fixed half guarantees the
    delay actually grows, and the random half stops `pipeline_concurrency`
    workers that hit one rate limit together from retrying in lockstep and
    reproducing it.
    """
    window = _RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
    window = min(window, _RETRY_MAX_DELAY_SECONDS)
    return window / 2 + random.uniform(0, window / 2)


def _output_cap(params: dict, api_kind: str | None = None) -> int | None:
    """Return the configured output-token cap, whichever key carries it."""
    for key in output_cap_keys(api_kind):
        value = params.get(key)
        if isinstance(value, int):
            return value
    return None



def _dig(payload: dict, dotted: str):
    """Descend a dotted path, returning None rather than raising on a miss."""
    node = payload
    for part in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def extract_usage(payload: dict | None, quirks) -> dict | None:
    """Normalise one vendor response into the four counts, or None.

    None means "this vendor told us nothing", which is **not** zero — the
    doctrine ``benchlib/twin.py`` sets, where a report prints
    ``tokens: not measured`` rather than a fabricated 0. A vendor that stops
    surfacing usage must not read as a free model.

    Handles both shapes: the OpenAI-compat ``usage`` envelope, and Ollama's
    native ``prompt_eval_count``/``eval_count``, which ride the ``done`` chunk
    on the streaming path. Where the cached count lives is a vendor difference,
    so it is read from the quirk row rather than from a comparison against a
    vendor name — ``tests/test_api_kind_dispatch.py`` fails the build on the
    latter.
    """
    if not payload:
        return None
    usage = payload.get("usage")
    if isinstance(usage, dict) and (
        usage.get("prompt_tokens") is not None
        or usage.get("completion_tokens") is not None
    ):
        cached = 0
        for field_path in quirks.cache_hit_fields:
            value = _dig(usage, field_path)
            if value:
                cached = int(value)
                break
        reasoning = _dig(usage, "completion_tokens_details.reasoning_tokens")
        return {
            "prompt_tokens": usage.get("prompt_tokens"),
            "cached_tokens": cached,
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": int(reasoning) if reasoning else None,
            "raw": usage,
        }
    if payload.get("prompt_eval_count") is not None or payload.get("eval_count") is not None:
        return {
            "prompt_tokens": payload.get("prompt_eval_count"),
            "cached_tokens": 0,
            "completion_tokens": payload.get("eval_count"),
            "reasoning_tokens": None,
            "raw": {
                k: payload.get(k)
                for k in ("prompt_eval_count", "eval_count")
                if payload.get(k) is not None
            },
        }
    return None


class LLMTruncationError(RuntimeError):
    """Raised when a completion stops at its output-token cap.

    The vendor reports ``finish_reason='length'`` (Ollama: ``done_reason``),
    meaning generation was cut off before the model finished. For JSON
    purposes like extraction the body is then unparseable, so callers that
    require complete output opt in via ``raise_on_truncation`` instead of
    silently consuming a half-written response and failing later with a
    misleading parse error.
    """


#: Purpose-param key opting a qwen-behind-compat deployment into the
#: ``/no_think`` chat-template directive. Not a wire field — it is stripped
#: from the request body and steers the prompt instead. Vendors that define no
#: such directive simply never set it.
NO_THINK_PARAM = "prompt_no_think"


class LLMOrchestrator:
    """Routes purpose-specific calls to the right wire protocol.

    Dispatch contract for ``api_kind`` — every chat / embed / tool method
    here asks ``app.services.llm_quirks`` what the configured vendor needs
    and never names a vendor itself. Kinds whose ``native_protocol`` is set
    take their own wire surface (Ollama's ``/api/chat``, ``/api/embed``);
    every other kind shares the OpenAI-compatible path
    (``/chat/completions``, ``/embeddings``) with its quirks patched from
    the same table. To plug in a native adapter for a vendor, give its row a
    native protocol and branch here on the capability, not on the name. The
    enum lives on ``LLMApiKind`` in ``app/config.py``.
    """

    # Conservative transport-level retries for idempotent connection/transient
    # failures. httpx only retries on connection errors and a closed pool here,
    # not on response status, so this never replays a request the server already
    # accepted — it just smooths over transient 429/5xx-adjacent network blips
    # and DNS/connect flakiness against cloud vendors. Timeouts are unchanged.
    _TRANSPORT_RETRIES = 2

    def __init__(self, config: dict[str, LLMPurposeConfig], recorder=None):
        self.config = config
        self._leases = 0
        self._retiring = False
        self._drained = asyncio.Event()
        self._drained.set()
        #: Optional ``UsageRecorder``. None in tests and in any construction
        #: that has no session to write with; metering is never load-bearing.
        self._recorder = recorder
        self._client = httpx.AsyncClient(
            # Split timeout instead of a single 300s scalar. connect/write/pool
            # fail fast so a black-hole endpoint or an exhausted connection pool
            # can't wedge a caller (and any job lock it holds) for five minutes;
            # only the read budget stays generous because a long completion or a
            # large embedding batch on a slow local model legitimately needs it.
            timeout=httpx.Timeout(connect=10.0, read=300.0, write=30.0, pool=10.0),
            # Make the connection cap explicit and bounded so a high
            # pipeline_concurrency can't fan out an unbounded number of
            # simultaneous requests at a rate-limited vendor.
            limits=httpx.Limits(max_connections=64, max_keepalive_connections=16),
            transport=httpx.AsyncHTTPTransport(retries=self._TRANSPORT_RETRIES),
        )


    async def _post_with_retry(
        self, url: str, *, headers: dict, body: dict, purpose: str,
    ) -> httpx.Response:
        """POST to a vendor, retrying the failures that can succeed later.

        Every vendor call in this class goes through here, so the retriable set
        is defined once rather than per protocol path. Replay is safe because
        callers forward a content-derived ``seed`` at temperature 0: a retried
        extraction returns the same JSON the first attempt would have.

        The final attempt's response is returned even when it is retriable, so
        the caller's own ``raise_for_status`` still produces the error message
        it always did. This never swallows a failure; it only re-sends.
        """
        for attempt in range(1, _RETRY_MAX_ATTEMPTS + 1):
            last = attempt == _RETRY_MAX_ATTEMPTS
            try:
                response = await self._client.post(url, headers=headers, json=body)
            except _RETRYABLE_EXCEPTIONS as e:
                if last:
                    raise
                delay = _backoff_delay(attempt)
                logger.warning(
                    "LLM %s call failed (%s: %s); retrying in %.1fs "
                    "(attempt %d/%d)",
                    purpose, type(e).__name__, e, delay, attempt,
                    _RETRY_MAX_ATTEMPTS,
                )
                await _sleep(delay)
                continue
            if response.status_code in _RETRYABLE_STATUS and not last:
                delay = _parse_retry_after(response.headers.get("retry-after"))
                if delay is None:
                    delay = _backoff_delay(attempt)
                logger.warning(
                    "LLM %s call returned %d; retrying in %.1fs (attempt %d/%d)",
                    purpose, response.status_code, delay, attempt,
                    _RETRY_MAX_ATTEMPTS,
                )
                await _sleep(delay)
                continue
            return response
        # Unreachable: the final iteration always returns or raises.
        raise AssertionError("retry loop exited without a response")

    @asynccontextmanager
    async def _meter(self, purpose: str, cfg, subject=None):
        """Time one vendor call and record what it cost, success or failure.

        Wraps the request/response cycle rather than living at the end of it:
        every error path here raises, so a recorder placed after the response
        would see only the calls that worked — and a failed call is exactly the
        waste this measurement exists to find.

        The caller sets ``box["payload"]`` to the parsed response body; leaving
        it None records the call as unmeasured, which is not the same as free.
        """
        started = time.perf_counter()
        box: dict = {"payload": None, "extra_raw": None}
        try:
            yield box
        except Exception as exc:
            await self._report(purpose, cfg, subject, None, started, False,
                               type(exc).__name__, box.get("extra_raw"))
            raise
        else:
            await self._report(purpose, cfg, subject, box["payload"], started,
                               True, None, box.get("extra_raw"))

    async def _report(self, purpose, cfg, subject, payload, started, ok,
                      error_kind, extra_raw):
        if self._recorder is None:
            return
        await self._recorder.record(
            purpose=purpose,
            model=cfg.model,
            provider=getattr(cfg, "provider_name", None),
            api_kind=cfg.api_kind,
            payload=payload,
            subject=subject,
            duration_ms=int((time.perf_counter() - started) * 1000),
            ok=ok,
            error_kind=error_kind,
            extra_raw=extra_raw,
        )

    @staticmethod
    def _fingerprint(model: str, dims: int) -> str:
        return f"{model}|{dims}"

    @staticmethod
    def _assert_can_embed(cfg) -> None:
        assert_can_embed(cfg.api_kind, cfg.model)

    @staticmethod
    def _check_dims(cfg, actual: int) -> None:
        """Fail loud when the real vector length contradicts configured dims.

        llm_fingerprint() names the partition from cfg.dimensions, but embeds
        emit ``model|len(vec)``. If the stored value is wrong the two disagree
        and reads route to a partition writes never populated, so reject the
        misconfiguration here instead of silently mislabeling the partition.
        """
        configured = cfg.dimensions
        if configured and actual != configured:
            raise RuntimeError(
                f"Embedding dimension mismatch for model {cfg.model!r}: "
                f"configured dimensions={configured} but the embedder returned "
                f"{actual}. Fix the embedding purpose's dimensions (or clear it)."
            )

    def llm_fingerprint(self) -> str:
        """Identifier for the configured LLM embedder.

        Must agree with the fingerprint the embed methods actually emit
        (``f"{model}|{len(vec)}"``). When ``dimensions`` is unset we cannot
        know the real dimension without embedding, so we surface the same
        ``0`` sentinel the empty-batch paths use; a real embed call then
        registers the true-dimension fingerprint on demand.

        **Who may call this directly, and who may not (T2.68, T2.82).** This
        method is pure and session-less, so it cannot check whether the
        sentinel it may return actually has a partition behind it. Callers
        that only need a *name* to write under — the empty-batch paths above,
        and boot-time registration, which registers whatever this returns and
        is a no-op under the sentinel because ``dims <= 0`` fails validation
        before any table is created — may call it bare.

        ``ReembedService`` as a whole is **not** safe calling it bare, and
        this docstring claimed it was until T2.82. Its counting and listing
        paths are: they probe partition existence with ``to_regclass`` and
        treat a missing table as "everything missing" rather than running a
        ``SELECT`` against an unchecked name. Its cache prune is not, because
        it never reads the partition — it keeps the one
        ``entity_embedding_cache`` child the fingerprint names and DROPs every
        other one, so a fingerprint nothing registered keeps nothing and takes
        every live cache in the deployment. That path now asks the question
        itself (``ReembedService._assert_prunable``: a live ``embedders`` row
        plus the child table it implies) and raises
        ``CachePruneFingerprintUnresolved`` rather than dropping on a key
        nothing was ever written under.

        Any other caller about to *read* a per-fingerprint partition without
        such a check (a bulk vector scan, a clustering view — anything that
        will run ``SELECT ... FROM <parent>__<slug>`` unconditionally) must
        NOT call this bare: a ``|0`` result names a partition nothing ever
        wrote to, so the read either raises ``UndefinedTable`` or, worse,
        silently returns empty forever if something else happens to have
        registered that slug. The same is true, more insidiously, of a wrong
        *non-zero* ``dimensions`` (768 configured, 1024 real, T2.83): boot
        registration does not reject a positive dims value, so it happily
        creates an empty, syntactically valid partition nothing will ever
        embed into (``_check_dims`` below refuses every real embed attempt
        under the mismatch) — a bare read against that fingerprint never even
        raises, it just reads zero rows forever. Those read paths go through
        ``PostgresVectorRepository.resolve_read_fingerprint``, which resolves
        to whichever live fingerprint for the same model actually holds data,
        or raises ``EmbedderFingerprintUnresolved`` when none does — never
        proceeds keyed on an unconfirmed fingerprint, sentinel or not.
        Retrieval (``hybrid_search``) never calls this method at all: it
        takes its fingerprint from ``embed()``'s return value, an actual
        vector's length, so it structurally cannot receive a wrong one.
        """
        cfg = self.config["embedding"]
        return self._fingerprint(cfg.model, cfg.dimensions or 0)

    async def embed(self, text: str) -> tuple[list[float], str]:
        """Return (vector, fingerprint).

        Fingerprint identifies which embedder actually produced the vector,
        so the caller can route the write into the matching partition.
        """
        cfg = self.config["embedding"]
        headers = self._headers(cfg)
        async with self._meter("embedding", cfg) as meter:
            if quirks_for(cfg.api_kind).native_protocol:
                url = embeddings_url(cfg.api_kind, cfg.base_url)
                response = await self._post_with_retry(
                    url, headers=headers,
                    body={"model": cfg.model, "input": text},
                    purpose="embedding",
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    raise RuntimeError(
                        f"Ollama embed failed ({e.response.status_code}): {e.request.url.host}"
                    ) from e
                body = response.json()
                vec = body["embeddings"][0]
            else:
                self._assert_can_embed(cfg)
                response = await self._post_with_retry(
                    embeddings_url(cfg.api_kind, cfg.base_url),
                    headers=headers,
                    body={"input": text, "model": cfg.model},
                    purpose="embedding",
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    raise RuntimeError(
                        f"LLM embedding call failed ({e.response.status_code}): {e.request.url.host}"
                    ) from e
                body = response.json()
                vec = body["data"][0]["embedding"]
            # The envelope both protocols already send and this method used to
            # discard: OpenAI-compat as ``usage``, Ollama as
            # ``prompt_eval_count``. Without it, embeddings -- one of the four
            # cost sources -- were structurally unmeasurable.
            meter["payload"] = body
        self._check_dims(cfg, len(vec))
        return vec, self._fingerprint(cfg.model, len(vec))

    async def embed_batch(self, texts: list[str]) -> tuple[list[list[float]], str]:
        if not texts:
            return [], self.llm_fingerprint()
        cfg = self.config["embedding"]
        headers = self._headers(cfg)
        async with self._meter("embedding", cfg) as meter:
            if quirks_for(cfg.api_kind).native_protocol:
                url = embeddings_url(cfg.api_kind, cfg.base_url)
                response = await self._post_with_retry(
                    url, headers=headers,
                    body={"model": cfg.model, "input": texts},
                    purpose="embedding",
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    raise RuntimeError(
                        f"Ollama embed_batch failed ({e.response.status_code}): {e.request.url.host}"
                    ) from e
                body = response.json()
                vectors = body["embeddings"]
            else:
                self._assert_can_embed(cfg)
                response = await self._post_with_retry(
                    embeddings_url(cfg.api_kind, cfg.base_url),
                    headers=headers,
                    body={"input": texts, "model": cfg.model},
                    purpose="embedding",
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as e:
                    raise RuntimeError(
                        f"LLM embed_batch failed ({e.response.status_code}): {e.request.url.host}"
                    ) from e
                body = response.json()
                data = body["data"]
                # Sort by ``index`` to restore input order, but fall back to the
                # element's existing position when a vendor omits the field.
                ordered = sorted(
                    enumerate(data), key=lambda pair: pair[1].get("index", pair[0])
                )
                vectors = [d["embedding"] for _, d in ordered]
            meter["payload"] = body
            # How many texts one call covered. The per-memory view uses this to
            # say "batched" rather than dividing a shared cost N ways and
            # presenting the arithmetic as an observation.
            meter["extra_raw"] = {"batch_size": len(texts)}
        dims = len(vectors[0]) if vectors else (cfg.dimensions or 0)
        if vectors:
            self._check_dims(cfg, dims)
        return vectors, self._fingerprint(cfg.model, dims)

    async def embed_batch_chunked(
        self,
        texts: list[str],
        chunk_size: int,
        concurrency: int,
    ) -> tuple[list[list[float]], str]:
        """Embed many texts via multiple concurrent embed_batch calls.

        Preserves input order; returns the fingerprint of the embedder that
        actually produced the vectors. All chunks must come from the same
        embedder — the active embedder cannot change mid-batch.
        """
        if not texts:
            return [], self.llm_fingerprint()

        chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]
        semaphore = asyncio.Semaphore(concurrency)

        async def run_chunk(chunk: list[str]) -> tuple[list[list[float]], str]:
            async with semaphore:
                return await self.embed_batch(chunk)

        tasks = [asyncio.create_task(run_chunk(chunk)) for chunk in chunks]
        try:
            results = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                if not task.cancelling():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        if not results:
            return [], self.llm_fingerprint()
        fingerprint = results[0][1]
        for _, fp in results[1:]:
            if fp != fingerprint:
                # Active embedder changed mid-flight (admin saved a new
                # embedding config between chunks). Treat as a hard error
                # so we never persist mixed-embedder vectors under one label.
                raise RuntimeError(
                    f"embed_batch_chunked produced mixed fingerprints: {fingerprint!r} vs {fp!r}"
                )
        flat = [vec for chunk_result, _ in results for vec in chunk_result]
        return flat, fingerprint

    async def chat_completion(
        self,
        purpose: str,
        messages: list[dict],
        response_format: dict | None = None,
        seed: int | None = None,
        raise_on_truncation: bool = False,
        return_meta: bool = False,
        usage_subject=None,
        usage_extra: dict | None = None,
    ) -> str | tuple[str, dict]:
        """Meter one chat call, then delegate.

        The metering rides ``return_meta``, which already carries the usage
        envelope for both the compat and the native path — so this wrapper
        needs no second parse and no duplicated extraction. Callers keep the
        signature they had; ``usage_subject`` is the only addition, and it is
        how ingest attributes a call to its own memory rather than to whatever
        ambient scope the batch is running under. ``usage_extra`` is for a
        caller that knows something about the call the orchestrator cannot see
        — that this one request is carrying two purposes' work, for instance.
        """
        cfg = self.config[purpose]
        async with self._meter(purpose, cfg, usage_subject) as meter:
            meter["extra_raw"] = usage_extra
            content, meta = await self._chat_completion_inner(
                purpose,
                messages,
                response_format=response_format,
                seed=seed,
                raise_on_truncation=raise_on_truncation,
                return_meta=True,
            )
            usage = meta.get("usage") if isinstance(meta, dict) else None
            meter["payload"] = {"usage": usage} if usage else None
        return (content, meta) if return_meta else content

    async def _chat_completion_inner(
        self,
        purpose: str,
        messages: list[dict],
        response_format: dict | None = None,
        seed: int | None = None,
        raise_on_truncation: bool = False,
        return_meta: bool = False,
    ) -> str | tuple[str, dict]:
        """Send a chat-completion request to the configured LLM.

        ``return_meta`` opts into ``(content, meta)`` where ``meta`` carries
        the served ``model``, the usage envelope and ``system_fingerprint``.
        Additive by design: the ~30 call sites that read a ``str`` keep it.
        A gate re-measurement must record what was actually served, and the
        response body is the only place that exists.

        ``seed`` (when set) is forwarded to the vendor as a top-level
        ``seed`` parameter in the request body. OpenAI, DeepSeek, z.ai,
        and Google's OpenAI-compat shims all honour it; Anthropic does
        not (the param is silently ignored). Combined with
        ``temperature=0``, a fixed seed makes the same content +
        same prompt produce the same output across calls — the single
        biggest determinism lever for the extraction pipeline. Callers
        typically derive the seed from a hash of the user content so
        same-content requests are reproducible while different content
        gets different sampling paths.
        """
        cfg = self.config[purpose]
        headers = self._headers(cfg)

        if quirks_for(cfg.api_kind).native_protocol:
            return await self._chat_completion_native(
                cfg, purpose, messages, response_format, headers, seed=seed,
                raise_on_truncation=raise_on_truncation, return_meta=return_meta,
            )

        body = self._build_openai_chat_body(
            cfg, messages, response_format=response_format, seed=seed,
        )

        try:
            response = await self._post_with_retry(
                chat_url(cfg.api_kind, cfg.base_url),
                headers=headers,
                body=body,
                purpose=purpose,
            )
        except httpx.ReadTimeout as e:
            # Most common cause on z.ai / DeepSeek: the model is in
            # thinking mode and the response trace exceeds the httpx
            # default. Surface the model + base url so the operator can
            # tell whether to disable thinking or raise the timeout.
            raise RuntimeError(
                f"LLM {purpose} call timed out against {cfg.base_url} "
                f"(model={cfg.model!r}, api_kind={cfg.api_kind!r}). "
                "If the model supports a thinking flag, ensure it's disabled "
                "for non-reasoning purposes, or set a higher timeout via the "
                "purpose params."
            ) from e
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"LLM {purpose} call failed ({e.response.status_code}): {e.response.text[:200]}") from e
        data = response.json()
        self._log_usage(purpose, cfg.model, data.get("usage"))
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"LLM {purpose} unexpected response: {str(data)[:200]}") from e
        if raise_on_truncation and choice.get("finish_reason") == "length":
            raise LLMTruncationError(self._truncation_message(purpose, cfg))
        if return_meta:
            return content, {
                "model": data.get("model"),
                "usage": data.get("usage"),
                "system_fingerprint": data.get("system_fingerprint"),
            }
        return content

    async def _chat_completion_native(
        self,
        cfg: LLMPurposeConfig,
        purpose: str,
        messages: list[dict],
        response_format: dict | None,
        headers: dict,
        seed: int | None = None,
        raise_on_truncation: bool = False,
        return_meta: bool = False,
    ) -> str | tuple[str, dict]:
        """Native (Ollama protocol) ``/api/chat`` call.

        Sends ``"think": false`` when ``cfg.reasoning`` is False — this
        actually disables qwen3-style reasoning, unlike the ``/no_think``
        directive that the OpenAI compat shim ignores.
        """
        url = chat_url(cfg.api_kind, cfg.base_url)
        body: dict = {
            "model": cfg.model,
            "messages": messages,
            "stream": False,
        }
        if not cfg.reasoning:
            body["think"] = False
        # Map common params into Ollama's ``options`` envelope.
        options: dict = {}
        for key, value in cfg.params.items():
            if key in ("extra_body", NO_THINK_PARAM):
                continue
            if key in ("temperature", "top_p", "top_k", "num_predict",
                       "num_ctx", "seed", "repeat_penalty", "stop"):
                options[key] = value
            else:
                # Pass-through for anything Ollama happens to accept top-level.
                body[key] = value
        if "extra_body" in cfg.params:
            # Merge extra_body into options where it makes sense, otherwise
            # top-level (caller's choice).
            extra = cfg.params["extra_body"]
            if isinstance(extra, dict):
                if "options" in extra and isinstance(extra["options"], dict):
                    options.update(extra["options"])
                for k, v in extra.items():
                    if k != "options":
                        body[k] = v
        # Per-call seed override — Ollama accepts ``seed`` inside
        # ``options``. Mirrors the OpenAI-path override above so callers
        # can derive a content-hash seed for reproducibility.
        if seed is not None:
            options["seed"] = int(seed)
        if options:
            body["options"] = options
        if response_format and response_format.get("type") == "json_object":
            body["format"] = "json"

        response = await self._post_with_retry(
            url, headers=headers, body=body, purpose=purpose,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Ollama {purpose} call failed ({e.response.status_code}): {e.response.text[:200]}"
            ) from e
        data = response.json()
        # Ollama returns ``prompt_eval_count`` / ``eval_count`` instead of
        # the OpenAI ``usage`` envelope. Adapt to the same logging surface
        # so the local path also gets a token-count line. Ollama has no
        # cross-call cache to surface.
        if "prompt_eval_count" in data or "eval_count" in data:
            self._log_usage(purpose, cfg.model, {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
            })
        try:
            content = data["message"]["content"]
        except (KeyError, TypeError) as e:
            raise RuntimeError(
                f"Ollama {purpose} unexpected response: {str(data)[:200]}"
            ) from e
        if raise_on_truncation and data.get("done_reason") == "length":
            raise LLMTruncationError(self._truncation_message(purpose, cfg))
        if return_meta:
            return content, {
                "model": data.get("model"),
                "usage": {
                    "prompt_tokens": data.get("prompt_eval_count"),
                    "completion_tokens": data.get("eval_count"),
                },
                "system_fingerprint": None,
            }
        return content

    @staticmethod
    def _truncation_message(purpose: str, cfg: LLMPurposeConfig) -> str:
        cap = _output_cap(cfg.params, cfg.api_kind)
        cap_phrase = f"its {cap}-token output cap" if cap is not None else "its output-token cap"
        return (
            f"LLM {purpose} response was truncated at {cap_phrase} "
            f"(model={cfg.model!r}). Raise the max output tokens for the "
            f"{purpose} purpose in Settings → LLM Pipeline."
        )

    @staticmethod
    def _log_usage(purpose: str, model: str, usage: dict | None) -> None:
        """Surface prompt-caching wins and token counts at INFO level.

        Cache-hit fields by vendor (all read off the OpenAI-compat
        ``usage`` envelope or a small superset):

        - **OpenAI** (gpt-4o, gpt-5 family): automatic prompt caching for
          system prompts ≥1024 tokens. Hit count appears at
          ``usage.prompt_tokens_details.cached_tokens``. Cached tokens
          are billed at 50% of input. No request-side change required.
        - **DeepSeek** (deepseek-chat, deepseek-reasoner): automatic
          context cache. Hit count at ``usage.prompt_cache_hit_tokens``.
          Cached tokens are billed at ~5% of input.
        - **z.ai (GLM-4.5 family)**: documented prompt caching is opt-in
          per request; current OpenAI-compat path may not surface a hit
          field. Treat as no-cache for budgeting.
        - **Anthropic**: requires native ``/v1/messages`` with explicit
          ``cache_control: {"type": "ephemeral"}`` markers. Our
          orchestrator dispatches Anthropic via the OpenAI-compat path
          today, so caching does NOT fire — a native adapter is the
          (separate) lift needed to capture Haiku/Sonnet cache savings.
        """
        if not usage:
            return
        prompt_tokens = usage.get("prompt_tokens", 0) or 0
        completion_tokens = usage.get("completion_tokens", 0) or 0
        # Try every cache-hit field shape we know about.
        cached = 0
        details = usage.get("prompt_tokens_details")
        if isinstance(details, dict):
            cached = details.get("cached_tokens", 0) or 0
        if not cached:
            cached = usage.get("prompt_cache_hit_tokens", 0) or 0
        if not cached:
            cached = usage.get("cached_tokens", 0) or 0
        if cached and prompt_tokens:
            ratio = cached / prompt_tokens
            logger.info(
                "LLM %s [%s]: prompt=%d (cached=%d, %.0f%%) completion=%d",
                purpose, model, prompt_tokens, cached, ratio * 100, completion_tokens,
            )
        else:
            logger.info(
                "LLM %s [%s]: prompt=%d completion=%d",
                purpose, model, prompt_tokens, completion_tokens,
            )

    def _build_openai_chat_body(
        self,
        cfg: LLMPurposeConfig,
        messages: list[dict],
        *,
        response_format: dict | None = None,
        seed: int | None = None,
        stream: bool = False,
    ) -> dict:
        """Assemble the OpenAI-compat ``/chat/completions`` request body.

        Shared by ``chat_completion`` and ``chat_completion_stream`` so both
        paths apply the same params merge, ``extra_body`` overlay, and per-call
        ``seed``, and resolve the same vendor quirks out of
        ``llm_quirks.quirks_for``. Mutates a local copy of ``messages`` only.
        """
        quirks = quirks_for(cfg.api_kind)
        # ``/no_think`` is a qwen chat-template directive, not a wire
        # parameter, so it is opt-in per purpose rather than applied to every
        # compat vendor. It used to be unconditional: measured 2026-08-25,
        # that put a literal " /no_think" on the end of every non-reasoning
        # prompt sent to OpenAI, Anthropic, Gemini, DeepSeek and GLM, none of
        # which have ever defined it. It is still wanted for a qwen model
        # served behind an OpenAI-compatible endpoint (vLLM, LM Studio), which
        # is a property of the MODEL and not of the api_kind — so it lives in
        # the purpose's params where the model is chosen, not in the vendor
        # quirk table where it could not be expressed.
        if not cfg.reasoning and cfg.params.get(NO_THINK_PARAM):
            messages = self._append_no_think(messages)

        body: dict = {"model": cfg.model, "messages": messages}
        if stream:
            body["stream"] = True
        # Apply standard params. NO_THINK_PARAM steers the prompt above and is
        # not a wire field; sending it would reach the vendor as an unknown
        # key — a 400 on the strict ones and, worse, a silent no-op on the
        # permissive ones.
        for key, value in cfg.params.items():
            if key not in ("extra_body", NO_THINK_PARAM):
                body[key] = value
        # Apply extra_body params (provider-specific).
        if "extra_body" in cfg.params:
            body.update(cfg.params["extra_body"])
        if response_format and quirks.accepts_response_format:
            body["response_format"] = response_format
        # Reasoning-by-default vendors silently consume the entire
        # ``max_tokens`` budget on a hidden chain-of-thought before emitting any
        # visible output. With a small budget and a long extraction prompt the
        # trace pegs the cap, ``finish_reason`` is ``length``, and ``content``
        # comes back empty — the parser then fails with "Invalid JSON:
        # Expecting value: line 1 column 1". Inject whichever disable knob the
        # vendor actually honours so non-reasoning purposes get a real response.
        if quirks.thinking_flag and "thinking" not in body:
            body["thinking"] = {
                "type": "enabled" if cfg.reasoning else "disabled",
            }
        if (
            quirks.reasoning_disable_effort is not None
            and not cfg.reasoning
            and "reasoning_effort" not in body
        ):
            body["reasoning_effort"] = quirks.reasoning_disable_effort
        # After the injection, not before it: validating only the configured
        # value would let a mistyped ``reasoning_disable_effort`` in the quirk
        # table ship a 400 to production instead of raising here.
        assert_reasoning_effort(cfg.api_kind, body.get("reasoning_effort"))

        # Per-call seed override. The cfg.params.seed value, if present, can
        # also pin the seed — this overrides it so callers can supply
        # per-content seeds.
        if seed is not None and quirks.honours_seed:
            body["seed"] = int(seed)
        return body

    async def chat_completion_stream(
        self,
        purpose: str,
        messages: list[dict],
        usage_subject=None,
    ):
        """Yields token strings as they arrive from the LLM.

        Metered in a ``finally`` rather than through ``_meter``: this is a
        generator, and a consumer that stops early (a client disconnect) never
        reaches the end of the body. The vendor billed for the call either way,
        so the row is written on the way out whatever happened -- with
        ``tokens_measured=false`` when no usage frame arrived.

        ``usage_subject`` is passed rather than read off the ambient scope for
        the same reason: the ``finally`` below can run at ``aclose`` or at
        collection, which is not guaranteed to be the context the caller set.
        """
        cfg = self.config[purpose]
        headers = self._headers(cfg)
        started = time.perf_counter()
        final_payload: dict | None = None
        ok = True
        error_kind: str | None = None
        try:
            if quirks_for(cfg.api_kind).native_protocol:
                url = chat_url(cfg.api_kind, cfg.base_url)
                body: dict = {
                    "model": cfg.model,
                    "messages": messages,
                    "stream": True,
                }
                if not cfg.reasoning:
                    body["think"] = False
                options: dict = {}
                for key, value in cfg.params.items():
                    if key in ("extra_body", NO_THINK_PARAM):
                        continue
                    if key in ("temperature", "top_p", "top_k", "num_predict",
                               "num_ctx", "seed", "repeat_penalty", "stop"):
                        options[key] = value
                    else:
                        body[key] = value
                # Same extra_body handling as the non-streaming native path.
                # It used to be dropped here, so one purpose config produced
                # two different Ollama bodies depending only on whether the
                # call streamed.
                extra = cfg.params.get("extra_body")
                if isinstance(extra, dict):
                    if isinstance(extra.get("options"), dict):
                        options.update(extra["options"])
                    for k, v in extra.items():
                        if k != "options":
                            body[k] = v
                if options:
                    body["options"] = options

                async with self._client.stream(
                    "POST", url, headers=headers, json=body,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        if chunk.get("done"):
                            # Ollama puts prompt_eval_count/eval_count on exactly
                            # this chunk. Breaking first threw the counts away one
                            # line before they could be read, which is why chat
                            # cost was unmeasurable on the local path.
                            final_payload = chunk
                            break
                        msg = chunk.get("message", {})
                        content = msg.get("content")
                        if content:
                            yield content
                return

            body = self._build_openai_chat_body(cfg, messages, stream=True)
            if quirks_for(cfg.api_kind).stream_usage_option:
                # Without this a streamed compat response carries no usage envelope
                # at all -- the cost is not merely unrecorded, it is never sent.
                body["stream_options"] = {"include_usage": True}

            async with self._client.stream(
                "POST",
                chat_url(cfg.api_kind, cfg.base_url),
                headers=headers,
                json=body,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    chunk = json.loads(data)
                    if chunk.get("usage"):
                        # The usage frame arrives last, with an empty choices list.
                        final_payload = chunk
                    delta = (chunk.get("choices") or [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
        except asyncio.CancelledError:
            ok, error_kind = False, "cancelled"
            raise
        except Exception as exc:
            ok, error_kind = False, type(exc).__name__
            raise
        finally:
            # A disconnected client's cancellation is re-delivered at every
            # await, which would cancel the write itself; the row is written
            # by its own task and outlives the one being torn down.
            await asyncio.shield(spawn_background(
                self._report(purpose, cfg, usage_subject, final_payload,
                             started, ok, error_kind, None),
                name="llm-usage-report",
            ))

    async def close(self):
        self._retiring = True
        await self._drained.wait()
        await self._client.aclose()

    @staticmethod
    def _append_no_think(messages: list[dict]) -> list[dict]:
        messages = [dict(m) for m in messages]
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].get("role") == "user":
                messages[i]["content"] = messages[i]["content"].rstrip() + " /no_think"
                break
        return messages

    @staticmethod
    def _headers(cfg: LLMPurposeConfig) -> dict:
        return {
            "Content-Type": "application/json",
            **auth_headers(cfg.api_kind, cfg.api_key),
        }
