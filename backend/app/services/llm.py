import asyncio
import json
import logging

import httpx

from app.config import LLMPurposeConfig

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    """Routes purpose-specific calls to the right wire protocol.

    Dispatch contract for ``api_kind`` — every chat / embed / tool method
    here follows the same shape: when ``cfg.api_kind == "ollama"`` we go
    through the native Ollama path (``/api/chat`` etc., with
    ``think: false`` support). Every other kind — ``"openai"`` and the
    vendor-specific kinds ``"anthropic"``, ``"google"``, ``"deepseek"``,
    ``"zai"`` — currently shares the OpenAI-compatible path
    (``/chat/completions``, ``/embeddings``). To plug in a native adapter
    for one of those vendors, add a ``cfg.api_kind == "<vendor>"`` branch
    above the OpenAI fallback in each public method. The enum lives on
    ``LLMApiKind`` in ``app/config.py``.
    """

    # Conservative transport-level retries for idempotent connection/transient
    # failures. httpx only retries on connection errors and a closed pool here,
    # not on response status, so this never replays a request the server already
    # accepted — it just smooths over transient 429/5xx-adjacent network blips
    # and DNS/connect flakiness against cloud vendors. Timeouts are unchanged.
    _TRANSPORT_RETRIES = 2

    def __init__(self, config: dict[str, LLMPurposeConfig]):
        self.config = config
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

    # Vendors that have no embeddings endpoint on their OpenAI-compat layer.
    # An embed call against one of these would 404 on every request; fail loud
    # naming the vendor instead. The ``supports_embedding`` flag on the provider
    # profile is the UI-side guard for the same fact; this is the runtime guard
    # for the case where a config slips past it. (``openai``/``google``/``zai``
    # do expose embeddings via the compat path, so they are not listed.)
    _NO_EMBEDDING_VENDORS: frozenset[str] = frozenset({"anthropic", "deepseek"})

    @staticmethod
    def _fingerprint(model: str, dims: int) -> str:
        return f"{model}|{dims}"

    @classmethod
    def _assert_can_embed(cls, cfg) -> None:
        if cfg.api_kind in cls._NO_EMBEDDING_VENDORS:
            raise RuntimeError(
                f"Vendor {cfg.api_kind!r} has no embeddings endpoint; the "
                f"embedding purpose cannot use this provider (model={cfg.model!r}). "
                f"Point the embedding purpose at a provider that supports embeddings."
            )

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
        if cfg.api_kind == "ollama":
            url = self._ollama_url(cfg, "/api/embed")
            response = await self._client.post(
                url, headers=headers, json={"model": cfg.model, "input": text},
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"Ollama embed failed ({e.response.status_code}): {e.request.url.host}"
                ) from e
            vec = response.json()["embeddings"][0]
        else:
            self._assert_can_embed(cfg)
            response = await self._client.post(
                f"{cfg.base_url}/embeddings",
                headers=headers,
                json={"input": text, "model": cfg.model},
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"LLM embedding call failed ({e.response.status_code}): {e.request.url.host}"
                ) from e
            vec = response.json()["data"][0]["embedding"]
        self._check_dims(cfg, len(vec))
        return vec, self._fingerprint(cfg.model, len(vec))

    async def embed_batch(self, texts: list[str]) -> tuple[list[list[float]], str]:
        if not texts:
            return [], self.llm_fingerprint()
        cfg = self.config["embedding"]
        headers = self._headers(cfg)
        if cfg.api_kind == "ollama":
            url = self._ollama_url(cfg, "/api/embed")
            response = await self._client.post(
                url, headers=headers, json={"model": cfg.model, "input": texts},
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"Ollama embed_batch failed ({e.response.status_code}): {e.request.url.host}"
                ) from e
            vectors = response.json()["embeddings"]
        else:
            self._assert_can_embed(cfg)
            response = await self._client.post(
                f"{cfg.base_url}/embeddings",
                headers=headers,
                json={"input": texts, "model": cfg.model},
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"LLM embed_batch failed ({e.response.status_code}): {e.request.url.host}"
                ) from e
            data = response.json()["data"]
            # Sort by ``index`` to restore input order, but fall back to the
            # element's existing position when a vendor omits the field.
            ordered = sorted(
                enumerate(data), key=lambda pair: pair[1].get("index", pair[0])
            )
            vectors = [d["embedding"] for _, d in ordered]
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

        results = await asyncio.gather(*[run_chunk(c) for c in chunks])
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
    ) -> str:
        """Send a chat-completion request to the configured LLM.

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

        if cfg.api_kind == "ollama":
            return await self._chat_completion_ollama(
                cfg, purpose, messages, response_format, headers, seed=seed,
            )

        body = self._build_openai_chat_body(
            cfg, messages, response_format=response_format, seed=seed,
        )

        try:
            response = await self._client.post(
                f"{cfg.base_url}/chat/completions",
                headers=headers,
                json=body,
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
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"LLM {purpose} unexpected response: {str(data)[:200]}") from e

    async def _chat_completion_ollama(
        self,
        cfg: LLMPurposeConfig,
        purpose: str,
        messages: list[dict],
        response_format: dict | None,
        headers: dict,
        seed: int | None = None,
    ) -> str:
        """Native Ollama ``/api/chat`` call.

        Sends ``"think": false`` when ``cfg.reasoning`` is False — this
        actually disables qwen3-style reasoning, unlike the ``/no_think``
        directive that the OpenAI compat shim ignores.
        """
        url = self._ollama_url(cfg, "/api/chat")
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
            if key == "extra_body":
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

        response = await self._client.post(url, headers=headers, json=body)
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
            return data["message"]["content"]
        except (KeyError, TypeError) as e:
            raise RuntimeError(
                f"Ollama {purpose} unexpected response: {str(data)[:200]}"
            ) from e

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

    @staticmethod
    def _ollama_url(cfg: LLMPurposeConfig, path: str) -> str:
        """Build a native-Ollama URL by stripping the OpenAI-compat suffix.

        Lets users keep one ``base_url`` (``http://host:11434/v1``) and have
        both api_kinds work. ``/api/...`` paths replace the compat ``/v1``
        suffix when present.
        """
        base = cfg.base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[:-3]
        elif base.endswith("/api"):
            base = base[:-4]
        return f"{base}{path}"

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
        paths apply the same params merge, ``extra_body`` overlay, Anthropic
        ``response_format`` drop, the zai/deepseek hidden-reasoning disable, and
        the per-call ``seed``. Mutates a local copy of ``messages`` only.
        """
        # ``/no_think`` is a soft directive — works for some qwen variants but
        # is silently ignored by others. The ``ollama`` path uses
        # ``"think": false`` instead.
        if not cfg.reasoning:
            messages = self._append_no_think(messages)

        body: dict = {"model": cfg.model, "messages": messages}
        if stream:
            body["stream"] = True
        # Apply standard params.
        for key, value in cfg.params.items():
            if key != "extra_body":
                body[key] = value
        # Apply extra_body params (provider-specific).
        if "extra_body" in cfg.params:
            body.update(cfg.params["extra_body"])
        if response_format:
            # Anthropic's OpenAI-compat shim only accepts
            # ``response_format.type == "json_schema"`` with strict=True
            # and a fully-defined schema. The loose ``json_object`` form
            # that OpenAI/DeepSeek/z.ai accept is rejected with HTTP 400.
            # Our extraction path encodes the schema in the prompt rather
            # than a structured Pydantic schema, so we cannot supply a
            # strict json_schema. Drop the field entirely for Anthropic
            # and rely on the in-prompt schema instructions; the parser
            # in extraction.py strips the markdown fences Anthropic
            # sometimes wraps JSON in.
            if cfg.api_kind != "anthropic":
                body["response_format"] = response_format
        # Reasoning-by-default models (z.ai's GLM-4.5/5 family,
        # DeepSeek v4) silently consume the entire ``max_tokens`` budget
        # on a hidden chain-of-thought before emitting any visible
        # output. With max_tokens=2048 and a long extraction prompt the
        # reasoning trace pegs the cap, ``finish_reason`` is ``length``,
        # and ``content`` comes back empty — the parser then fails with
        # "Invalid JSON: Expecting value: line 1 column 1". Inject the
        # thinking flag so non-reasoning purposes get a real response.
        # Both vendors accept the same ``thinking`` field shape; for
        # DeepSeek v4 this is the only flag empirically observed to
        # zero out ``reasoning_tokens`` (the documented
        # ``reasoning_effort=low|high`` and ``enable_thinking=false``
        # only reduce, not eliminate, the hidden trace).
        if cfg.api_kind in {"zai", "deepseek"} and "thinking" not in body:
            body["thinking"] = {
                "type": "enabled" if cfg.reasoning else "disabled",
            }

        # Per-call seed override (Anthropic ignores; everyone else honours).
        # The cfg.params.seed value, if present, can also pin the seed —
        # this overrides it so callers can supply per-content seeds.
        if seed is not None and cfg.api_kind != "anthropic":
            body["seed"] = int(seed)
        return body

    async def chat_completion_stream(
        self,
        purpose: str,
        messages: list[dict],
    ):
        """Yields token strings as they arrive from the LLM."""
        cfg = self.config[purpose]
        headers = self._headers(cfg)

        if cfg.api_kind == "ollama":
            url = self._ollama_url(cfg, "/api/chat")
            body: dict = {
                "model": cfg.model,
                "messages": messages,
                "stream": True,
            }
            if not cfg.reasoning:
                body["think"] = False
            options: dict = {}
            for key, value in cfg.params.items():
                if key == "extra_body":
                    continue
                if key in ("temperature", "top_p", "top_k", "num_predict",
                           "num_ctx", "seed", "repeat_penalty", "stop"):
                    options[key] = value
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
                        break
                    msg = chunk.get("message", {})
                    content = msg.get("content")
                    if content:
                        yield content
            return

        body = self._build_openai_chat_body(cfg, messages, stream=True)

        async with self._client.stream(
            "POST",
            f"{cfg.base_url}/chat/completions",
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
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content

    async def close(self):
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
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            if cfg.api_kind == "anthropic":
                # Anthropic authenticates via x-api-key (not Bearer) and
                # requires the anthropic-version header. The OpenAI-compat
                # vendors all take Authorization: Bearer.
                headers["x-api-key"] = cfg.api_key
                headers["anthropic-version"] = "2023-06-01"
            else:
                headers["Authorization"] = f"Bearer {cfg.api_key}"
        return headers
