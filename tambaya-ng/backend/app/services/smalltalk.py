"""Conversational layer: greetings, thanks, acknowledgements and goodbyes in all five languages, answered instantly
without retrieval or an LLM call (modelled on CivicSpeak NG). A message counts as small talk only when EVERY word in
it is small talk or filler ("good morning sir", "ok thanks o", "no wahala", "🙏"); "hi, how do I get my NIN?" is a
question and goes to retrieval. These turns are stored with an empty domain so follow-ups walk past them to the
last real topic."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# (pattern, kind, language hint). Order matters: longer phrases first so "how far" is not read as "how".
_PHRASES: list[tuple[str, str, str]] = [
    # how are you
    (r"how are you( doing| today)?|how (is|are) (you|things)|how'?s it going|how do you do", "howareyou", "en"),
    (r"how (you|una) dey|how body|how your side|how e dey|wetin dey (happen|sup)|how far( now)?|how market", "howareyou", "pcm"),
    (r"ina gajiya|ya aiki|kana lafiya|kina lafiya|lafiya lau|ina labari|yaya kake|yaya kike", "howareyou", "ha"),
    (r"ṣé dáadáa ni|se daadaa ni|ṣe àlàáfíà ni|se alaafia ni|bawo ni nkan|báwo ni nǹkan|ṣé ẹ wà|se e wa", "howareyou", "yo"),
    (r"kedu ka [iị] mere|kedu ka ị dị|kedu ka i di|ị dị mma|i di mma", "howareyou", "ig"),
    # goodbye
    (r"good ?bye|bye( bye)?|see you( later| soon)?|talk (to you )?later|later then|good night|take care|cheers", "bye", "en"),
    (r"make i (dey )?go|i dey go|i don go|we go see|later o|ok bye o", "bye", "pcm"),
    (r"sai an jima|sai anjima|sai wani lokaci|sai gobe|mu kwana lafiya|a kwana lafiya", "bye", "ha"),
    (r"ó dàbọ̀|o dabo|ó dàárọ̀|o daaro|ó di ọ̀la|o di ola|ó dìgbà|o digba", "bye", "yo"),
    (r"ka ọ dị|ka o di|ka emesịa|ka emesia|ka chi fo|ka chi foo", "bye", "ig"),
    # thanks
    (r"thank you( so much| very much| a lot)?|thanks( a lot| so much| very much)?|many thanks|thank u|thx|tnx|thnx|"
     r"i appreciate( it| you)?|much appreciated|god bless( you)?|you'?ve been (very )?helpful|you are (very )?helpful|"
     r"that'?s (very )?helpful|this is (very )?helpful|great help", "thanks", "en"),
    (r"thank you o+|tanks o+|i hail|you too much|e don do|you do well|god go bless you|bless you o", "thanks", "pcm"),
    (r"na gode( sosai| kwarai)?|nagode|mun gode|godiya|allah ya saka( da alheri)?|madalla", "thanks", "ha"),
    (r"ẹ ṣé( gan| púpọ̀)?|e se( gan| pupo)?|ẹ ṣeun|e seun|o ṣeun|o seun|o ṣé|o se gan", "thanks", "yo"),
    (r"daalụ( rinne)?|daalu( rinne)?|imeela|i meela|ị meela", "thanks", "ig"),
    # greetings
    (r"good (morning|afternoon|evening|day)|hi+|hey+|hello+|helo|hallo|howdy|greetings|hiya|yo|sup|whats? up|"
     r"compliments of the season|happy new year|merry christmas|happy sunday", "greet", "en"),
    (r"how far|wetin dey|my guy|my people|how una", "greet", "pcm"),
    (r"(as)?sala+mu? (wa)?alaikum( (wa )?rahmatullah)?|salam|sannu( da (zuwa|aiki|rana))?|ina kwana|ina wuni|barka( da (safiya|rana|yamma|asuba|zuwa))?", "greet", "ha"),
    (r"ẹ n lẹ́|ẹ n le|e n le|ẹ káàárọ̀|ẹ kaaro|e kaaro|ẹ káàsán|e kaasan|ẹ káalẹ́|e kaale|ẹ kú|e ku( aaro| asan| ale)?|"
     r"ẹ káàbọ̀|e kaabo|bawo ni|báwo ni", "greet", "yo"),
    (r"ndewo( nu)?|kedu|ụtụtụ ọma|ututu oma|ehihie ọma|ehihie oma|mgbede ọma|mgbede oma|nnọọ|nnoo", "greet", "ig"),
    # acknowledgements
    (r"ok(ay|ey|k+)?|alright|all right|noted|cool|fine|great|nice|good|i see|i understand|understood|got it|gotcha|"
     r"no problem|perfect|sure|right|yes|yeah|yep|correct|wow|interesting|hmm+|mm+|kk|k|nothing( else)?|that'?s all|"
     r"(i'?m|i am) (good|fine|okay|ok|alright)|no thanks|no|nope", "ack", "en"),
    (r"no wahala|e good|e don clear|i don hear|i hear you|i don see|sharp|na so|correct o|ehen|oya", "ack", "pcm"),
    (r"to+h?|shikenan|na gane|na ji|madalla|yauwa|haka ne|da kyau", "ack", "ha"),
    (r"ó dáa|o daa|ó dára|o dara|mo gbọ́|mo gbo|bẹ́ẹ̀ ni|bee ni|ó yé mi|o ye mi", "ack", "yo"),
    (r"ọ dị mma|o di mma|ọ dịmma|odimma|m nụrụ|m nuru|ezi okwu|ọ ga-adị|o ga-adi", "ack", "ig"),
]
# Language-specific phrases first and generic English acknowledgements last, so "no wahala" and "thank you o" are
# read as Pidgin before "no" or "thank you" is read as English.
_PHRASES.sort(key=lambda t: (t[2] == "en", t[1] == "ack" and t[2] == "en"))
_COMPILED = [(re.compile(rf"(?<![\w'’])(?:{p})(?![\w'’])", re.I), kind, lang) for p, kind, lang in _PHRASES]

# Words that carry no request of their own: honorifics, softeners, names for the bot, emphasis.
_FILLER = re.compile(
    r"(?<![\w'’])(sir|ma|mah|madam|maam|ma'am|boss|chief|oga|bros|broda|brother|sister|sis|aunty|auntie|uncle|guy|guys|"
    r"dear|friend|bot|tambaya( ng)?|there|all|everyone|o+|oo+|sha|jare|abeg|please|pls|plz|biko|nau|now|again|too|"
    r"very|much|so|a lot|and|then|just|well|oh|ah|eh|wow|lol|haha+|ehn|ehen|sef|o jare|una|you|u|yall|y'all|"
    r"for (your|the) (help|info|information|time)|for helping|for this|for that|kuma|ma|fa|ke|kai|nwanne|nna|nne|"
    r"ẹ|e|mi|m|ọ|o)(?![\w'’])", re.I)
_EMOJI_ONLY = re.compile(r"^[\s\W_]*$")
_GOOD_EMOJI = re.compile("[\U0001F44D\U0001F64F\U0001F44C\U0001F60A\U0001F642❤✅\U0001F600-\U0001F64F]")

_PRIORITY = {"bye": 0, "thanks": 1, "howareyou": 2, "greet": 3, "ack": 4}


@dataclass
class SmallTalk:
    kind: str       # greet | howareyou | thanks | ack | bye
    language: str   # the language the phrase belongs to ("en" for neutral words such as "ok" or "hi")


def _fold(s: str) -> str:
    return unicodedata.normalize("NFC", s.lower()).strip()


def classify(message: str) -> SmallTalk | None:
    text = _fold(message)
    if not text:
        return None
    if _EMOJI_ONLY.match(text):
        # "👍", "🙏", "...", "?" : an emoji is an acknowledgement; bare punctuation is not a message worth answering
        # as small talk, except "..." which is a nudge.
        if _GOOD_EMOJI.search(message):
            return SmallTalk("ack", "en")
        return SmallTalk("ack", "en") if re.fullmatch(r"\s*(\.{2,}|…)\s*", text) else None
    found: list[tuple[int, str, str]] = []
    rest = text
    for pat, kind, lang in _COMPILED:
        for m in pat.finditer(rest):
            found.append((m.start(), kind, lang))
        rest = pat.sub(" ", rest)
    if not found:
        return None
    rest = _FILLER.sub(" ", rest)
    if re.search(r"[^\W\d_]", rest):   # a real word remains: this is a question or request, not small talk
        return None
    if re.search(r"\d", rest):
        return None
    kinds = sorted({k for _, k, _ in found}, key=_PRIORITY.get)
    # The language comes from the first non-English phrase, so "ok, na gode" is Hausa.
    langs = [l for _, _, l in sorted(found) if l != "en"]
    return SmallTalk(kinds[0], langs[0] if langs else "en")


REPLIES: dict[str, dict[str, str]] = {
    "greet": {
        "en": "Hello! I'm Tambaya NG. Ask me about **NIN**, **passports**, **driver's licences** or **birth registration**, "
              "in English, Hausa, Yorùbá, Igbo or Pidgin. For example: \"How much is a passport?\"",
        "pcm": "How far! Na Tambaya NG be this. Ask me anything about **NIN**, **passport**, **driver's licence** or "
               "**birth registration**, for English, Hausa, Yorùbá, Igbo or Pidgin. Like: \"How much be passport?\"",
        "ha": "Sannu! Ni ne Tambaya NG. Tambaye ni game da **NIN**, **fasfo**, **lasisin tuƙi** ko **rajistar haihuwa**, "
              "da Hausa, Turanci, Yarbanci, Igbo ko Pidgin. Misali: \"Nawa ne kuɗin fasfo?\"",
        "yo": "Ẹ n lẹ́! Èmi ni Tambaya NG. Ẹ bi mí nípa **NIN**, **pásípọ̀ọ̀tù**, **ìwé-àṣẹ awakọ̀** tàbí **ìforúkọsílẹ̀ ìbí**, "
              "ní Yorùbá, Gẹ̀ẹ́sì, Hausa, Igbo tàbí Pidgin. Fún àpẹẹrẹ: \"Èló ni pásípọ̀ọ̀tù?\"",
        "ig": "Ndewo! Abụ m Tambaya NG. Jụọ m gbasara **NIN**, **paspọtụ**, **ikike ịnya ụgbọala** ma ọ bụ **ndebanye aha ọmụmụ**, "
              "n'Igbo, Bekee, Hausa, Yoruba ma ọ bụ Pidgin. Dịka: \"Ego ole ka paspọtụ na-efu?\"",
    },
    "howareyou": {
        "en": "I'm doing well, thank you! How can I help with your NIN, passport, driver's licence or birth registration?",
        "pcm": "I dey kampe, thank you! Wetin I fit help you with: NIN, passport, driver's licence or birth registration?",
        "ha": "Lafiya lau, na gode! Me zan taimaka maka da shi game da NIN, fasfo, lasisin tuƙi ko rajistar haihuwa?",
        "yo": "Dáadáa ni, ẹ ṣé! Báwo ni mo ṣe lè ràn yín lọ́wọ́ nípa NIN, pásípọ̀ọ̀tù, ìwé-àṣẹ awakọ̀ tàbí ìforúkọsílẹ̀ ìbí?",
        "ig": "Adị m mma, daalụ! Kedu ka m ga-esi nyere gị aka gbasara NIN, paspọtụ, ikike ịnya ụgbọala ma ọ bụ ndebanye aha ọmụmụ?",
    },
    "thanks": {
        "en": "You're welcome! Is there anything else you'd like to know about NIN, passports, driver's licences or birth registration?",
        "pcm": "No wahala! Anything else wey you wan know about NIN, passport, licence or birth registration?",
        "ha": "Babu komai! Akwai wani abu kuma da kake son sani game da NIN, fasfo, lasisin tuƙi ko rajistar haihuwa?",
        "yo": "Kò tọ́pẹ́! Ṣé ohun mìíràn wà tí ẹ fẹ́ mọ̀ nípa NIN, pásípọ̀ọ̀tù, ìwé-àṣẹ awakọ̀ tàbí ìforúkọsílẹ̀ ìbí?",
        "ig": "Ọ dịghị nsogbu! Ọ nwere ihe ọzọ ị chọrọ ịma gbasara NIN, paspọtụ, ikike ịnya ụgbọala ma ọ bụ ndebanye aha ọmụmụ?",
    },
    "ack": {
        "en": "Alright. If you have another question about NIN, passports, driver's licences or birth registration, just ask.",
        "pcm": "Okay o. If you get another question about NIN, passport, licence or birth registration, just ask.",
        "ha": "To, shikenan. Idan kana da wata tambaya game da NIN, fasfo, lasisin tuƙi ko rajistar haihuwa, ka tambaya.",
        "yo": "Ó dáa. Tí ẹ bá ní ìbéèrè mìíràn nípa NIN, pásípọ̀ọ̀tù, ìwé-àṣẹ awakọ̀ tàbí ìforúkọsílẹ̀ ìbí, ẹ béèrè.",
        "ig": "Ọ dị mma. Ọ bụrụ na ị nwere ajụjụ ọzọ gbasara NIN, paspọtụ, ikike ịnya ụgbọala ma ọ bụ ndebanye aha ọmụmụ, jụọ m.",
    },
    "bye": {
        "en": "Goodbye, and all the best with your application. Come back any time you have a question.",
        "pcm": "Alright, take care! All the best with your application. Come back anytime you get question.",
        "ha": "Sai an jima! Allah ya sa a yi nasara da buƙatarka. Ka dawo kowane lokaci.",
        "yo": "Ó dàbọ̀! A kú orí ire fún ìbéèrè yín. Ẹ padà wá nígbàkúùgbà.",
        "ig": "Ka ọ dị! Ihe ọma n'arịrịọ gị. Lọghachi mgbe ọ bụla ị nwere ajụjụ.",
    },
}


def reply(kind: str, language: str) -> str:
    table = REPLIES.get(kind, REPLIES["ack"])
    return table.get(language) or table["en"]
