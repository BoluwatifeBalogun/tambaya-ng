"""Evaluation harness for Chapter Four (report §3.19 'Planned Evaluation Metrics').

Runs a gold question set through the live pipeline and reports:
  retrieval relevance (hit@1, hit@3), source accuracy, fallback precision on out-of-scope questions,
  language accuracy (answer language == expected), and latency (mean, p95), split by language.

Usage (from backend/):  python -m scripts.evaluate [--out ../docs/evaluation-results.md]
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal  # noqa: E402
from app.services import pipeline  # noqa: E402
from app.services.embeddings import get_embedder  # noqa: E402

# (question, language, expected entry_key or None for out-of-scope)
GOLD = [
    # English
    ("What documents do I need to enrol for a NIN?", "en", "nin-documents"),
    ("Is NIN registration free?", "en", "nin-cost"),
    ("I forgot my NIN, how do I check it?", "en", "nin-retrieve"),
    ("How much is NIN date of birth correction?", "en", "nin-modify-fees"),
    ("Can an agent get my NIN faster if I pay?", "en", "nin-scam-warning"),
    ("How much does a Nigerian passport cost?", "en", "pp-fees"),
    ("How do I apply for a passport for the first time?", "en", "pp-fresh-steps"),
    ("What do I need to get a passport for my child?", "en", "pp-minor"),
    ("How long does it take to get a passport?", "en", "pp-processing-time"),
    ("My passport has expired, how do I renew it?", "en", "pp-renewal"),
    ("How much is a driver's licence for 5 years?", "en", "dl-fees"),
    ("What are the requirements for a driver's licence?", "en", "dl-requirements"),
    ("I lost my driving licence, what do I do?", "en", "dl-reissue"),
    ("How do I renew my driver's licence?", "en", "dl-renewal"),
    ("How do I get a commercial driver's licence?", "en", "dl-commercial"),
    ("How do I register my baby's birth?", "en", "br-how-register"),
    ("Is birth registration free?", "en", "br-cost"),
    ("I am an adult and was never registered at birth, what can I do?", "en", "br-late"),
    ("Can I register a birth online?", "en", "br-online-portals"),
    ("How do I get a death certificate?", "en", "br-death"),
    # Hausa
    ("Wadanne takardu nake buƙata don rajistar NIN?", "ha", "nin-documents"),
    ("Rajistar NIN kyauta ce?", "ha", "nin-cost"),
    ("Nawa ne kuɗin fasfo?", "ha", "pp-fees"),
    ("Ta yaya zan sabunta fasfona?", "ha", "pp-renewal"),
    ("Nawa ne kuɗin lasisin tuƙi?", "ha", "dl-fees"),
    ("Lasisin tuƙina ya ɓace, me zan yi?", "ha", "dl-reissue"),
    ("Ta yaya zan yi rajistar haihuwar ɗana?", "ha", "br-how-register"),
    ("Rajistar haihuwa kyauta ce?", "ha", "br-cost"),
    ("Ta yaya zan gyara ranar haihuwa a NIN?", "ha", "nin-modify-how"),
    ("Ina zan iya neman fasfo?", "ha", "pp-where"),
    # Yoruba / Igbo
    ("Èló ni pásípọ̀ọ̀tù?", "yo", "pp-fees"),
    ("Báwo ni mo ṣe lè forúkọ sílẹ̀ fún NIN?", "yo", "nin-enrol-steps"),
    ("Èló ni ìwé-àṣẹ awakọ̀?", "yo", "dl-fees"),
    ("Ego ole ka paspọtụ na-efu?", "ig", "pp-fees"),
    ("Kedu ka m ga-esi debanye aha ọmụmụ nwa m?", "ig", "br-how-register"),
    ("Kedu ka m ga-esi nweta NIN?", "ig", "nin-enrol-steps"),
    # Out of scope
    ("What is the weather in Lagos today?", "en", None),
    ("Who won the Premier League?", "en", None),
    ("How do I cook jollof rice?", "en", None),
    ("How do I get a Canadian visa?", "en", None),
    ("Yaya yanayin Kano yau?", "ha", None),
    ("Tell me a joke", "en", None),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "docs" / "evaluation-results.md"))
    args = ap.parse_args()

    rows = []
    with SessionLocal() as db:
        for q, lang, expected in GOLD:
            r = pipeline.answer(db, q, "auto", None, None)
            keys = [s["entry_key"] for s in [c.model_dump() for c in r.sources]]
            rows.append({"q": q, "lang": lang, "expected": expected, "got": keys, "detected": r.detected_language,
                         "answer_lang": r.language, "fallback": r.fallback, "mode": r.mode, "ms": r.timings.total_ms,
                         "retrieval_ms": r.timings.retrieval_ms})

    in_scope = [r for r in rows if r["expected"]]
    oos = [r for r in rows if not r["expected"]]
    hit1 = sum(1 for r in in_scope if r["got"][:1] == [r["expected"]]) / len(in_scope)
    hit3 = sum(1 for r in in_scope if r["expected"] in r["got"][:3]) / len(in_scope)
    answered = sum(1 for r in in_scope if not r["fallback"]) / len(in_scope)
    source_acc = sum(1 for r in in_scope if r["got"] and r["got"][0] == r["expected"]) / len(in_scope)
    lang_acc = sum(1 for r in in_scope if r["answer_lang"] == r["lang"]) / len(in_scope)
    detect_acc = sum(1 for r in rows if r["detected"] == r["lang"]) / len(rows)
    fallback_prec = sum(1 for r in oos if r["fallback"]) / len(oos)
    lat = [r["ms"] for r in rows]
    mean_ms, p95 = statistics.mean(lat), sorted(lat)[int(0.95 * (len(lat) - 1))]

    by_lang = {}
    for code in ("en", "ha", "yo", "ig"):
        sub = [r for r in in_scope if r["lang"] == code]
        if sub:
            by_lang[code] = sum(1 for r in sub if r["got"][:1] == [r["expected"]]) / len(sub)

    emb = get_embedder()
    lines = [
        "# Evaluation results (automated gold set)", "",
        f"Embedder: `{emb.name}` | Generation: {'Groq' if rows[0]['mode'] == 'llm' else 'extractive (offline mode)'} | Questions: {len(rows)} ({len(in_scope)} in scope, {len(oos)} out of scope)", "",
        "| Metric | Value |", "|---|---|",
        f"| Retrieval relevance hit@1 | {hit1:.1%} |", f"| Retrieval relevance hit@3 | {hit3:.1%} |",
        f"| Source accuracy (top cited source is the expected entry) | {source_acc:.1%} |",
        f"| In-scope questions answered (not fallback) | {answered:.1%} |",
        f"| Fallback precision on out-of-scope questions | {fallback_prec:.1%} |",
        f"| Language detection accuracy | {detect_acc:.1%} |",
        f"| Answer language accuracy | {lang_acc:.1%} |",
        f"| Mean total latency | {mean_ms:.0f} ms |", f"| p95 total latency | {p95:.0f} ms |", "",
        "## hit@1 by language", "", "| Language | hit@1 |", "|---|---|",
        *[f"| {k} | {v:.1%} |" for k, v in by_lang.items()], "",
        "## Per question", "", "| Question | Lang | Expected | Top result | Detected | Mode | ms |", "|---|---|---|---|---|---|---|",
        *[f"| {r['q']} | {r['lang']} | {r['expected'] or 'out of scope'} | {r['got'][0] if r['got'] else ('fallback' if r['fallback'] else '-')} | {r['detected']} | {r['mode']} | {r['ms']} |" for r in rows],
    ]
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:16]))
    print(f"\nWritten to {args.out}")


if __name__ == "__main__":
    main()
