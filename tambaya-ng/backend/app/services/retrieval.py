"""RAG retrieval layer (report §3.14.1 and §2.5.2 items 5 to 7): hybrid dense + lexical search over
PostgreSQL/pgvector fused with Reciprocal Rank Fusion, plus soft domain routing."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from .embeddings import get_embedder

RRF_K = 60
DOMAIN_BOOST = 0.004  # about a quarter of one RRF rank step (1/61 - 1/62); a tie-breaker, never a filter
OUT_OF_SCOPE = "out_of_scope"

# Rule layer for meta intents. Matched before retrieval; pins the top entry (still a verified KB entry).
INTENT_RULES: list[tuple[re.Pattern, str, str]] = [
    # greetings / help
    (re.compile(r"^\W*(hi|hey|hello|helo|hallo|good (morning|afternoon|evening|day)|greetings|sannu|ina kwana|ina wuni|barka( da \w+)?|ẹ n lẹ́?|e n le|ẹ káàárọ̀|e kaaro|ẹ káàsán|e kaasan|ẹ káalẹ́|ndewo|kedu|ụtụtụ ọma|ututu oma|good day o?)\W*$", re.I), "gen-what-can-you-do", "general"),
    (re.compile(r"^\W*(help|taimako|ìrànlọ́wọ́|iranlowo|enyemaka|menu|start|what can you do|me za ka iya yi|kí ni o lè ṣe|kini o le se|gịnị ka ị nwere ike ime|what (do you|can you) (do|cover|help)|what services (do|can) you|which services do you|who are you|what is tambaya( ng)?|menene tambaya( ng)?|kini tambaya( ng)?|gịnị bụ tambaya( ng)?)\b.*$", re.I), "gen-what-can-you-do", "general"),
    # capability / boundary: "can you ... for me", "check my status", "apply on my behalf"
    (re.compile(r"\b(can|could|will|would) you\b.*\b(apply|enrol|enroll|register|book|check|verify|look ?up|process|pay|issue|get|do it|renew|track)\b", re.I), "gen-boundary", "general"),
    (re.compile(r"\b(on my behalf|for me\b.*\?|do you process|are you (a )?government|are you nimc|are you immigration|are you frsc|madadina|za ka iya (duba|neman|yin|ɗauko|dauko|biya)|kana sarrafa|ṣé o lè|se o le|ị nwere ike i?(rịọ|lelee|debanye)|i nwere ike i?(rio|lelee|debanye))", re.I), "gen-boundary", "general"),
    # misuse: fake documents, skipping capture/tests, bribes, someone else's identity, falsifying age.
    # Refused with the legitimate route (gen-misuse). Placed before the identifier rule.
    (re.compile(r"\b(fake|forged?|forging|counterfeit|bogus|jabu|bogi|ayederu|ayédèrú|adịgboroja|adigboroja)\W+(\w+\W+){0,2}"
                r"(nin|passport|licen[cs]e|lasisi\w*|fasfo\w*|birth|certificate|cert|document|slip|id|paper|takard\w*|ìwé|iwe|akwụkwọ|akwukwo|paspọtụ|pásípọ̀ọ̀tù)\b|"
                r"\b(nin|passport|licen[cs]e|lasisi\w*|fasfo\w*|certificate|takard\w*|ìwé|iwe|akwụkwọ|paspọtụ)\b(\W+\w+){0,4}\W+(na )?(jabu|bogi|ayederu|ayédèrú|adịgboroja|adigboroja)\b|"
                r"\b(licen[cs]e|lasisi\w*|passport|fasfo\w*|nin)\b.{0,40}\b(without|no|ba tare da|láì|laisi|láìsí|na-enweghị|na-enweghi)\W+"
                r"(\w+\W+){0,2}(capture|biometrics?|test|driving test|testing|driving school|gwaji|ìdánwò|idanwo|ule|ɗaukar|daukar)\b|"
                r"\b(buy|purchase|sell|sayi|saya|ra)\W+(\w+\W+){0,2}(nin|passport|licen[cs]e|birth certificate|lasisi\w*|fasfo\w*)\b(?!.{0,20}\b(booklet|form|fee|online)\b)|"
                r"\b(how (do|can|will|should) i|make i|i wan|let me|should i|can i|help me)\W+(\w+\W+){0,2}(bribe|settle|grease|egunje|tip)\b|"
                r"\b(use|using|register with|enrol with|enroll with|collect)\W+(\w+\W+){0,1}(someone else'?s?|another person'?s?|other person'?s?|"
                r"another person|person|my (brother|sister|friend|father|mother|papa|mama|uncle|cousin|wife|husband)'?s?)\W+(nin|passport|licen[cs]e|bvn|identity|id)\b|"
                r"\b(pay|give|settle)\W+(\w+\W+){0,1}(person|someone|somebody|agent|man|guy)\b.{0,40}\b(bring|deliver|carry)\b.{0,30}\b(licen[cs]e|passport|nin|slip)\b|"
                r"\b(two|2|second|another|extra|multiple|more than one) nins?\b|\bnins? (two|2) times\b|"
                r"\b(reduce|lower|cut|increase|shave|remove)\W+(\w+\W+){0,1}(age|years|date of birth|dob)\b|\b(look|be|appear) younger\b", re.I),
     "gen-misuse", "general"),
    # identifiers shared or requested: never validate, never look up
    (re.compile(r"\b\d{11}\b|\b[A-Z]\d{8}\b|\b(someone else'?s?|another person'?s?|other people'?s?) (nin|passport|licen[cs]e|bvn)|"
                r"\b(check|verify|confirm|look ?up|validate) (my|his|her|their) (nin|passport|licen[cs]e|bvn)\b.{0,20}\b(status|number|valid)", re.I), "gen-boundary", "general"),
]

# Misuse is checked before everything else: "help me make a fake birth certificate" must not read as a help request.
INTENT_RULES.sort(key=lambda r: r[1] != "gen-misuse")

# Terms that mark a question as outside the four services even when it shares a domain word.
OOS_TERMS = re.compile(r"\b(visa|visas|usa|uk|canada|america|london|schengen|international driving permit|idp|bvn|cac|company registration|"
                       r"jamb result|cutoff|voter'?s? card|inec|pvc|tax identification|tin\b|firs|electricity|nepa|phcn|fuel|petrol|"
                       r"vehicle papers|number plate|road worthiness|insurance|land|plot|rent|weather|football|premier league|bank account|open a bank|"
                       r"super eagles|recipe|jollof|joke|poem|song|translate|capital of|president|governor|salary|loan|crypto|election|"
                       r"public holiday)\b", re.I)
# Questions the knowledge base never answers even when they name an agency (office hours change by office).
HARD_OOS = re.compile(r"\b(opening hours|closing time|working hours|office hours|what time (does|do|is|will)|"
                      r"(open|work|working) on (saturday|sunday|weekends?)|close (today|on)|resumption time|waec|neco|jamb (form|result|registration)|"
                      r"exam result|post ?utme|nysc|scholarship)\b", re.I)


@dataclass
class Retrieved:
    entry_id: str
    entry_key: str
    language_code: str
    section_title: str
    question_text: str
    answer_text: str
    document_title: str
    source_url: str
    last_verified: str | None
    domain_slug: str
    domain_name: str
    agency_name: str
    dense_score: float = 0.0
    lexical_score: float = 0.0
    fused_score: float = 0.0
    ranks: dict[str, int] = field(default_factory=dict)


_BASE_SELECT = """
SELECT ke.entry_id::text, ke.entry_key, l.language_code, ke.section_title, ke.question_text, ke.answer_text,
       kd.title AS document_title, kd.source_url, kd.last_verified::text, sd.slug AS domain_slug,
       sd.domain_name, coalesce(a.agency_name, '') AS agency_name
