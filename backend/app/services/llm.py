import json

import httpx

from app.config import LLMPurposeConfig


class LLMOrchestrator:
    def __init__(self, config: dict[str, LLMPurposeConfig]):
        self.config = config
        self._client = httpx.AsyncClient(timeout=120.0)

    async def embed(self, text: str) -> list[float]:
        cfg = self.config["embedding"]
        headers = self._headers(cfg)
        response = await self._client.post(
            f"{cfg.base_url}/embeddings",
            headers=headers,
            json={"input": text, "model": cfg.model},
        )
        response.raise_for_status()
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
        response.raise_for_status()
        data = response.json()["data"]
        return [d["embedding"] for d in sorted(data, key=lambda x: x["index"])]

    async def chat_completion(self, purpose: str, messages: list[dict], response_format: dict | None = None) -> str:
        cfg = self.config[purpose]
        headers = self._headers(cfg)

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
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    async def chat_completion_stream(
        self,
        purpose: str,
        messages: list[dict],
    ):
        """Yields token strings as they arrive from the LLM."""
        cfg = self.config[purpose]
        headers = self._headers(cfg)

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
    def _headers(cfg: LLMPurposeConfig) -> dict:
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"
        return headers
