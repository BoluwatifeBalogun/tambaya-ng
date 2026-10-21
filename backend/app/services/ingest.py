"""Knowledge-base preparation (report §3.19 steps 1 to 3): load catalog + entries JSON, embed, store."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import DATA_DIR
from ..models import Agency, KnowledgeDocument, KnowledgeEntry, Language, ServiceDomain, Source
from .embeddings import get_embedder
from .retrieval import invalidate_vocabulary


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ingest_catalog(db: Session, data_dir: Path = DATA_DIR) -> dict[str, int]:
    cat = _load(data_dir / "catalog.json")
    counts = {"languages": 0, "agencies": 0, "domains": 0, "documents": 0}

    langs: dict[str, Language] = {}
    for l in cat["languages"]:
        obj = db.execute(select(Language).where(Language.language_code == l["code"])).scalar_one_or_none()
        if not obj:
            obj = Language(language_code=l["code"])
            db.add(obj)
            counts["languages"] += 1
        obj.language_name, obj.native_name = l["name"], l.get("native_name", l["name"])
        obj.is_active, obj.native_kb = l.get("is_active", True), l.get("native_kb", False)
        langs[l["code"]] = obj

    agencies: dict[str, Agency] = {}
    for a in cat["agencies"]:
        obj = db.execute(select(Agency).where(Agency.slug == a["slug"])).scalar_one_or_none()
        if not obj:
            obj = Agency(slug=a["slug"])
            db.add(obj)
            counts["agencies"] += 1
        obj.agency_name, obj.agency_description = a["name"], a.get("description", "")
        obj.website_url, obj.contact_info = a.get("website_url", ""), a.get("contact_info", "")
        agencies[a["slug"]] = obj
    db.flush()

    domains: dict[str, ServiceDomain] = {}
    for d in cat["domains"]:
        obj = db.execute(select(ServiceDomain).where(ServiceDomain.slug == d["slug"])).scalar_one_or_none()
        if not obj:
            obj = ServiceDomain(slug=d["slug"])
            db.add(obj)
            counts["domains"] += 1
        obj.domain_name, obj.description, obj.keywords = d["name"], d.get("description", ""), d.get("keywords", [])
        obj.agency_id = agencies[d["agency"]].agency_id if d.get("agency") else None
        domains[d["slug"]] = obj
    db.flush()

    for doc in cat["documents"]:
        obj = db.execute(select(KnowledgeDocument).where(KnowledgeDocument.slug == doc["slug"])).scalar_one_or_none()
        if not obj:
            obj = KnowledgeDocument(slug=doc["slug"])
            db.add(obj)
            counts["documents"] += 1
        obj.domain_id = domains[doc["domain"]].domain_id
        obj.title, obj.document_type, obj.source_url = doc["title"], doc.get("document_type", "webpage"), doc["source_url"]
        obj.last_verified = date.fromisoformat(doc["last_verified"]) if doc.get("last_verified") else None
        db.flush()
        if not obj.sources:
            db.add(Source(document_id=obj.document_id, source_name=doc.get("source_name", doc["title"]),
                          source_url=doc["source_url"], source_type="official"))
    db.commit()
    return counts


def ingest_entries(db: Session, data_dir: Path = DATA_DIR, reembed: bool = False) -> dict[str, int]:
    emb = get_embedder()
    langs = {l.language_code: l for l in db.execute(select(Language)).scalars()}
    docs = {d.slug: d for d in db.execute(select(KnowledgeDocument)).scalars()}
    counts = {"created": 0, "updated": 0, "embedded": 0}
    to_embed: list[KnowledgeEntry] = []

    for path in sorted(data_dir.glob("entries.*.json")):
        code = path.stem.split(".")[-1]
        if code not in langs:
            raise ValueError(f"Unknown language file {path.name}; add it to catalog.json first")
        for e in _load(path):
            obj = db.execute(select(KnowledgeEntry).where(
                KnowledgeEntry.entry_key == e["id"], KnowledgeEntry.language_id == langs[code].language_id
            )).scalar_one_or_none()
            if not obj:
                obj = KnowledgeEntry(entry_key=e["id"], language_id=langs[code].language_id)
                db.add(obj)
                counts["created"] += 1
            else:
                counts["updated"] += 1
            changed = (obj.question_text != e["question_text"] or obj.answer_text != e["answer_text"]
                       or (obj.alt_questions or []) != e.get("alt_questions", []))
            obj.document_id = docs[e["document"]].document_id
            obj.section_title = e.get("section_title", "")
            obj.question_text, obj.alt_questions, obj.answer_text = e["question_text"], e.get("alt_questions", []), e["answer_text"]
            obj.page_reference = e.get("page_reference", "")
            obj.review_status, obj.is_active = "approved", True
            if changed or reembed or obj.embedding_vector is None or obj.embedding_model != emb.name:
                to_embed.append(obj)
    db.flush()

    for i in range(0, len(to_embed), 32):
        batch = to_embed[i : i + 32]
        vecs = emb.embed([b.embedding_text if emb.is_model else b.embedding_text_local for b in batch])
        for b, v in zip(batch, vecs):
            b.embedding_vector = v
            b.embedding_model = emb.name
            counts["embedded"] += 1
    db.commit()
    invalidate_vocabulary()
    return counts


def embed_entry(db: Session, entry: KnowledgeEntry) -> None:
    emb = get_embedder()
    entry.embedding_vector = emb.embed([entry.embedding_text if emb.is_model else entry.embedding_text_local])[0]
    entry.embedding_model = emb.name
    db.commit()
    invalidate_vocabulary()
