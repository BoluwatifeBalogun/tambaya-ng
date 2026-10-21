"""Groq client behaviour against a mock HTTP transport: request shape, JSON parsing, model fallback,
parameter degradation on 400, rate-limit retry, and graceful failure. No network or key needed."""
from __future__ import annotations

import json

import httpx
import pytest

from app.config import get_settings
from app.services import generation as gen
from app.services.retrieval import Retrieved


@pytest.fixture
def groq_settings(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "groq_api_key", "gsk_test_key")
    monkeypatch.setattr(s, "groq_model", "openai/gpt-oss-120b")
    monkeypatch.setattr(s, "groq_fallback_model", "openai/gpt-oss-20b")
    return s


def ctx():
    return [Retrieved(entry_id="1", entry_key="pp-fees", language_code="en", section_title="Fees", question_text="How much is a passport?",
                      answer_text="32-page 5-year ₦100,000; 64-page 10-year ₦200,000.", document_title="NIS fees",
                      source_url="https://immigration.gov.ng", last_verified="2026-10-20", domain_slug="passport",
                      domain_name="Passport", agency_name="NIS")]


def completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": content}}]})


GOOD = json.dumps({"answer": "A 32-page passport costs ₦100,000 [1].", "cited": [1], "needs_official_action": True,
                   "official_channel": "passport.immigration.gov.ng", "insufficient": False, "confidence": 0.9})


def test_request_shape_and_successful_parse(groq_settings):
    seen = []
    def handler(request: httpx.Request):
        seen.append(request)
        return completion(GOOD)
    client = gen.GroqClient(transport=httpx.MockTransport(handler))
    out = client.generate("How much is a passport?", "en", ctx(), [])
    assert out and out.mode == "llm" and out.cited == [1] and "₦100,000" in out.answer
    req = seen[0]
    assert str(req.url) == gen.GROQ_URL
    assert req.headers["authorization"] == "Bearer gsk_test_key"
    body = json.loads(req.content)
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["response_format"] == {"type": "json_object"}
    assert body["reasoning_effort"] == "low"
    assert body["messages"][0]["role"] == "system" and "Answer ONLY from the numbered CONTEXT" in body["messages"][0]["content"]
    assert "[1] (NIS; NIS fees" in body["messages"][1]["content"]
    assert client.last_model == "openai/gpt-oss-120b"


def test_falls_back_to_second_model_on_404(groq_settings):
    models = []
    def handler(request):
        body = json.loads(request.content); models.append(body["model"])
        if body["model"] == "openai/gpt-oss-120b":
            return httpx.Response(404, json={"error": {"message": "model_not_found"}})
        return completion(GOOD)
    client = gen.GroqClient(transport=httpx.MockTransport(handler))
    assert client.generate("q", "en", ctx(), []) is not None
    assert models == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"] and client.last_model == "openai/gpt-oss-20b"


def test_400_drops_optional_params_then_succeeds(groq_settings):
    bodies = []
    def handler(request):
        body = json.loads(request.content); bodies.append(body)
        if "reasoning_effort" in body or "response_format" in body:
            return httpx.Response(400, json={"error": {"message": "unsupported parameter"}})
        return completion("Here you go:\n```json\n" + GOOD + "\n```")  # prose + fenced JSON still parses
    client = gen.GroqClient(transport=httpx.MockTransport(handler))
    out = client.generate("q", "en", ctx(), [])
    assert out is not None and out.cited == [1]
    assert "reasoning_effort" not in bodies[-1] and "response_format" not in bodies[-1]


def test_429_is_retried(groq_settings, monkeypatch):
    monkeypatch.setattr(gen.time, "sleep", lambda s: None)
    calls = {"n": 0}
    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "1"}, json={"error": {"message": "rate limit"}})
        return completion(GOOD)
    client = gen.GroqClient(transport=httpx.MockTransport(handler))
    assert client.generate("q", "en", ctx(), []) is not None and calls["n"] == 2


