from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMPurposeConfig(BaseModel):
    provider: str = "ollama"
    base_url: str = "http://localhost:11434/v1"
    model: str = "nomic-embed-text"
    api_key: str | None = None
    dimensions: int | None = None
    params: dict = Field(default_factory=dict)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem"
    test_database_url: str = "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test"
    qdrant_url: str = "http://localhost:6333"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "darkmem123"
    api_key_prefix: str = "dm_"

    llm_embedding: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="nomic-embed-text", dimensions=768,
    )
    llm_extraction: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen3:8b", params={"temperature": 0.2},
    )
    llm_reasoning: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen3:8b", params={"temperature": 0.7},
    )
    llm_summarization: LLMPurposeConfig = LLMPurposeConfig(
        provider="ollama", base_url="http://localhost:11434/v1",
        model="qwen3:8b", params={"temperature": 0.3},
    )


settings = Settings()
