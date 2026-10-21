"""Unit tests (report §3.20 'Unit Testing'): language handling, glossary, fusion, embeddings."""
from app.services import embeddings as emb
from app.services.language import build_offline_retrieval_query, detect_language, glossary_normalise, looks_like_followup
from app.services.retrieval import Retrieved, rrf_fuse


def test_detects_hausa_from_lexicon_and_hooked_letters():
    d = detect_language("Nawa ne kuɗin fasfo?")
    assert d.language == "ha" and d.confidence >= 0.6


def test_detects_yoruba_and_igbo():
    assert detect_language("Èló ni ìwé-àṣẹ awakọ̀?").language == "yo"
    assert detect_language("Kedu ka m ga-esi nweta NIN?").language == "ig"


def test_detects_english_and_pidgin_separately():
    assert detect_language("How do I renew my passport?").language == "en"
    assert detect_language("Abeg how much be passport now?").language == "pcm"
    assert detect_language("Wetin I need carry go NIMC office?").language == "pcm"
    # Nigerian English with softeners or "I don't" / "I go to" stays English
    assert detect_language("abeg how do i renew my passport").language == "en"
    assert detect_language("I don't have a birth certificate").language == "en"
    assert detect_language("Where do I go to renew my passport?").language == "en"
    assert detect_language("pls hw do i get my nin").language == "en"


def test_glossary_expands_whole_words_only():
    q = glossary_normalise("Nawa ne kuɗin fasfo?")
    assert "passport" in q and "how much" in q
    assert "costn" not in q  # no mid-word replacement


def test_offline_query_appends_previous_turn_for_followups():
    q = build_offline_retrieval_query("how much does it cost?", "en", ["NIN date of birth modification"])
    assert "fee" in q and "NIN date of birth modification" in q
    assert looks_like_followup("nawa ne?", "ha")
    assert not looks_like_followup("What documents do I need to apply for an international passport in Nigeria", "en")


def test_local_embedder_is_deterministic_and_unit_norm():
    a = emb.local_embed("How do I get a NIN?", 768)
    b = emb.local_embed("How do I get a NIN?", 768)
    assert a == b and len(a) == 768
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_local_embedder_similarity_orders_paraphrases_above_unrelated():
    dot = lambda x, y: sum(p * q for p, q in zip(x, y))
    base = emb.local_embed("How much does a passport cost?", 768)
    para = emb.local_embed("Passport fee and cost in Nigeria", 768)
    other = emb.local_embed("Recipe for jollof rice with chicken", 768)
    assert dot(base, para) > dot(base, other)


def _r(key, lang="en", domain="nin", dense=0.0, lex=0.0):
    return Retrieved(entry_id=key + lang, entry_key=key, language_code=lang, section_title="", question_text="",
                     answer_text="", document_title="", source_url="", last_verified=None, domain_slug=domain,
                     domain_name="", agency_name="", dense_score=dense, lexical_score=lex)


def test_rrf_fuses_both_legs_and_dedupes_sibling_languages():
    dense = [_r("a", dense=0.5), _r("b", dense=0.4), _r("a", "ha", dense=0.45)]
    lexical = [_r("b", lex=0.9), _r("c", lex=0.5)]
    out = rrf_fuse(dense, lexical, "nin", 5)
    keys = [o.entry_key for o in out]
    assert keys[0] == "b"  # appears in both legs
    assert keys.count("a") == 1  # Hausa sibling collapsed into one fact
