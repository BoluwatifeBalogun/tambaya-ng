"""The orchestrator: algorithm steps 1 to 10 from docs/PLAN.md §2 (report §3.12.3 / §3.14.3)."""
from __future__ import annotations

import re
import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AppUser, Conversation, Message
from ..schemas import ChatResponse, SourceCard, Timings
from . import generation as gen
from . import smalltalk
from .language import (SUPPORTED, build_offline_retrieval_query, carry_intent, detect_language, looks_like_followup,
                       normalise_sms)
from .retrieval import OUT_OF_SCOPE, Retrieved, hybrid_search, route_domain, sibling_in_language
from .verify import verify_generation

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class ValidationError(ValueError):
    pass


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _get_or_create_user(db: Session, user_id: str | None) -> AppUser:
    if user_id:
        try:
            u = db.get(AppUser, uuid.UUID(user_id))
            if u:
                return u
        except ValueError:
            pass
    u = AppUser()
    db.add(u)
    db.flush()
    return u


def _get_or_create_conversation(db: Session, conversation_id: str | None, user: AppUser, language: str) -> Conversation:
    if conversation_id:
        try:
            c = db.get(Conversation, uuid.UUID(conversation_id))
            if c and c.user_id == user.user_id:
                return c
        except ValueError:
            pass
    c = Conversation(user_id=user.user_id, language_code=language)
    db.add(c)
    db.flush()
    return c


def _history(db: Session, conversation: Conversation, limit: int) -> list[dict]:
    rows = db.execute(
        select(Message).where(Message.conversation_id == conversation.conversation_id)
        .order_by(Message.created_at.desc()).limit(limit)
    ).scalars().all()
    return [{"role": m.role, "text": m.text, "retrieval_query": m.retrieval_query, "domain": m.domain,
             "top_entry_key": m.top_entry_key, "language": m.language_code} for m in reversed(rows)]


def _source_cards(context: list[Retrieved], cited: list[int]) -> list[SourceCard]:
    cards = []
    for i, r in enumerate(context, start=1):
        if cited and i not in cited:
            continue
        cards.append(SourceCard(
            n=i, entry_id=r.entry_id, entry_key=r.entry_key, title=r.document_title, section_title=r.section_title,
            agency=r.agency_name, domain=r.domain_slug, source_url=r.source_url, last_verified=r.last_verified,
            language=r.language_code, score=round(r.dense_score, 3),
        ))
    return cards


# "A and B" questions. A comma only joins two intents when the second clause asks something specific
# ("..., how much?"), not "I lost my passport, what do I do?". Igbo "na" counts only as a separate word ("na-efu" is not).
_CONJ = re.compile(r"\b(and|also|plus|as well as|&|da kuma|kuma|àti|ati|nakwa)\b|(?<![\w-])na(?=\s)|"
                   r"[,;] *(how (much|long|many)|what (documents|are the|is the)|where|when|nawa|yaya|ina|èló|kedu|ego ole)", re.I)


def _multi_intent_extras(db: Session, text: str, context: list[Retrieved], target: str) -> list[Retrieved]:
    """For 'A and B' questions, include a second strong entry from the same domain in the extractive answer."""
    if len(context) < 2 or not _CONJ.search(text):
        return []
    first, second = context[0], context[1]
    if second.domain_slug != first.domain_slug or second.entry_key == first.entry_key:
        return []
    if second.fused_score < 0.7 * first.fused_score and second.dense_score < 0.8 * first.dense_score:
        return []
    native = sibling_in_language(db, second.entry_key, target) if second.language_code != target else None
    return [native or second]


def _renumber(answer: str, cited: list[int]) -> tuple[str, list[int]]:
    """Make citation numbers contiguous [1..n] in the order they were cited, so the UI cards line up."""
    if not cited:
        return answer, []
    mapping = {old: new for new, old in enumerate(cited, start=1)}
    def repl(m):
        old = int(m.group(1))
        return f"[{mapping[old]}]" if old in mapping else ""
    return re.sub(r"\[(\d+)\]", repl, answer), list(mapping.values())


