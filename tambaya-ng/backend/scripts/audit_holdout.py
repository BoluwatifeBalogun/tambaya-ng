"""Held-out phrasings never added to alt_questions: an honest generalisation check. python -m scripts.audit_holdout"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import SessionLocal
from app.services import pipeline

HOLDOUT = [
    ("my sister wants to do her nin, what should she carry along", "nin-documents"),
    ("is there any payment at the nimc centre", "nin-cost"),
    ("the number i used for nin enrolment is lost, can i still see my nin", "nin-retrieve"),
    ("they spelt my surname wrongly on my nin", "nin-modify-how"),
    ("how many naira for dob change on nin", "nin-modify-fees"),
    ("my sim was barred because of nin, why", "nin-uses"),
    ("which app shows my digital nin", "nin-ninauth"),
    ("a man in the market says 2k will make my nin come out same day", "nin-scam-warning"),
    ("green passport price now", "pp-fees"),
    ("never had a passport before, procedure please", "pp-fresh-steps"),
    ("guarantor requirement for international passport", "pp-documents"),
    ("my daughter is 7, passport process", "pp-minor"),
    ("passport booklet finished pages, what do i do", "pp-renewal"),
    ("married last year, want my husband's name on passport", "pp-change-data"),
    ("did capture 3 weeks ago, when do i get the booklet", "pp-processing-time"),
    ("which immigration office can i use in abuja", "pp-where"),
    ("someone offered express passport in 2 days for 150k", "pp-touts"),
    ("difference between class A and class B licence", "dl-overview"),
    ("finished my driving lessons last week, next step for licence", "dl-fresh-steps"),
    ("am I old enough at 17 to get a licence", "dl-requirements"),
    ("okada licence price", "dl-fees"),
    ("licence expired last month what now", "dl-renewal"),
    ("my wallet was stolen with my licence inside", "dl-reissue"),
    ("after how many years does the licence expire", "dl-validity"),
    ("they said my licence card is ready where do i go", "dl-tracking"),
    ("i want to drive trailers, which licence", "dl-commercial"),
    ("which government body keeps birth records", "br-overview"),
    ("gave birth last week, how do i get the certificate", "br-how-register"),
    ("what to carry to npc for baby registration", "br-documents"),
    ("npc officer asked for 2000 naira for my baby's certificate", "br-cost"),
    ("i am 30 with no birth certificate", "br-late"),
    ("immigration rejected my attestation, is it different from certificate", "br-attestation-vs-certificate"),
    ("npc website for registering birth", "br-online-portals"),
    ("my grandmother passed away, how do we get the certificate", "br-death"),
    ("'yata tana son yin NIN, me za ta kawo", "nin-documents"),
    ("ana karbar kudi a cibiyar NIMC?", "nin-cost"),
    ("sun rubuta sunana ba daidai ba a NIN", "nin-modify-how"),
    ("kudin fasfo kore yanzu", "pp-fees"),
    ("ban taba yin fasfo ba, yaya za a yi", "pp-fresh-steps"),
    ("'yata 'yar shekara 7, yadda ake yi mata fasfo", "pp-minor"),
    ("na gama darussan tuki, mataki na gaba na lasisi", "dl-fresh-steps"),
    ("kudin lasisin babur", "dl-fees"),
    ("lasisina ya kare watan jiya me zan yi yanzu", "dl-renewal"),
    ("an sace walat dina da lasisi a ciki", "dl-reissue"),
    ("na haihu makon jiya, yaya zan samu takardar", "br-how-register"),
    ("jami'in NPC ya nemi naira 2000 don takardar jaririna", "br-cost"),
    ("ina da shekara 30 ba ni da takardar haihuwa", "br-late"),
    ("kakata ta rasu, yaya za mu samu takardar", "br-death"),
    ("ọmọ mi fẹ́ ṣe NIN, kí ni kí ó mú lọ", "nin-documents"),
    ("owó pásípọ̀ọ̀tù aláwọ̀ ewé báyìí", "pp-fees"),
    ("mo bí ọmọ ní ọ̀sẹ̀ tó kọjá, báwo ni mo ṣe lè gba ìwé-ẹ̀rí", "br-how-register"),
    ("wọ́n jí wọ́lẹ́ẹ̀tì mi pẹ̀lú lásìnsì mi nínú", "dl-reissue"),
    ("nwanne m nwanyị chọrọ ime NIN, gịnị ka ọ ga-eweta", "nin-documents"),
    ("ego paspọtụ akwụkwọ ndụ ugbu a", "pp-fees"),
    ("a mụrụ m nwa n'izu gara aga, kedu ka m ga-esi nweta akwụkwọ", "br-how-register"),
    ("e zuru obere akpa m na laisensị m n'ime ya", "dl-reissue"),
    ("how to get a nigerian visa for my american friend", None),
    ("best bank for savings account", None),
    ("how do i check my waec result", None),
    ("register my car plate number", None),
    ("what time does nimc office close", None),  # plausible but not in KB: should not invent
    ("can i use nin to vote", None),
]

with SessionLocal() as db:
    ok = 0
    for q, exp in HOLDOUT:
        r = pipeline.answer(db, q, "auto", None, None)
        got = r.sources[0].entry_key if r.sources else None
        passed = (exp is None and r.fallback) or (exp is not None and got == exp)
        ok += passed
        if not passed:
            print(f"FAIL  {q!r:70} expected={exp} got={got or ('fallback' if r.fallback else '-')} det={r.detected_language}")
    print(f"\nHeld-out: {ok}/{len(HOLDOUT)} = {ok/len(HOLDOUT):.1%}")
