import asyncio
import json

import httpx

from app.config import LLMPurposeConfig


class LLMOrchestrator:
    def __init__(self, config: dict[str, LLMPurposeConfig]):
        self.config = config
        self._client = httpx.AsyncClient(timeout=300.0)

    async def embed(self, text: str) -> list[float]:
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
