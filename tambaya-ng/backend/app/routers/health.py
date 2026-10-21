from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import KnowledgeEntry, Language
from ..schemas import HealthResponse
from ..services.embeddings import get_embedder

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    s = get_settings()
    db_ok = pgvector_ok = False
    entries = 0
    langs: list[str] = []
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        pgvector_ok = db.execute(text("SELECT count(*) FROM pg_extension WHERE extname='vector'")).scalar() == 1
        entries = db.execute(select(func.count()).select_from(KnowledgeEntry).where(KnowledgeEntry.is_active)).scalar() or 0
        langs = [l for (l,) in db.execute(select(Language.language_code).where(Language.is_active)).all()]
    except Exception:
        pass
    return HealthResponse(status="ok" if db_ok and pgvector_ok else "degraded", app=s.app_name, database=db_ok,
                          pgvector=pgvector_ok, llm_enabled=s.llm_enabled, llm_provider="groq",
                          llm_model=s.groq_model if s.llm_enabled else None, embedder=get_embedder().name,
                          entries_active=entries, languages=langs)
