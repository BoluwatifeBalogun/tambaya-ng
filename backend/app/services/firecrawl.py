"""Knowledge-base update component (report §3.12.2 item 9, §3.19 step 6).

Collected content is staged with review_status='pending' and is_active=False. Nothing reaches the retrieval
system until an administrator approves it, matching the report's 'review/validation before approval' rule."""
from __future__ import annotations

import re

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import KnowledgeDocument, KnowledgeEntry, Language

FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"


class FirecrawlUnavailable(RuntimeError):
    pass


def scrape_markdown(url: str) -> str:
    s = get_settings()
    if not s.firecrawl_api_key:
        raise FirecrawlUnavailable("FIRECRAWL_API_KEY is not configured")
    with httpx.Client(timeout=60) as client:
        r = client.post(FIRECRAWL_URL, headers={"Authorization": f"Bearer {s.firecrawl_api_key}"},
                        json={"url": url, "formats": ["markdown"], "onlyMainContent": True})
        r.raise_for_status()
        data = r.json()
    return (data.get("data") or {}).get("markdown") or ""


def chunk_markdown(md: str, max_chars: int = 900) -> list[tuple[str, str]]:
    """Split by headings, then by paragraphs; returns (section_title, text) chunks (report §2.5.2 item 3)."""
    chunks: list[tuple[str, str]] = []
    current_title = "Untitled section"
    buf: list[str] = []

    def flush():
        text = "\n".join(buf).strip()
        if len(text) >= 80:
            for i in range(0, len(text), max_chars):
                chunks.append((current_title, text[i : i + max_chars].strip()))
        buf.clear()

    for line in md.splitlines():
        if re.match(r"^#{1,4}\s", line):
            flush()
            current_title = re.sub(r"^#{1,4}\s*", "", line).strip()[:120]
        else:
            buf.append(line)
    flush()
    return chunks


def stage_document_refresh(db: Session, document_slug: str, url: str | None, language_code: str) -> dict:
    doc = db.execute(select(KnowledgeDocument).where(KnowledgeDocument.slug == document_slug)).scalar_one_or_none()
    if not doc:
        raise ValueError(f"Unknown document {document_slug}")
    lang = db.execute(select(Language).where(Language.language_code == language_code)).scalar_one_or_none()
    if not lang:
        raise ValueError(f"Unknown language {language_code}")
    md = scrape_markdown(url or doc.source_url)
    chunks = chunk_markdown(md)
    staged = 0
    for i, (title, text) in enumerate(chunks, start=1):
        key = f"{document_slug}-crawl-{i:03d}"
        exists = db.execute(select(KnowledgeEntry).where(
            KnowledgeEntry.entry_key == key, KnowledgeEntry.language_id == lang.language_id)).scalar_one_or_none()
        if exists:
            exists.answer_text, exists.section_title, exists.review_status, exists.is_active = text, title, "pending", False
        else:
            db.add(KnowledgeEntry(entry_key=key, language_id=lang.language_id, document_id=doc.document_id,
                                  section_title=title, question_text=f"{doc.title}: {title}", answer_text=text,
                                  review_status="pending", is_active=False))
        staged += 1
    db.commit()
    return {"document": document_slug, "chunks_staged": staged, "characters": len(md)}
