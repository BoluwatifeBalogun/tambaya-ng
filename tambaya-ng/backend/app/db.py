from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_engine(_settings.sqlalchemy_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create the pgvector extension, all tables, and the indexes SQLAlchemy cannot express portably."""
    from . import models  # noqa: F401  (register models)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        # Generated full-text column for the lexical leg of hybrid retrieval ('simple' config keeps
        # Hausa/Yoruba/Igbo tokens intact instead of English stemming them).
        conn.execute(text(
            """
            CREATE OR REPLACE FUNCTION immutable_join(arr text[]) RETURNS text
            LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $f$ SELECT array_to_string(arr, ' ') $f$;
            """
        ))
        conn.execute(text(
            """
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                             WHERE table_name='knowledge_entry' AND column_name='search_vector') THEN
                ALTER TABLE knowledge_entry ADD COLUMN search_vector tsvector
                  GENERATED ALWAYS AS (
                    setweight(to_tsvector('simple', coalesce(question_text,'')), 'A') ||
                    setweight(to_tsvector('simple', coalesce(immutable_join(alt_questions),'')), 'A') ||
                    setweight(to_tsvector('simple', coalesce(section_title,'')), 'B') ||
                    setweight(to_tsvector('simple', coalesce(answer_text,'')), 'C')
                  ) STORED;
              END IF;
            END $$;
            """
        ))
        conn.execute(text("ALTER TABLE message ADD COLUMN IF NOT EXISTS top_entry_key VARCHAR(64) DEFAULT ''"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_knowledge_entry_search ON knowledge_entry USING GIN (search_vector)"))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_entry_embedding ON knowledge_entry "
            "USING hnsw (embedding_vector vector_cosine_ops)"
        ))
