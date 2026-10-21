"""Knowledge-base management (report FR 'Manage knowledge-base information'; use cases Add/Update/Remove)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import Conversation, KnowledgeDocument, KnowledgeEntry, Language, Message
from ..schemas import KnowledgeEntryIn, KnowledgeEntryOut, RefreshRequest
from ..services import firecrawl
from ..services.ingest import embed_entry, ingest_catalog, ingest_entries

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(x_admin_token: str = Header(default=""), token: str = Query(default="")) -> None:
    """Admin token via the X-Admin-Token header, or ?token= so diagnostics can be opened straight in a browser."""
    if (x_admin_token or token) != get_settings().admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


def _out(e: KnowledgeEntry) -> KnowledgeEntryOut:
    return KnowledgeEntryOut(
        entry_id=str(e.entry_id), entry_key=e.entry_key, document_slug=e.document.slug, language_code=e.language.language_code,
        section_title=e.section_title, question_text=e.question_text, alt_questions=e.alt_questions or [],
        answer_text=e.answer_text, page_reference=e.page_reference, review_status=e.review_status, is_active=e.is_active,
        embedding_model=e.embedding_model, created_at=e.created_at.isoformat(), updated_at=e.updated_at.isoformat(),
    )


@router.get("/entries", response_model=list[KnowledgeEntryOut], dependencies=[Depends(require_admin)])
def list_entries(db: Session = Depends(get_db), language: str | None = None, status: str | None = None,
                 q: str | None = None, limit: int = Query(200, le=1000)):
    stmt = select(KnowledgeEntry).join(Language)
    if language:
        stmt = stmt.where(Language.language_code == language)
    if status:
        stmt = stmt.where(KnowledgeEntry.review_status == status)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(KnowledgeEntry.question_text.ilike(like) | KnowledgeEntry.answer_text.ilike(like) | KnowledgeEntry.entry_key.ilike(like))
    rows = db.execute(stmt.order_by(KnowledgeEntry.entry_key, Language.language_code).limit(limit)).scalars().all()
    return [_out(e) for e in rows]


@router.post("/entries", response_model=KnowledgeEntryOut, dependencies=[Depends(require_admin)], status_code=201)
def create_entry(body: KnowledgeEntryIn, db: Session = Depends(get_db)):
    doc = db.execute(select(KnowledgeDocument).where(KnowledgeDocument.slug == body.document_slug)).scalar_one_or_none()
    lang = db.execute(select(Language).where(Language.language_code == body.language_code)).scalar_one_or_none()
    if not doc or not lang:
        raise HTTPException(status_code=400, detail="Unknown document_slug or language_code")
    dup = db.execute(select(KnowledgeEntry).where(KnowledgeEntry.entry_key == body.entry_key,
                                                  KnowledgeEntry.language_id == lang.language_id)).scalar_one_or_none()
    if dup:
        raise HTTPException(status_code=409, detail="Entry with this key and language already exists")
    e = KnowledgeEntry(entry_key=body.entry_key, document_id=doc.document_id, language_id=lang.language_id,
                       section_title=body.section_title, question_text=body.question_text, alt_questions=body.alt_questions,
                       answer_text=body.answer_text, page_reference=body.page_reference, review_status=body.review_status,
                       is_active=body.is_active)
    db.add(e)
    db.flush()
    embed_entry(db, e)
    db.refresh(e)
    return _out(e)


@router.put("/entries/{entry_id}", response_model=KnowledgeEntryOut, dependencies=[Depends(require_admin)])
def update_entry(entry_id: str, body: KnowledgeEntryIn, db: Session = Depends(get_db)):
    e = db.get(KnowledgeEntry, uuid.UUID(entry_id))
    if not e:
        raise HTTPException(status_code=404, detail="Entry not found")
    doc = db.execute(select(KnowledgeDocument).where(KnowledgeDocument.slug == body.document_slug)).scalar_one_or_none()
    lang = db.execute(select(Language).where(Language.language_code == body.language_code)).scalar_one_or_none()
    if not doc or not lang:
        raise HTTPException(status_code=400, detail="Unknown document_slug or language_code")
    text_changed = (e.question_text, e.answer_text, e.alt_questions or [], e.section_title) != \
                   (body.question_text, body.answer_text, body.alt_questions, body.section_title)
    e.entry_key, e.document_id, e.language_id = body.entry_key, doc.document_id, lang.language_id
    e.section_title, e.question_text, e.alt_questions = body.section_title, body.question_text, body.alt_questions
    e.answer_text, e.page_reference, e.review_status, e.is_active = body.answer_text, body.page_reference, body.review_status, body.is_active
    if text_changed:
        embed_entry(db, e)
    db.commit()
    db.refresh(e)
    return _out(e)


@router.post("/entries/{entry_id}/approve", response_model=KnowledgeEntryOut, dependencies=[Depends(require_admin)])
def approve_entry(entry_id: str, db: Session = Depends(get_db)):
    e = db.get(KnowledgeEntry, uuid.UUID(entry_id))
    if not e:
        raise HTTPException(status_code=404, detail="Entry not found")
    e.review_status, e.is_active = "approved", True
    embed_entry(db, e)
    db.refresh(e)
    return _out(e)


@router.delete("/entries/{entry_id}", dependencies=[Depends(require_admin)])
def deactivate_entry(entry_id: str, db: Session = Depends(get_db)):
    """Soft delete: 'Remove outdated information' use case keeps the record for traceability."""
    e = db.get(KnowledgeEntry, uuid.UUID(entry_id))
    if not e:
        raise HTTPException(status_code=404, detail="Entry not found")
    e.is_active, e.review_status = False, "rejected"
    db.commit()
    return {"entry_id": entry_id, "is_active": False}


@router.post("/reingest", dependencies=[Depends(require_admin)])
def reingest(db: Session = Depends(get_db), reembed: bool = False):
    return {"catalog": ingest_catalog(db), "entries": ingest_entries(db, reembed=reembed)}


@router.post("/refresh", dependencies=[Depends(require_admin)])
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        return firecrawl.stage_document_refresh(db, body.document_slug, body.url, body.language_code)
    except firecrawl.FirecrawlUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/documents", dependencies=[Depends(require_admin)])
def documents(db: Session = Depends(get_db)):
    rows = db.execute(select(KnowledgeDocument).order_by(KnowledgeDocument.slug)).scalars().all()
    return [{"slug": d.slug, "title": d.title, "domain": d.domain.slug, "source_url": d.source_url,
             "last_verified": d.last_verified.isoformat() if d.last_verified else None, "is_active": d.is_active,
             "entries": len(d.entries)} for d in rows]


@router.get("/stats", dependencies=[Depends(require_admin)])
def stats(db: Session = Depends(get_db)):
    total = db.execute(select(func.count()).select_from(KnowledgeEntry)).scalar() or 0
    by_lang = db.execute(select(Language.language_code, func.count()).join(KnowledgeEntry).group_by(Language.language_code)).all()
    pending = db.execute(select(func.count()).select_from(KnowledgeEntry).where(KnowledgeEntry.review_status == "pending")).scalar() or 0
    convs = db.execute(select(func.count()).select_from(Conversation)).scalar() or 0
    msgs = db.execute(select(func.count()).select_from(Message).where(Message.role == "assistant")).scalar() or 0
    fallbacks = db.execute(select(func.count()).select_from(Message).where(Message.was_fallback)).scalar() or 0
    avg_latency = db.execute(select(func.avg(Message.latency_ms)).where(Message.role == "assistant")).scalar()
    by_domain = db.execute(select(Message.domain, func.count()).where(Message.role == "user").group_by(Message.domain)).all()
    return {"entries_total": total, "entries_by_language": dict(by_lang), "entries_pending": pending,
            "conversations": convs, "answers": msgs, "fallbacks": fallbacks,
            "fallback_rate": round(fallbacks / msgs, 3) if msgs else 0.0,
            "avg_latency_ms": int(avg_latency or 0), "questions_by_domain": dict(by_domain)}


@router.get("/diagnose", dependencies=[Depends(require_admin)])
def diagnose(q: str = Query(..., min_length=1, max_length=1000), language: str = "auto", db: Session = Depends(get_db)):
    """Run one question through every stage separately (nothing is stored) and report what each stage decided,
    including Groq's raw replies. Open in a browser: /api/admin/diagnose?q=how+do+i+get+my+nin&token=ADMIN_TOKEN"""
    from ..services import generation as gen
    from ..services.embeddings import get_embedder
    from ..services.language import SUPPORTED, build_offline_retrieval_query, detect_language
    from ..services.retrieval import hybrid_search
    from ..services.verify import verify_generation

    s = get_settings()
    out: dict = {"question": q, "llm_enabled": s.llm_enabled, "llm_model": s.groq_model if s.llm_enabled else None,
                 "embedder": get_embedder().name}
    det = detect_language(q)
    out["detection"] = {"language": det.language, "confidence": det.confidence, "scores": det.scores}
    llm = gen.get_llm()
    rewrite = llm.rewrite_query(q, []) if llm.available else None
    out["rewrite"] = {"result": rewrite, "model": llm.last_model, "error": llm.last_error} if llm.available else "llm disabled"
    detected = det.language
    if rewrite and rewrite.get("language") in SUPPORTED and det.confidence < 0.6:
        detected = rewrite["language"]
    target = language if language in SUPPORTED else detected
    offline_q = build_offline_retrieval_query(q, detected, [])
    rq = str(rewrite["query"]) if rewrite and rewrite.get("query") else offline_q
    out["retrieval_query"] = {"used": rq, "offline_version": offline_q, "target_language": target}
    rr = hybrid_search(db, rq, q, target, query_language=detected)
    out["retrieval"] = {"grounded": rr.grounded, "reason": rr.reason, "domain": rr.domain, "top_dense": round(rr.top_dense, 3),
                        "top_lexical": round(rr.top_lexical, 3),
                        "results": [{"entry_key": r.entry_key, "language": r.language_code, "dense": round(r.dense_score, 3),
                                     "lexical": round(r.lexical_score, 3), "fused": round(r.fused_score, 4), "ranks": r.ranks}
                                    for r in rr.results]}
    if not rr.grounded:
        out["outcome"] = "fallback: retrieval not grounded (" + rr.reason + ")"
        return out
    if not llm.available:
        out["outcome"] = "extractive: no GROQ_API_KEY, verified entry served verbatim"
        return out
    result = llm.generate(q, target, rr.results, [])
    out["generation"] = {"model": llm.last_model, "error": llm.last_error,
                         "raw": result.raw if result else None,
                         "parsed": None if not result else {"cited": result.cited, "insufficient": result.insufficient,
                                                            "confidence": result.confidence, "answer": result.answer}}
    if result is None:
        out["outcome"] = "extractive: Groq call failed or returned no usable JSON (see generation.error)"
    elif result.insufficient:
        out["outcome"] = "fallback: model declared the context insufficient"
    elif not result.cited or result.confidence < 0.4:
        out["outcome"] = "extractive: model output had no citations or low confidence"
    else:
        v = verify_generation(result, rr.results, target)
        out["verification"] = {"action": v.action, "passed": v.passed, "failed": v.failed}
        out["outcome"] = {"keep": "llm answer shown", "extractive": "extractive: answer failed verification",
                          "fallback": "fallback: answer failed verification"}[v.action]
    return out