def _smalltalk_response(db: Session, conversation: Conversation, user: AppUser, text: str, chit: smalltalk.SmallTalk,
                        language: str, history: list[dict], t_total: float) -> ChatResponse:
    if language in SUPPORTED:
        target = language
    elif chit.language != "en":
        target = chit.language
    else:
        # neutral words ("ok", "thanks", "hi") keep the language the conversation is already in
        prev = next((h.get("language") for h in reversed(history) if h["role"] == "user" and h.get("language") in SUPPORTED), None)
        target = prev or "en"
    reply = smalltalk.reply(chit.kind, target)
    total_ms = _ms(t_total)
    db.add(Message(conversation_id=conversation.conversation_id, role="user", text=text, language_code=target, domain="",
                   retrieval_query="", top_similarity=0.0, top_entry_key=""))
    db.add(Message(conversation_id=conversation.conversation_id, role="assistant", text=reply, language_code=target, domain="",
                   cited_entry_ids=[], was_fallback=False, latency_ms=total_ms, top_similarity=0.0))
    db.commit()
    return ChatResponse(
        conversation_id=str(conversation.conversation_id), user_id=str(user.user_id), answer=reply, language=target,
        detected_language=chit.language if chit.language != "en" else target, domain="general", retrieval_query="",
        sources=[], needs_official_action=False, official_channel=None, fallback=False, mode="chat", confidence=1.0,
        checks=[f"smalltalk:{chit.kind}"],
        timings=Timings(language_ms=0, retrieval_ms=0, generation_ms=0, total_ms=total_ms),
    )


