"""Post-generation verification (algorithm step 8).

A strong RAG system does not trust the model's output: every number, URL and citation in a generated answer must
be traceable to the retrieved context, the answer must be in the requested language, and the model must not
leak its instructions. Each check returns a reason string; the pipeline degrades to the extractive answer or the
templated fallback when a check fails, so an unfaithful sentence never reaches the user."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .generation import SYSTEM_PROMPT, Generated
from .language import detect_language
from .retrieval import Retrieved

_NUM = re.compile(r"(?:₦|\$|N)\s?\d[\d,]*(?:\.\d+)?|\b\d{1,3}(?:,\d{3})+\b|\b\d{2,}\b|\*\d{3}#")
_URL = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:gov\.ng|com\.ng|org\.ng|ng|com|org|net)\b", re.I)
_LEAK = re.compile(r"(system prompt|admin token|ADMIN_TOKEN|api key|GROQ_API_KEY|gsk_[A-Za-z0-9]{8,}|my instructions|as an ai language model|"
                   r"rules you must follow|CONTEXT entries)", re.I)
_PROMPT_SENTENCES = [s.strip().lower() for s in re.split(r"[.\n]", SYSTEM_PROMPT) if len(s.strip()) > 40]


def _norm_num(tok: str) -> str:
    return re.sub(r"[₦$N\s,]", "", tok)


@dataclass
class Verification:
    ok: bool
    action: str  # keep | extractive | fallback
    failed: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)


def verify_generation(result: Generated, context: list[Retrieved], target_language: str) -> Verification:
    v = Verification(ok=True, action="keep")
    cited_ctx = [context[i - 1] for i in result.cited if 1 <= i <= len(context)]
    ctx_text = " ".join(f"{r.question_text} {r.answer_text} {r.source_url} {r.document_title}" for r in cited_ctx)
    ctx_nums = {_norm_num(t) for t in _NUM.findall(ctx_text)}
    ctx_urls = {u.lower() for u in _URL.findall(ctx_text)}
    answer = result.answer or ""

    def fail(name: str, action: str) -> None:
        v.ok = False
        v.failed.append(name)
        # the stricter action wins
        if action == "fallback" or v.action == "fallback":
            v.action = "fallback"
        else:
            v.action = action

    # 1. answer exists and cites something
    if len(answer.strip()) < 15:
        fail("empty_answer", "fallback")
    else:
        v.passed.append("non_empty")
    if not cited_ctx:
        fail("no_valid_citations", "fallback")
    else:
        v.passed.append("citations_resolve")

    # 2. citation markers in the text must refer to cited entries
    marks = {int(m) for m in re.findall(r"\[(\d+)\]", answer)}
    if marks and not marks.issubset(set(result.cited)):
        fail("unknown_citation_marker", "extractive")
    else:
        v.passed.append("citation_markers")

    # 3. numeric faithfulness: every figure in the answer appears in the cited context
    bad_nums = [t for t in _NUM.findall(answer) if _norm_num(t) not in ctx_nums and not re.fullmatch(r"\[?\d\]?", t)]
    bad_nums = [t for t in bad_nums if not re.fullmatch(r"\d{2,4}", _norm_num(t)) or _norm_num(t) not in ctx_text]
    if bad_nums:
        fail(f"unsupported_numbers:{','.join(bad_nums[:3])}", "extractive")
    else:
        v.passed.append("numbers_grounded")

    # 4. URL faithfulness
    bad_urls = [u for u in _URL.findall(answer) if u.lower() not in ctx_urls and not u.lower().endswith(("nimc.gov.ng", "immigration.gov.ng", "frsc.gov.ng", "nationalpopulation.gov.ng"))]
    if bad_urls:
        fail(f"unsupported_urls:{','.join(bad_urls[:2])}", "extractive")
    else:
        v.passed.append("urls_grounded")

    # 5. language consistency (Pidgin shares English vocabulary, so for Pidgin only a wrong indigenous language fails)
    if target_language == "pcm" and len(answer) > 60:
        d = detect_language(answer)
        if d.language in ("ha", "yo", "ig") and d.confidence >= 0.6:
            fail("wrong_language", "extractive")
        else:
            v.passed.append("language_matches")
    elif target_language != "en" and len(answer) > 60:
        d = detect_language(answer)
        if d.language == "en" and d.confidence >= 0.6:
            fail("wrong_language", "extractive")
        else:
            v.passed.append("language_matches")
    else:
        v.passed.append("language_matches")

    # 6. instruction leak / injection compliance
    low = answer.lower()
    if _LEAK.search(answer) or any(s in low for s in _PROMPT_SENTENCES):
        fail("instruction_leak", "fallback")
    else:
        v.passed.append("no_instruction_leak")

    return v
