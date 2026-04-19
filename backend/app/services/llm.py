import asyncio
import json
import logging

import httpx

from app.config import LLMPurposeConfig, ml_pipeline_settings

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    def __init__(self, config: dict[str, LLMPurposeConfig]):
        self.config = config
        self._client = httpx.AsyncClient(timeout=300.0)
        self._warned_ml_unavailable = False

    async def _is_ml_retrieval_enabled(self) -> bool:
        """Check the cached ``ml_retrieval`` feature flag without holding a session."""
        from app.database import async_session_factory  # noqa: PLC0415
        from app.services.pipeline import _get_feature_flags_cached  # noqa: PLC0415
        flags = await _get_feature_flags_cached(async_session_factory)
        return bool(flags.get("ml_retrieval", False))

    async def _embed_ml(self, text: str) -> list[float]:
        # Lazy-load the retriever group. First call blocks while the model
        # warms up; subsequent calls are cheap and just bump the access time.
        def _load_then_encode() -> list[float]:
            from app.services.ml_models import ensure_retriever_loaded  # noqa: PLC0415
            ml = ensure_retriever_loaded()
            prefixed = ml_pipeline_settings.retriever_query_prefix + text
            vec = ml.retriever.encode(
                prefixed,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            return vec.tolist()

        return await asyncio.to_thread(_load_then_encode)

    async def _embed_batch_ml(self, texts: list[str]) -> list[list[float]]:
        def _load_then_encode() -> list[list[float]]:
            from app.services.ml_models import ensure_retriever_loaded  # noqa: PLC0415
            ml = ensure_retriever_loaded()
            prefix = ml_pipeline_settings.retriever_query_prefix
            prefixed = [prefix + t for t in texts]
            batch = ml_pipeline_settings.retriever_batch_size
            mat = ml.retriever.encode(
                prefixed,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=batch,
            )
            return mat.tolist()

        return await asyncio.to_thread(_load_then_encode)

    async def embed(self, text: str) -> list[float]:
        if await self._is_ml_retrieval_enabled():
            try:
                return await self._embed_ml(text)
            except Exception as exc:
                if not self._warned_ml_unavailable:
                    logger.warning("ml_retrieval enabled but load failed: %s", exc)
                    self._warned_ml_unavailable = True
                # Fall through to the Ollama embedder.
        cfg = self.config["embedding"]
        headers = self._headers(cfg)
        response = await self._client.post(
            f"{cfg.base_url}/embeddings",
            headers=headers,
            json={"input": text, "model": cfg.model},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"LLM embedding call failed ({e.response.status_code}): {e.request.url.host}") from e
        return response.json()["data"][0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if await self._is_ml_retrieval_enabled():
            try:
                return await self._embed_batch_ml(texts)
            except Exception as exc:
                if not self._warned_ml_unavailable:
                    logger.warning("ml_retrieval batch path failed, using LLM embedder: %s", exc)
                    self._warned_ml_unavailable = True
        cfg = self.config["embedding"]
        headers = self._headers(cfg)
        response = await self._client.post(
            f"{cfg.base_url}/embeddings",
            headers=headers,
            json={"input": texts, "model": cfg.model},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"LLM embed_batch failed ({e.response.status_code}): {e.request.url.host}") from e
        data = response.json()["data"]
        return [d["embedding"] for d in sorted(data, key=lambda x: x["index"])]

    async def embed_batch_chunked(
        self,
        texts: list[str],
        chunk_size: int,
        concurrency: int,
    ) -> list[list[float]]:
        """Embed many texts via multiple concurrent embed_batch calls.

        Preserves input order. Any chunk failure propagates.
        """
        if not texts:
            return []

        chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]
        semaphore = asyncio.Semaphore(concurrency)

        async def run_chunk(chunk: list[str]) -> list[list[float]]:
            async with semaphore:
                return await self.embed_batch(chunk)

        results = await asyncio.gather(*[run_chunk(c) for c in chunks])
        return [vec for chunk_result in results for vec in chunk_result]

    async def chat_completion(self, purpose: str, messages: list[dict], response_format: dict | None = None) -> str:
        cfg = self.config[purpose]
        headers = self._headers(cfg)

        if not cfg.reasoning:
            messages = self._append_no_think(messages)

        body: dict = {"model": cfg.model, "messages": messages}
        # Apply standard params
        for key, value in cfg.params.items():
            if key != "extra_body":
                body[key] = value
        # Apply extra_body params (provider-specific)
        if "extra_body" in cfg.params:
            body.update(cfg.params["extra_body"])
        if response_format:
            body["response_format"] = response_format

        response = await self._client.post(
            f"{cfg.base_url}/chat/completions",
            headers=headers,
            json=body,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"LLM {purpose} call failed ({e.response.status_code}): {e.response.text[:200]}") from e
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"LLM {purpose} unexpected response: {str(data)[:200]}") from e

    async def chat_completion_tools(
        self, purpose: str, messages: list[dict], tools: list[dict],
    ) -> list[dict]:
        """Send a chat completion with tools and return the tool call results."""
        cfg = self.config[purpose]
        headers = self._headers(cfg)

        if not cfg.reasoning:
            messages = self._append_no_think(messages)

        body: dict = {"model": cfg.model, "messages": messages, "tools": tools}
        for key, value in cfg.params.items():
            if key != "extra_body":
                body[key] = value
        if "extra_body" in cfg.params:
            body.update(cfg.params["extra_body"])

        response = await self._client.post(
            f"{cfg.base_url}/chat/completions",
            headers=headers,
            json=body,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"LLM {purpose} tool call failed ({e.response.status_code}): {e.response.text[:200]}") from e

        data = response.json()
        msg = data.get("choices", [{}])[0].get("message", {})
        tool_calls = msg.get("tool_calls", [])
        results = []
        for tc in tool_calls:
            raw_args = tc["function"].get("arguments", "{}")
            if isinstance(raw_args, str):
                raw_args = json.loads(raw_args)
            results.append({"name": tc["function"]["name"], "arguments": raw_args})
        return results

    async def chat_completion_stream(
        self,
        purpose: str,
        messages: list[dict],
    ):
        """Yields token strings as they arrive from the LLM."""
        cfg = self.config[purpose]
        headers = self._headers(cfg)

        if not cfg.reasoning:
            messages = self._append_no_think(messages)

        body: dict = {"model": cfg.model, "messages": messages, "stream": True}
        for key, value in cfg.params.items():
            if key != "extra_body":
                body[key] = value
        if "extra_body" in cfg.params:
            body.update(cfg.params["extra_body"])

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
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        return headers