FROM knowledge_entry ke
JOIN language l ON l.language_id = ke.language_id
JOIN knowledge_document kd ON kd.document_id = ke.document_id
JOIN service_domain sd ON sd.domain_id = kd.domain_id
LEFT JOIN agency a ON a.agency_id = sd.agency_id
WHERE ke.is_active AND ke.review_status = 'approved' AND kd.is_active AND l.language_code = ANY(:langs)
"""


def _row_to_retrieved(row) -> Retrieved:
    return Retrieved(
        entry_id=row[0], entry_key=row[1], language_code=row[2], section_title=row[3] or "",
        question_text=row[4], answer_text=row[5], document_title=row[6], source_url=row[7] or "",
        last_verified=row[8], domain_slug=row[9], domain_name=row[10], agency_name=row[11],
    )


def dense_search(db: Session, query_vec: list[float], langs: list[str], limit: int) -> list[Retrieved]:
    vec_literal = "[" + ",".join(f"{x:.7f}" for x in query_vec) + "]"
    sql = text(_BASE_SELECT + """
      AND ke.embedding_vector IS NOT NULL
    ORDER BY ke.embedding_vector <=> CAST(:qvec AS vector)
    LIMIT :lim
    """)
    rows = db.execute(sql, {"langs": langs, "qvec": vec_literal, "lim": limit}).fetchall()
    out = [_row_to_retrieved(r) for r in rows]
    if out:
        sim_sql = text(
            "SELECT entry_id::text, 1 - (embedding_vector <=> CAST(:qvec AS vector)) FROM knowledge_entry "
            "WHERE entry_id = ANY(CAST(:ids AS uuid[]))"
        )
        sims = dict(db.execute(sim_sql, {"qvec": vec_literal, "ids": [r.entry_id for r in out]}).fetchall())
        for r in out:
            r.dense_score = float(sims.get(r.entry_id, 0.0))
    return out


_STOP = {
    # English
    "the", "is", "are", "a", "an", "of", "to", "for", "in", "on", "and", "or", "do", "does", "i", "my", "me", "you",
    "it", "its", "this", "that", "what", "how", "where", "when", "can", "need", "get", "with", "now", "please", "about",
    "there", "be", "was", "were", "have", "has", "will", "would", "should", "much", "many", "which", "who", "am",
    # Hausa / Yoruba / Igbo function words
    "ne", "ce", "na", "ta", "da", "don", "kuma", "ko", "ba", "ya", "yi", "zan", "zai", "ina", "ake", "ana", "nake",
    "ni", "mo", "ṣe", "se", "kí", "ki", "fún", "fun", "sí", "si", "tí", "ti", "ló", "lo", "ka", "m", "gị", "gi", "ga",
    "nke", "ya", "esi", "ihe", "bụ", "bu",
}


def _lexical_or_query(q: str) -> str:
    """OR-query over significant tokens so partial matches rank instead of failing the AND that
    websearch_to_tsquery produces under the 'simple' configuration (which keeps stopwords)."""
    # The 'simple' parser splits "driver's" into "driver" + "s", so split on apostrophes here too.
    toks = re.findall(r"[\wɓɗƙƴẹọṣịụṅ\-]+", re.sub(r"['ʼ’]", " ", q.lower()))
    keep: list[str] = []
    for t in toks:
        t = t.strip("-")
        if len(t) < 3 and not t.isdigit() and t not in {"nin", "id", "hi"}:
            continue
        if t in _STOP or t in keep:
            continue
        keep.append(t)
    return " | ".join(f"'{t}'" for t in keep[:24])


def lexical_search(db: Session, query: str, langs: list[str], limit: int) -> list[Retrieved]:
    tsq = _lexical_or_query(query)
    if not tsq:
        return []
    sql = text(_BASE_SELECT + """
      AND ke.search_vector @@ to_tsquery('simple', :q)
    ORDER BY ts_rank_cd('{0.05,0.15,0.4,1.0}', ke.search_vector, to_tsquery('simple', :q), 32) DESC
    LIMIT :lim
    """)
    rows = db.execute(sql, {"langs": langs, "q": tsq, "lim": limit}).fetchall()
    out = [_row_to_retrieved(r) for r in rows]
    if out:
        rank_sql = text(
            "SELECT entry_id::text, ts_rank_cd('{0.05,0.15,0.4,1.0}', search_vector, to_tsquery('simple', :q), 32) FROM knowledge_entry "
            "WHERE entry_id = ANY(CAST(:ids AS uuid[]))"
        )
        ranks = dict(db.execute(rank_sql, {"q": tsq, "ids": [r.entry_id for r in out]}).fetchall())
        for r in out:
            r.lexical_score = float(ranks.get(r.entry_id, 0.0))
    return out


def trigram_search(db: Session, query: str, langs: list[str], limit: int) -> list[Retrieved]:
    """Phrase-match leg: pg_trgm similarity of the message against EACH stored phrasing (question_text and
    every alt_question) individually. Near-exact phrasings score close to 1 and can pin the result; it also
    gives typo tolerance ("pasport fee")."""
    q = re.sub(r"\s+", " ", query.lower().strip())[:200]
    if not q:
        return []
    sql = text("""
    WITH phr AS (
      SELECT ke.entry_id, max(similarity(lower(unaccent(p)), lower(unaccent(:q)))) AS sim
      FROM knowledge_entry ke
      JOIN language l ON l.language_id = ke.language_id,
      LATERAL unnest(array_append(coalesce(ke.alt_questions, '{}'), ke.question_text)) AS p
      WHERE ke.is_active AND ke.review_status = 'approved' AND l.language_code = ANY(:langs)
      GROUP BY ke.entry_id
    )
    """ + _BASE_SELECT.replace("SELECT ke.entry_id::text,", "SELECT ke.entry_id::text, phr.sim,").replace(
        "FROM knowledge_entry ke", "FROM knowledge_entry ke JOIN phr ON phr.entry_id = ke.entry_id") + """
      AND phr.sim > 0.25
    ORDER BY phr.sim DESC
    LIMIT :lim
    """)
    try:
        rows = db.execute(sql, {"langs": langs, "q": q, "lim": limit}).fetchall()
    except Exception:
        db.rollback()
        return []
    out = []
    for row in rows:
        r = _row_to_retrieved(row[:1] + row[2:])
        r.lexical_score = float(row[1])
        out.append(r)
    return out


_VOCAB: dict[str, object] = {"tokens": set(), "at": 0.0}


def kb_vocabulary(db: Session) -> set[str]:
    """Tokens of every active entry (all languages), cached for 60 s. Used to spot out-of-vocabulary words
    (likely typos), which is when a fuzzy phrase match deserves to be decisive."""
    import time as _t
    if _VOCAB["tokens"] and _t.time() - _VOCAB["at"] < 60:
        return _VOCAB["tokens"]
    rows = db.execute(text("SELECT lower(unaccent(question_text || ' ' || coalesce(immutable_join(alt_questions),'') || ' ' || answer_text)) "
                           "FROM knowledge_entry WHERE is_active")).fetchall()
    toks: set[str] = set()
    for (blob,) in rows:
        toks.update(re.findall(r"[a-z]{3,}", blob or ""))
    _VOCAB["tokens"], _VOCAB["at"] = toks, _t.time()
    return toks


def invalidate_vocabulary() -> None:
    _VOCAB["at"] = 0.0


def has_oov_token(db: Session, message: str) -> bool:
    vocab = kb_vocabulary(db)
    folded = db.execute(text("SELECT lower(unaccent(:m))"), {"m": message}).scalar() or message.lower()
    words = [w for w in re.findall(r"[a-z]{4,}", folded) if w not in _STOP]
    return any(w not in vocab for w in words)


_GREETING_START = re.compile(r"^\W*(hi+|hey+|hello+|helo|hallo|howdy|yo|good (morning|afternoon|evening|day)|greetings|sannu|"
                             r"ina kwana|ina wuni|barka|ẹ n lẹ́?|e n le|ẹ káàárọ̀|e kaaro|ẹ káàsán|e kaasan|ndewo|kedu|"
                             r"ụtụtụ ọma|ututu oma|thanks|thank you|na gode|ẹ ṣé|e se|daalụ|daalu)\b", re.I)
_DOMAIN_WORD = re.compile(r"\b(nin|nimc|passport|fasfo|paspọtụ|pásípọ̀ọ̀tù|licen[cs]e|lasisi\w*|birth|haihuwa|ọmụmụ|ìbí|"
                          r"frsc|npc|nis|fee|cost|apply|register|renew|how|what|where|when|nawa|yaya|ina zan|èló|kedu ka|ego)\b", re.I)


def _is_greeting(message: str) -> bool:
    """'hi', 'hi, guy', 'hello there', 'good morning sir', 'thanks!': a greeting word first, at most four words,
    and no service or question words (so 'hi, how do I get NIN?' is still treated as a question)."""
    m = message.strip()
    if not _GREETING_START.search(m):
        return False
    rest = _GREETING_START.sub("", m, count=1)
    return len(re.findall(r"\w+", m)) <= 4 and not _DOMAIN_WORD.search(rest)


def match_intent_rule(*texts: str) -> tuple[str, str] | None:
    blob = " ".join(t for t in texts if t).strip()
    if _is_greeting(blob):
        return "gen-what-can-you-do", "general"
    for pattern, key, domain in INTENT_RULES:
        if pattern.search(blob):
            return key, domain
    return None


def pinned_entry(db: Session, entry_key: str, langs: list[str]) -> Retrieved | None:
    sql = text(_BASE_SELECT + " AND ke.entry_key = :key ORDER BY (l.language_code = :pref) DESC LIMIT 1")
    row = db.execute(sql, {"langs": langs, "key": entry_key, "pref": langs[-1]}).fetchone()
    if not row:
        return None
    r = _row_to_retrieved(row)
    r.dense_score, r.lexical_score, r.fused_score = 1.0, 1.0, 1.0
    return r


def route_domain(db: Session, *texts: str) -> tuple[str, float]:
    """Soft keyword routing over service_domain.keywords. Returns (slug, score). Never a hard filter."""
    rows = db.execute(text("SELECT slug, keywords FROM service_domain WHERE is_active")).fetchall()
    blob = " ".join(t.lower() for t in texts if t)
    # "date of birth" belongs to whichever record is being corrected, not to civil registration
    blob = re.sub(r"\b(date of birth|birth ?date|dob|ranar haihuwa|ọjọ́ ìbí|ojo ibi|ụbọchị ọmụmụ|ubochi omumu)\b", " ", blob)
    # "...for NIN if I don't have a birth certificate": the certificate is a document here, the service is NIN
    if re.search(r"\b(nin|nimc|passport|licen[cs]e)\b", blob):
        blob = re.sub(r"\b(without|no|(do not|don'?t|dont) have|never had|i have no)( a| my| any)? birth cert\w*", " ", blob)
    best, best_score = OUT_OF_SCOPE, 0.0
    for slug, keywords in rows:
        score = 0.0
        for kw in keywords or []:
            kw_l = kw.lower()
            if re.search(rf"(?<!\w){re.escape(kw_l)}(?!\w)", blob):
                score += 1.0 + 0.2 * len(kw_l.split())
        if score > best_score:
            best, best_score = slug, score
    return best, best_score


def rrf_fuse(dense: list[Retrieved], lexical: list[Retrieved], domain: str, top_k: int, trigram: list[Retrieved] | None = None, pin_threshold: float = 0.6) -> list[Retrieved]:
    pool: dict[str, Retrieved] = {}
    for rank, r in enumerate(dense, start=1):
        pool.setdefault(r.entry_id, r).ranks["dense"] = rank
        pool[r.entry_id].dense_score = max(pool[r.entry_id].dense_score, r.dense_score)
    for rank, r in enumerate(lexical, start=1):
        pool.setdefault(r.entry_id, r).ranks["lexical"] = rank
        pool[r.entry_id].lexical_score = max(pool[r.entry_id].lexical_score, r.lexical_score)
    for rank, r in enumerate(trigram or [], start=1):
        pool.setdefault(r.entry_id, r).ranks["phrase"] = rank + 2
        pool[r.entry_id].lexical_score = max(pool[r.entry_id].lexical_score, r.lexical_score)
        pool[r.entry_id].lexical_score = max(pool[r.entry_id].lexical_score, r.lexical_score)
    def score_of(ranks: dict[str, int], lexical: float, slug: str) -> float:
        score = sum(1.0 / (RRF_K + rk) for rk in ranks.values())
        # tie-break within the same rank pattern by raw lexical rank magnitude (ts_rank_cd / trigram similarity)
        score += min(lexical, 1.0) * 0.002
        if domain != OUT_OF_SCOPE and slug == domain:
            score += DOMAIN_BOOST
        return score

    for r in pool.values():
        r.fused_score = score_of(r.ranks, r.lexical_score, r.domain_slug)
    # Sibling translations are one fact: fuse their evidence per entry_key (best rank per leg across languages), so a
    # Hausa phrasing match and an English dense match reinforce each other instead of competing. The best-scoring
    # sibling represents the fact; presentation swaps in the user's language later.
    by_key: dict[str, Retrieved] = {}
    merged_ranks: dict[str, dict[str, int]] = {}
    for r in sorted(pool.values(), key=lambda r: (r.fused_score, r.dense_score), reverse=True):
        if r.entry_key not in by_key:
            by_key[r.entry_key] = r
            merged_ranks[r.entry_key] = dict(r.ranks)
            continue
        rep, ranks = by_key[r.entry_key], merged_ranks[r.entry_key]
        for leg, rk in r.ranks.items():
            ranks[leg] = min(ranks.get(leg, rk), rk)
        rep.dense_score = max(rep.dense_score, r.dense_score)
        rep.lexical_score = max(rep.lexical_score, r.lexical_score)
    for key, rep in by_key.items():
        rep.ranks = merged_ranks[key]
        rep.fused_score = score_of(rep.ranks, rep.lexical_score, rep.domain_slug)
    # A near-exact match to a stored phrasing is decisive (this mirrors what a strong embedding does).
    if trigram and trigram[0].lexical_score >= pin_threshold:
        by_key[trigram[0].entry_key].fused_score += 1.0
    ranked = sorted(by_key.values(), key=lambda r: (r.fused_score, r.dense_score), reverse=True)
    return ranked[:top_k]


@dataclass
class RetrievalResult:
    results: list[Retrieved]
    domain: str
    domain_score: float
    top_dense: float
    top_lexical: float
    grounded: bool
    reason: str


def hybrid_search(db: Session, retrieval_query: str, original_message: str, target_language: str, prev_domain: str | None = None, is_followup: bool = False, query_language: str | None = None) -> RetrievalResult:
    s = get_settings()
    emb = get_embedder()
    # Retrieval runs on the English canonical layer; native entries join only when the question itself is written
    # in that language (their English portal names would otherwise pollute ranking). Presentation swaps in the
    # native sibling afterwards (pipeline), so the user still gets their language.
    qlang = query_language or target_language
    langs = ["en"] if qlang == "en" else ["en", qlang]

    rule = match_intent_rule(original_message)
    if rule:
        pinned = pinned_entry(db, rule[0], langs)
        if pinned:
            return RetrievalResult([pinned], rule[1], 10.0, 1.0, 1.0, True, "intent_rule")

    qvec = emb.embed_query(retrieval_query)
    dense = dense_search(db, qvec, langs, s.dense_candidates)
    lexical = lexical_search(db, f"{retrieval_query} {original_message}", langs, s.lexical_candidates)
    domain, domain_score = route_domain(db, retrieval_query, original_message)
    # phrase leg on the raw message; for follow-ups keep only candidates in the conversation's domain,
    # since "how much is it?" resembles every fee question
    trigram = trigram_search(db, original_message, langs, 8)
    if is_followup and prev_domain:
        trigram = [r for r in trigram if r.domain_slug == prev_domain]
        if domain == OUT_OF_SCOPE or domain == "general":
            domain = prev_domain
    if domain == OUT_OF_SCOPE and trigram and trigram[0].lexical_score >= 0.5:
        domain = trigram[0].domain_slug  # a near-phrasing match (typo) tells us the domain
    # A fuzzy phrase match is decisive when it is near-exact, or when the message has an out-of-vocabulary word
    # (a typo such as "renual"); templated near-misses ("track" vs "renew") share vocabulary and are not pinned.
    pin = 0.9 if is_followup else 0.85
    if trigram and 0.6 <= trigram[0].lexical_score < pin and not is_followup and has_oov_token(db, original_message):
        pin = 0.6
    # A clearly best phrasing (well ahead of the runner-up) is decisive too: "Ṣàlàyé NIN fún mi" vs the stored
    # "Ṣàlàyé NIN" scores 0.61 while the next phrasing scores 0.32.
    if (trigram and len(trigram) > 1 and not is_followup and trigram[0].lexical_score >= 0.55
            and trigram[0].lexical_score >= 1.6 * trigram[1].lexical_score):
        pin = min(pin, trigram[0].lexical_score)
    fused = rrf_fuse(dense, lexical, domain, s.retrieval_top_k, trigram, pin_threshold=pin)

    top_dense = max((r.dense_score for r in dense), default=0.0)
    top_lex = max([r.lexical_score for r in lexical] + [r.lexical_score for r in trigram], default=0.0)
    in_domain_term = re.search(r"\b(nin|nimc|passport|fasfo|paspọtụ|pásípọ̀ọ̀tù|licen[cs]e|lasisi\w*|birth|haihuwa|ọmụmụ|ìbí|frsc|npc|nis)\b", original_message, re.I)
    oos_hit = (bool(OOS_TERMS.search(original_message)) and not in_domain_term) or bool(HARD_OOS.search(original_message))
    content_source = retrieval_query if (is_followup and prev_domain) else original_message
    content_tokens = [t for t in re.findall(r"[^\W\d_]{3,}", content_source.lower()) if t not in _STOP]
    if not content_tokens:
        oos_hit = True  # nothing to retrieve on ("What is 2 + 2?", "???")
    gate = s.gate_dense_model if emb.is_model else s.gate_dense_local

    # Grounding gate (algorithm step 6).
    grounded, reason = True, "ok"
    if not fused:
        grounded, reason = False, "no_candidates"
    elif oos_hit:
        grounded, reason = False, "out_of_scope_term"
    elif top_dense >= gate:
        grounded, reason = True, "dense"
    elif domain != OUT_OF_SCOPE and top_lex >= s.gate_lexical_min and top_dense >= gate * 0.6:
        grounded, reason = True, "lexical+domain"
    elif domain != OUT_OF_SCOPE and top_lex >= 0.3 and fused and fused[0].domain_slug == domain:
        grounded, reason = True, "strong_lexical+domain"  # short in-domain messages such as greetings
    else:
        grounded, reason = False, "below_threshold"
    # An in-scope keyword hit is required when the dense signal is only moderately above the gate:
    # protects against generic questions that merely share vocabulary with the knowledge base.
    if grounded and domain == OUT_OF_SCOPE and top_dense < gate + 0.12:
        grounded, reason = False, "out_of_scope"
    return RetrievalResult(fused, domain, domain_score, top_dense, top_lex, grounded, reason)


def sibling_in_language(db: Session, entry_key: str, language_code: str) -> Retrieved | None:
    sql = text(_BASE_SELECT + " AND ke.entry_key = :key AND l.language_code = :lang LIMIT 1")
    row = db.execute(sql, {"langs": [language_code], "key": entry_key, "lang": language_code}).fetchone()
    return _row_to_retrieved(row) if row else None