@pytest.mark.parametrize("response", [
    httpx.Response(401, json={"error": {"message": "invalid api key"}}),
    httpx.Response(500, text="upstream error"),
    completion("I think a passport costs about ₦100,000."),            # not JSON at all
    completion(json.dumps({"cited": [1]})),                            # JSON without an answer
    httpx.Response(200, json={"unexpected": True}),                    # malformed envelope
])
def test_failures_return_none_so_pipeline_serves_verified_entry(groq_settings, response):
    client = gen.GroqClient(transport=httpx.MockTransport(lambda r: response))
    assert client.generate("q", "en", ctx(), []) is None
    assert client.last_error


def test_network_timeout_returns_none(groq_settings):
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)
    client = gen.GroqClient(transport=httpx.MockTransport(handler))
    assert client.generate("q", "en", ctx(), []) is None and "ReadTimeout" in client.last_error


def test_citations_are_sanitised(groq_settings):
    bad = json.dumps({"answer": "x" * 30, "cited": [1, 7, "2", None, "abc"], "needs_official_action": False,
                      "official_channel": None, "insufficient": False, "confidence": "high"})
    client = gen.GroqClient(transport=httpx.MockTransport(lambda r: completion(bad)))
    out = client.generate("q", "en", ctx(), [])
    assert out.cited == [1] and out.confidence == 0.85  # "high" is understood


def test_rewrite_query_parses_language_and_query(groq_settings):
    client = gen.GroqClient(transport=httpx.MockTransport(lambda r: completion('{"query": "passport fee", "language": "ha"}')))
    assert client.rewrite_query("Nawa ne kuɗin fasfo?", []) == {"query": "passport fee", "language": "ha"}


def test_disabled_without_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "groq_api_key", "")
    client = gen.GroqClient()
    assert not client.available and client.generate("q", "en", ctx(), []) is None


def test_end_to_end_pipeline_with_mocked_groq(client, groq_settings, monkeypatch):
    def handler(request):
        body = json.loads(request.content)
        system = body["messages"][0]["content"]
        if system.startswith("You rewrite"):
            return completion('{"query": "Nigerian passport fee", "language": "ha"}')
        user = body["messages"][1]["content"]
        assert "[1]" in user and "CONTEXT" in user
        return completion(json.dumps({"answer": "Littafi mai shafi 32 na shekaru 5 ₦100,000; mai shafi 64 na shekaru 10 ₦200,000 [1].",
                                      "cited": [1], "needs_official_action": True, "official_channel": "passport.immigration.gov.ng",
                                      "insufficient": False, "confidence": 0.9}))
    monkeypatch.setattr(gen, "_llm", gen.GroqClient(transport=httpx.MockTransport(handler)))
    r = client.post("/api/chat", json={"message": "Nawa ne kuɗin fasfo?", "language": "auto"})
    d = r.json()
    assert d["mode"] == "llm", d["checks"]
    assert d["retrieval_query"] == "Nigerian passport fee"
    assert d["sources"][0]["entry_key"] == "pp-fees" and "numbers_grounded" in d["checks"]
    monkeypatch.setattr(gen, "_llm", None)


def test_string_booleans_and_odd_fields_are_parsed_correctly(groq_settings):
    """bool("false") is True in Python: string booleans must not turn every answer into a refusal."""
    odd = json.dumps({"answer": "Enrolment is free at NIMC centres [1].", "cited": ["[1]"], "needs_official_action": "true",
                      "official_channel": "null", "insufficient": "false", "confidence": "90%"})
    client = gen.GroqClient(transport=httpx.MockTransport(lambda r: completion(odd)))
    out = client.generate("q", "en", ctx(), [])
    assert out.insufficient is False and out.needs_official_action is True
    assert out.cited == [1] and out.confidence == 0.9 and out.official_channel is None


