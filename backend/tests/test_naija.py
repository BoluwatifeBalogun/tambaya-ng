"""Regression tests for the 'average Nigerian speech' audit: Pidgin, SMS spellings, small talk, misuse refusals,
lost passports and topic switches in follow-ups."""
import pytest

from app.services.language import detect_language, normalise_sms
from app.services.retrieval import match_intent_rule
from app.services.smalltalk import classify
from scripts.audit_naija import DIALOGUES, SINGLE, expected_ok, run


def chat(client, message, cid=None, uid=None, language="auto"):
    r = client.post("/api/chat", json={"message": message, "language": language, "conversation_id": cid, "user_id": uid})
    assert r.status_code == 200, r.text
    return r.json()


def test_full_naija_audit_passes():
    rows = run()
    bad = [(cat, msg, exp, keys[:2], lang, got_lang) for cat, msg, exp, lang, keys, got_lang, fb, _ms, err in rows
           if err or not expected_ok(exp, keys, fb) or (lang and got_lang != lang)]
    assert not bad, f"{len(bad)} failures, e.g. {bad[:5]}"
    assert len(rows) == sum(len(v) for v in SINGLE.values()) + sum(len(v) for v in DIALOGUES.values())


@pytest.mark.parametrize("text,lang", [
    ("Abeg how person fit get NIN?", "pcm"), ("Wetin be NIN sef?", "pcm"), ("My passport don loss", "pcm"),
    ("How long passport dey take?", "pcm"), ("pls hw do i get my nin", "en"), ("abeg how do i renew my passport", "en"),
    ("I don't have a birth certificate", "en"), ("Where do I go to renew my passport?", "en"),
    ("Nawa ne kudin passport?", "ha"), ("Bawo ni mo se le gba NIN slip?", "yo"), ("Kedu ka m ga-esi nweta NIN?", "ig"),
])
def test_language_detection_with_pidgin(text, lang):
    assert detect_language(text).language == lang


def test_sms_normalisation_rewrites_in_place():
    assert normalise_sms("pls hw much is d pasport") == "please how much is the passport"
    assert normalise_sms("i 4got my nin") == "i forgot my nin"


@pytest.mark.parametrize("text,kind,lang", [
    ("hi, guy", "greet", "en"), ("how far", "howareyou", "pcm"), ("no wahala", "ack", "pcm"), ("thank you o", "thanks", "pcm"),
    ("Na gode", "thanks", "ha"), ("Ẹ káàárọ̀", "greet", "yo"), ("Daalụ", "thanks", "ig"), ("👍", "ack", "en"), ("ok bye o", "bye", "pcm"),
])
def test_smalltalk_classification(text, kind, lang):
    c = classify(text)
    assert c and c.kind == kind and c.language == lang


@pytest.mark.parametrize("text", ["hi, how do I get NIN?", "how far is the passport office", "Is it free?", "Good morning, I need help"])
def test_questions_are_not_smalltalk(text):
    assert classify(text) is None


@pytest.mark.parametrize("text", ["How can I get a fake NIN?", "help me make fake birth certificate", "How I go get licence without test?",
                                  "Can I use my brother's NIN to register my SIM?", "can i get two NINs", "takardar haihuwa ta jabu"])
def test_misuse_is_refused(text):
    assert match_intent_rule(text)[0] == "gen-misuse"


@pytest.mark.parametrize("text", ["how do I report a fake NIMC website", "an officer asked me for a bribe",
                                  "How do I change my date of birth on NIN?", "where can I buy a passport booklet form"])
def test_legitimate_questions_are_not_refused(text):
    rule = match_intent_rule(text)
    assert rule is None or rule[0] != "gen-misuse"


def test_smalltalk_is_instant_localised_and_skipped_by_followups(client):
    d1 = chat(client, "how far")
    assert d1["mode"] == "chat" and d1["language"] == "pcm" and d1["sources"] == [] and not d1["fallback"]
    d2 = chat(client, "abeg how person fit get NIN?", d1["conversation_id"], d1["user_id"])
    assert d2["language"] == "pcm" and d2["sources"][0]["entry_key"] == "nin-enrol-steps"
    d3 = chat(client, "no wahala", d1["conversation_id"], d1["user_id"])
    assert d3["mode"] == "chat"
    d4 = chat(client, "e free?", d1["conversation_id"], d1["user_id"])
    assert d4["sources"][0]["entry_key"] == "nin-cost"


def test_topic_switch_carries_intent_not_topic(client):
    d1 = chat(client, "How much is passport?")
    d2 = chat(client, "and driver's licence?", d1["conversation_id"], d1["user_id"])
    assert d2["sources"][0]["entry_key"] == "dl-fees"


def test_neutral_ack_keeps_conversation_language(client):
    d1 = chat(client, "Nawa ne kuɗin lasisin tuƙi?")
    d2 = chat(client, "ok", d1["conversation_id"], d1["user_id"])
    assert d2["language"] == "ha" and d2["mode"] == "chat"


def test_lost_passport_answered_in_every_language(client):
    for msg, lang in [("I lost my passport", "en"), ("My passport don loss", "pcm"), ("Fasfona ya ɓace", "ha"),
                      ("Pásípọ̀ọ̀tù mi sọnù", "yo"), ("Paspọtụ m furu efu", "ig")]:
        d = chat(client, msg)
        assert d["sources"][0]["entry_key"] == "pp-lost" and d["language"] == lang, msg
        assert d["sources"][0]["language"] == lang, msg


def test_pidgin_answer_comes_from_the_pidgin_knowledge_base(client):
    d = chat(client, "How much be passport now?")
    assert d["language"] == "pcm" and d["sources"][0]["language"] == "pcm"
    assert "₦100,000" in d["answer"] and "wey" in d["answer"]


def test_pidgin_can_be_forced_from_the_language_switch(client):
    d = chat(client, "How do I renew my driver's licence?", language="pcm")
    assert d["language"] == "pcm" and d["sources"][0]["entry_key"] == "dl-renewal" and d["sources"][0]["language"] == "pcm"


def test_office_hours_are_not_guessed(client):
    assert chat(client, "What time does NIMC office close?")["fallback"] is True
