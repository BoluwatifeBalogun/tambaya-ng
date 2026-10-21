"""Run the audit bank through the live pipeline and report every failure, grouped by category.

Usage (from backend/):  python -m scripts.audit [--verbose] [--out ../docs/audit-results.md]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal  # noqa: E402
from app.services import pipeline  # noqa: E402
from scripts import audit_bank as B  # noqa: E402


def expected_ok(expected, got_keys: list[str], fallback: bool) -> bool:
    if expected is None:
        return fallback
    if expected == "smalltalk":
        return got_keys == ["smalltalk"]
    if expected.startswith("domain:"):
        return bool(got_keys) and got_keys[0].startswith(expected.split(":")[1] + "-")
    return bool(got_keys) and got_keys[0] == expected


def run(verbose: bool):
    results = []  # (category, question, lang_expected, expected, got_keys, detected, answer_lang, fallback, ms, error)
    with SessionLocal() as db:
        def one(cat, q, expected, lang_expected, cid=None, uid=None):
            try:
                r = pipeline.answer(db, q, "auto", cid, uid)
                keys = ["smalltalk"] if r.mode == "chat" else [s.entry_key for s in r.sources]
                results.append((cat, q, lang_expected, expected, keys, r.detected_language, r.language, r.fallback, r.timings.total_ms, None))
                return r
            except pipeline.ValidationError as e:
                results.append((cat, q, lang_expected, expected, [], "-", "-", True, 0, f"validation: {e}"))
            except Exception as e:  # any crash is a bug
                db.rollback()
                results.append((cat, q, lang_expected, expected, [], "-", "-", False, 0, f"CRASH {type(e).__name__}: {e}"))
            return None

        for lang, bank in (("en", B.EN), ("ha", B.HA), ("yo", B.YO), ("ig", B.IG)):
            for key, qs in bank.items():
                for q in qs:
                    one(lang, q, key, lang)
        for q, key in B.PIDGIN:
            one("pidgin", q, key, "pcm")
        for q, key in B.CODE_SWITCHED:
            one("code-switched", q, key, None)
        for q, key in B.TYPOS:
            one("typos", q, key, None)
        for chain in B.CHAINS:
            cid = uid = None
            for q, key in chain:
                r = one("chains", q, key, None, cid, uid)
                if r:
                    cid, uid = r.conversation_id, r.user_id
        for q in B.OOS:
            one("out-of-scope", q, None, None)
        for q, key in B.ADVERSARIAL:
            one("adversarial", q, key, None)
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "docs" / "audit-results.md"))
    args = ap.parse_args()
    results = run(args.verbose)

    total, passed = len(results), 0
    by_cat_total, by_cat_pass = Counter(), Counter()
    lang_total = lang_ok = 0
    failures = defaultdict(list)
    for cat, q, lang_expected, expected, keys, detected, answer_lang, fallback, ms, err in results:
        ok = err is None and expected_ok(expected, keys, fallback)
        by_cat_total[cat] += 1
        if ok:
            passed += 1; by_cat_pass[cat] += 1
        else:
            failures[cat].append((q, expected, keys[:3], detected, fallback, err))
        if lang_expected and expected is not None and err is None:
            lang_total += 1
            lang_ok += detected == lang_expected
            if detected != lang_expected:
                failures["language-detection"].append((q, lang_expected, [detected], detected, fallback, None))
    lat = sorted(r[8] for r in results if r[9] is None)
    lines = [f"# Audit results", "", f"Questions: {total} | Passed: {passed} ({passed/total:.1%}) | Language detection: {lang_ok}/{lang_total} ({(lang_ok/lang_total if lang_total else 0):.1%}) | Latency mean {sum(lat)/len(lat):.0f} ms, p95 {lat[int(0.95*(len(lat)-1))]} ms", "",
             "| Category | Passed | Total |", "|---|---|---|"]
    for cat in by_cat_total:
        lines.append(f"| {cat} | {by_cat_pass[cat]} | {by_cat_total[cat]} |")
    lines += ["", "## Failures", ""]
    for cat, items in failures.items():
        lines.append(f"### {cat} ({len(items)})")
        for q, expected, got, detected, fallback, err in items:
            lines.append(f"- `{q}` → expected **{expected}**, got {got or ('fallback' if fallback else '-')} (detected {detected}){' ' + err if err else ''}")
        lines.append("")
    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