def test_missing_cited_list_falls_back_to_markers(groq_settings):
    j = json.dumps({"answer": "It costs ₦100,000 [1].", "insufficient": False, "confidence": 0.8})
    client = gen.GroqClient(transport=httpx.MockTransport(lambda r: completion(j)))
    assert client.generate("q", "en", ctx(), []).cited == [1]


@pytest.mark.parametrize("raw,expected", [(0.7, 0.7), (85, 0.85), ("high", 0.85), ("low", 0.3), ("0.4", 0.4), (None, 0.5), (True, 0.5)])
def test_confidence_parsing(raw, expected):
    assert gen._parse_confidence(raw) == pytest.approx(expected)


def test_greetings_with_trailing_words_get_a_conversational_reply(client):
    for msg in ["hi, guy", "Hello there!", "good morning sir", "thanks!"]:
        d = client.post("/api/chat", json={"message": msg, "language": "en"}).json()
        assert not d["fallback"] and d["mode"] == "chat" and d["sources"] == [], msg
    d = client.post("/api/chat", json={"message": "hi, how do I get NIN?", "language": "en"}).json()
    assert d["sources"][0]["entry_key"] == "nin-enrol-steps"


def test_how_do_i_get_my_nin_is_enrolment_not_slip(client):
    d = client.post("/api/chat", json={"message": "how do i get my nin", "language": "en"}).json()
    assert d["sources"][0]["entry_key"] == "nin-enrol-steps"


def test_model_format_slip_serves_verified_entry_not_refusal(client, groq_settings, monkeypatch):
    def handler(request):
        body = json.loads(request.content)
        if body["messages"][0]["content"].startswith("You rewrite"):
            return completion('{"query": "how to get a NIN", "language": "en"}')
        return completion(json.dumps({"answer": "Visit a NIMC centre.", "cited": [], "insufficient": False, "confidence": 0.9}))
    monkeypatch.setattr(gen, "_llm", gen.GroqClient(transport=httpx.MockTransport(handler)))
    d = client.post("/api/chat", json={"message": "how do i get my nin", "language": "en"}).json()
    assert not d["fallback"] and d["mode"] == "extractive" and "FAILED:no_citations" in d["checks"]
    monkeypatch.setattr(gen, "_llm", None)


def test_diagnose_endpoint_reports_each_stage(client):
    assert client.get("/api/admin/diagnose", params={"q": "hi"}).status_code == 401
    d = client.get("/api/admin/diagnose", params={"q": "how do i get my nin", "token": "dev-admin-token"}).json()
    assert d["retrieval"]["grounded"] and d["retrieval"]["results"][0]["entry_key"] == "nin-enrol-steps"
    assert d["outcome"].startswith("extractive: no GROQ_API_KEY")


def test_pidgin_llm_answer_passes_verification(client, groq_settings, monkeypatch):
    """A Pidgin answer reuses English words; the language check must not reject it as English."""
    def handler(request):
        body = json.loads(request.content)
        if body["messages"][0]["content"].startswith("You rewrite"):
            return completion('{"query": "passport fee", "language": "pcm"}')
        assert "Nigerian Pidgin" in body["messages"][0]["content"]
        return completion(json.dumps({
            "answer": "For Nigeria, 32-page passport wey get 5-year validity na ₦100,000, and the 64-page own wey get 10 years na ₦200,000 [1]. Na online you go pay am.",
            "cited": [1], "needs_official_action": True, "official_channel": "passport.immigration.gov.ng",
            "insufficient": False, "confidence": 0.9}))
    monkeypatch.setattr(gen, "_llm", gen.GroqClient(transport=httpx.MockTransport(handler)))
    d = client.post("/api/chat", json={"message": "How much be passport now?", "language": "auto"}).json()
    assert d["language"] == "pcm" and d["mode"] == "llm", d["checks"]
    assert "language_matches" in d["checks"]
    monkeypatch.setattr(gen, "_llm", None)