def answer(db: Session, message: str, language: str, conversation_id: str | None, user_id: str | None) -> ChatResponse:
    s = get_settings()
    t_total = time.perf_counter()

    # 1. VALIDATE
    text = _CONTROL.sub("", (message or "")).strip()
    if not text:
        raise ValidationError("Please type a question.")
    if len(text) > s.max_message_chars:
        raise ValidationError(f"Please keep your question under {s.max_message_chars} characters.")

    user = _get_or_create_user(db, user_id)
    conversation = _get_or_create_conversation(db, conversation_id, user, language)
    history = _history(db, conversation, s.history_turns)

    # 1b. SMALL TALK: greetings, thanks, "ok", goodbyes are answered instantly in the user's language (no retrieval,
    # no LLM) and stored with an empty domain so the next follow-up still reaches the last real topic.
    chit = smalltalk.classify(text)
    if chit:
        return _smalltalk_response(db, conversation, user, text, chit, language, history, t_total)

    # 2. IDENTIFY LANGUAGE
    t0 = time.perf_counter()
    detection = detect_language(text)
    detected = detection.language
    llm = gen.get_llm()
    rewrite = llm.rewrite_query(text, history) if llm.available else None
    if rewrite and rewrite.get("language") in SUPPORTED and detection.confidence < 0.6:
        detected = rewrite["language"]
    target = language if language in SUPPORTED else detected

    # 3. BUILD RETRIEVAL QUERY
    prev_user = [h for h in history if h["role"] == "user"]
    prev_queries = [h["retrieval_query"] for h in prev_user if h.get("retrieval_query")]
    prev_domain = next((h["domain"] for h in reversed(prev_user) if h.get("domain") and h["domain"] != OUT_OF_SCOPE), None)
    if prev_domain == "general":
        # A refusal or boundary turn ("licence without test?") still names a service: keep that as the topic.
        last = next(h for h in reversed(prev_user) if h.get("domain") == "general")
        named, _ = route_domain(db, build_offline_retrieval_query(last["text"], last.get("language") or detected, []))
        if named not in (OUT_OF_SCOPE, "general"):
            prev_domain = named
    prev_key = next((h["top_entry_key"] for h in reversed(prev_user) if h.get("top_entry_key")), None)
    # A message that names a different service ("and passport?", "wetin about driver licence?") switches topic: the
    # previous topic is not appended, but the previous INTENT (fee, documents, renewal...) is carried when the new
    # message has none of its own.
    clean = normalise_sms(text) if detected in ("en", "pcm") else text
    own_domain, _ = route_domain(db, build_offline_retrieval_query(text, detected, []))
    switched = bool(prev_domain) and own_domain not in (OUT_OF_SCOPE, "general", prev_domain)
    # In a service conversation, a short message that names no service of its own continues the current topic
    # ("so what are the real requirements?", "and the documents nko?").
    followup = bool(prev_domain) and not switched and (
        looks_like_followup(text, detected) or (own_domain == OUT_OF_SCOPE and len(re.findall(r"\w+", text)) <= 10))
    if rewrite and rewrite.get("query"):
        retrieval_query = str(rewrite["query"])[:600]
    elif switched:
        retrieval_query = build_offline_retrieval_query(text, detected, [])
        carried = carry_intent(text, prev_key) if looks_like_followup(text, detected) else ""
        if carried:
            retrieval_query = f"{retrieval_query} {carried}"[:600]
            clean = f"{carried} {clean}"  # so the phrase leg compares "fee ... NIN", not the bare "what of NIN?"
    else:
        retrieval_query = build_offline_retrieval_query(text, detected, prev_queries, prev_domain, prev_key, followup)
    language_ms = _ms(t0)

    # 4 + 5 + 6. ROUTE, HYBRID RETRIEVE, GATE
    t0 = time.perf_counter()
    is_followup = followup
    rr = hybrid_search(db, retrieval_query, clean, target, prev_domain, is_followup, query_language=detected)
    retrieval_ms = _ms(t0)

    # 7 + 8 + 9. GENERATE / VERIFY / FALLBACK
    t0 = time.perf_counter()
    context = rr.results
    checks: list[str] = [f"retrieval:{rr.reason}"]
    if not rr.grounded:
        result = gen.fallback_answer(target, rr.domain)
        context = []
    else:
        result = llm.generate(text, target, context, history) if llm.available else None
        if result is not None:
            if result.insufficient:
                # Model says the context does not answer it: controlled fallback rather than free text.
                checks.append("model_declared_insufficient")
                result = gen.fallback_answer(target, rr.domain if rr.domain != OUT_OF_SCOPE else context[0].domain_slug)
                context = []
            elif not result.cited or result.confidence < 0.4:
                # Retrieval was grounded but the model's output is unusable (no citations / unsure): serve the
                # verified entry verbatim instead of hiding a good answer behind a refusal.
                checks.append("FAILED:" + ("no_citations" if not result.cited else "low_model_confidence"))
                result = None
            else:
                verdict = verify_generation(result, context, target)
                checks += verdict.passed + [f"FAILED:{f}" for f in verdict.failed]
                if verdict.action == "fallback":
                    result = gen.fallback_answer(target, rr.domain if rr.domain != OUT_OF_SCOPE else context[0].domain_slug)
                    context = []
                elif verdict.action == "extractive":
                    result = None  # degrade to the verbatim verified entry below
        llm_error = getattr(llm, "last_error", None)
        if result is None and llm.available and llm_error:
            checks.append(f"llm_error:{llm_error}")
        if result is None:
            top = context[0]
            native = sibling_in_language(db, top.entry_key, target) if top.language_code != target else None
            extra = _multi_intent_extras(db, text, context, target)
            result = gen.extractive_answer(target, top, native, extra)
            context = [native or top] + extra
    generation_ms = _ms(t0)

    answer_text, cited = _renumber(result.answer, result.cited) if result.mode == "llm" else (result.answer, result.cited)
    ordered_context = [context[i - 1] for i in result.cited] if result.mode == "llm" else context
    cards = _source_cards(ordered_context, cited if result.mode == "llm" else [])
    domain = rr.domain if rr.domain != OUT_OF_SCOPE or not ordered_context else ordered_context[0].domain_slug

    # 10. PERSIST (no PII) + RESPOND
    total_ms = _ms(t_total)
    db.add(Message(conversation_id=conversation.conversation_id, role="user", text=text, language_code=detected,
                   domain=domain, retrieval_query=retrieval_query, top_similarity=rr.top_dense,
                   top_entry_key=(cards[0].entry_key if cards else "")))
    db.add(Message(conversation_id=conversation.conversation_id, role="assistant", text=answer_text, language_code=target,
                   domain=domain, cited_entry_ids=[c.entry_id for c in cards], was_fallback=result.mode == "fallback",
                   latency_ms=total_ms, top_similarity=rr.top_dense))
    db.commit()

    return ChatResponse(
        conversation_id=str(conversation.conversation_id), user_id=str(user.user_id), answer=answer_text,
        language=target, detected_language=detected, domain=domain, retrieval_query=retrieval_query, sources=cards,
        needs_official_action=result.needs_official_action, official_channel=result.official_channel,
        fallback=result.mode == "fallback", mode=result.mode, confidence=round(result.confidence, 2), checks=checks,
        timings=Timings(language_ms=language_ms, retrieval_ms=retrieval_ms, generation_ms=generation_ms, total_ms=total_ms),
    )
