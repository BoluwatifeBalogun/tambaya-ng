"""Regression guard: the full audit bank (scripts/audit_bank.py) must keep passing."""
from scripts.audit import expected_ok, run


def test_audit_bank_all_pass():
    results = run(False)
    failures = [(cat, q, expected, keys[:2], err) for cat, q, _l, expected, keys, _d, _a, fallback, _ms, err in results
                if not (err is None and expected_ok(expected, keys, fallback))]
    assert not failures, f"{len(failures)} audit failures, e.g. {failures[:5]}"


def test_audit_bank_language_detection():
    results = run(False)
    wrong = [(q, lang_expected, detected) for _c, q, lang_expected, expected, _k, detected, _a, _f, _ms, err in results
             if lang_expected and expected is not None and err is None and detected != lang_expected]
    assert not wrong, wrong[:10]
