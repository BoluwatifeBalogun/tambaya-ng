from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Conversation, Language, Message, ServiceDomain
from ..schemas import ChatRequest, ChatResponse
from ..services import pipeline

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    try:
        return pipeline.answer(db, req.message, req.language, req.conversation_id, req.user_id)
    except pipeline.ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except OperationalError:
        db.rollback()
        raise HTTPException(status_code=503, detail="The knowledge base is temporarily unavailable. Please try again in a moment.")


@router.get("/languages")
def languages(db: Session = Depends(get_db)):
    rows = db.execute(select(Language).where(Language.is_active).order_by(Language.language_code)).scalars().all()
    return [{"code": l.language_code, "name": l.language_name, "native_name": l.native_name, "native_kb": l.native_kb}
            for l in rows]


@router.get("/domains")
def domains(db: Session = Depends(get_db)):
    rows = db.execute(select(ServiceDomain).where(ServiceDomain.is_active)).scalars().all()
    return [{"slug": d.slug, "name": d.domain_name, "description": d.description,
             "agency": d.agency.agency_name if d.agency else None,
             "website": d.agency.website_url if d.agency else None} for d in rows if d.slug != "general"]


@router.get("/conversations/{conversation_id}")
def conversation(conversation_id: str, user_id: str, db: Session = Depends(get_db)):
    try:
        cid, uid = uuid.UUID(conversation_id), uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")
    c = db.get(Conversation, cid)
    if not c or c.user_id != uid:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = db.execute(select(Message).where(Message.conversation_id == cid).order_by(Message.created_at)).scalars().all()
    return {"conversation_id": conversation_id, "messages": [
        {"role": m.role, "text": m.text, "language": m.language_code, "domain": m.domain,
         "fallback": m.was_fallback, "latency_ms": m.latency_ms, "created_at": m.created_at.isoformat()} for m in msgs]}
