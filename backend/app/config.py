from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data" / "knowledge"
FRONTEND_DIR = PROJECT_DIR / "frontend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Tambaya NG"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/tambaya"

    # Groq (generation + query rewriting). Groq serves chat models only; embeddings are computed locally.
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    groq_fallback_model: str = "openai/gpt-oss-20b"
    groq_reasoning_effort: str = "low"
    groq_timeout_s: float = 25.0

    embed_dim: int = 768
    local_embed_model: str = ""  # optional sentence-transformers model, e.g. intfloat/multilingual-e5-small (EMBED_DIM=384)

    admin_token: str = "change-me"
    firecrawl_api_key: str = ""
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    retrieval_top_k: int = 5
    dense_candidates: int = 12
    lexical_candidates: int = 12
    # Grounding gate thresholds (cosine similarity). Calibrated separately for the two embedders.
    gate_dense_model: float = 0.55  # for a sentence-transformers embedder
    gate_dense_local: float = 0.30
    gate_lexical_min: float = 0.05

    max_message_chars: int = 1000
    history_turns: int = 6

    @property
    def sqlalchemy_url(self) -> str:
        """Hosting providers hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the psycopg driver prefix."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://"):]
        return url

    @property
    def llm_enabled(self) -> bool:
        return bool(self.groq_api_key.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
