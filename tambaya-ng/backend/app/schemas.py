from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LanguageCode = Literal["auto", "en", "ha", "yo", "ig", "pcm"]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    language: LanguageCode = "auto"
    conversation_id: str | None = None
    user_id: str | None = None


class SourceCard(BaseModel):
    n: int
    entry_id: str
    entry_key: str
    title: str
    section_title: str
    agency: str
    domain: str
    source_url: str
    last_verified: str | None
    language: str
    score: float


class Timings(BaseModel):
    language_ms: int = 0
    retrieval_ms: int = 0
    generation_ms: int = 0
    total_ms: int = 0


class ChatResponse(BaseModel):
    conversation_id: str
    user_id: str
    answer: str
    language: str
    detected_language: str
    domain: str
    retrieval_query: str
    sources: list[SourceCard]
    needs_official_action: bool = False
    official_channel: str | None = None
    fallback: bool = False
    mode: str  # llm | extractive | fallback | chat (small talk)
    confidence: float = 0.0
    checks: list[str] = []
    timings: Timings


class HealthResponse(BaseModel):
    status: str
    app: str
    database: bool
    pgvector: bool
    llm_enabled: bool
    llm_provider: str
    llm_model: str | None
    embedder: str
    entries_active: int
    languages: list[str]


class KnowledgeEntryIn(BaseModel):
    entry_key: str = Field(..., min_length=2, max_length=64)
    document_slug: str
    language_code: str
    section_title: str = ""
    question_text: str
    alt_questions: list[str] = []
    answer_text: str
    page_reference: str = ""
    review_status: str = "approved"
    is_active: bool = True


class KnowledgeEntryOut(KnowledgeEntryIn):
    entry_id: str
    embedding_model: str
    created_at: str
    updated_at: str


class RefreshRequest(BaseModel):
    document_slug: str
    url: str | None = None
    language_code: str = "en"
