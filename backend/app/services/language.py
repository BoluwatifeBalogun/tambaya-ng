"""Language-processing layer (report §3.14.1): identification, glossary normalisation and
retrieval-query construction. Kept independent of retrieval so new languages are a data change."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

SUPPORTED = ("en", "ha", "yo", "ig", "pcm")

LANGUAGE_NAMES = {"en": "English", "ha": "Hausa", "yo": "Yoruba", "ig": "Igbo", "pcm": "Nigerian Pidgin"}

# Lexicon detector: common function words and orthographic cues per language.
_MARKERS: dict[str, set[str]] = {
    "ha": {
        "yaya", "nawa", "menene", "mene", "ina", "wane", "wace", "wadanne", "wadannan", "zan", "zai", "za",
        "ne", "ce", "na", "ta", "da", "don", "kuma", "ko", "ba", "ban", "kudin", "kuɗin", "kudi", "kuɗi", "takarda",
        "takardar", "takardun", "fasfo", "fasfon", "lasisi", "lasisin", "tuki", "tuƙi", "haihuwa", "sannu", "ya",
        "yi", "yin", "samu", "sami", "samun", "bukata", "buƙata", "ake", "ana", "zaka", "zaku", "ka", "ki", "shi",
        "ita", "mu", "su", "nake", "muna", "mota", "rajista", "rijista", "shekaru", "wuri", "ofis", "ofishin",
        "gwamnati", "hukuma", "hukumar", "yara", "yaro", "iyaye", "biya", "biyan", "neman", "nema", "sabunta",
        "kyauta", "rajistar", "haihuwar", "yanar", "gizo", "wannan", "lokacin", "zama", "iya", "wane", "wace", "gyara",
        "gyaran", "sunana", "canza", "lambar", "waya", "biya", "sace", "lasisina", "taimako", "kira", "ganin", "wuni",
        "jariri", "katin", "karɓi", "karbi", "shirya", "bibiyar", "kawo", "mutuwar", "mahaifina", "shekara", "madadina",
        "sarrafa", "buƙatu", "bukatu", "zaka", "zai", "mai", "ake", "ana", "takardun", "suna", "gyaran", "lasisin", "fasfo",
    },
    "yo": {
        "báwo", "bawo", "ni", "mo", "ṣe", "se", "èló", "elo", "kí", "kini", "kín", "fún", "fun", "ìwé", "iwe",
        "orúkọ", "oruko", "ọmọ", "omo", "ibí", "ibi", "lè", "le", "gba", "ṣé", "àti", "ati", "tàbí", "tabi", "wà",
        "wa", "ló", "lo", "tí", "ti", "sí", "si", "nínú", "ninu", "owó", "owo", "àṣẹ", "ase", "awakọ̀", "awako",
        "pásípọ̀ọ̀tù", "pasipootu", "ìrìnnà", "irinna", "kaabo", "káàbọ̀", "ẹ", "e", "jọ̀wọ́", "jowo", "báwo ni",
        "nílò", "nilo", "ẹ̀rí", "eri", "ìforúkọsílẹ̀", "iforukosile", "forúkọ", "foruko", "ìjọba", "ijoba", "ikú", "iku",
        "sọnù", "sonu", "pàdánù", "padanu", "pari", "parí", "gbàgbé", "gbagbe", "fóònù", "foonu", "lórí", "lori", "tún", "tun",
        "lásìnsì", "lasinsi", "wo", "kí", "ṣé", "n", "a", "ń", "ẹ", "náà", "náa", "nkọ́", "nko", "rẹ̀", "re",
    },
    "ig": {
        "kedu", "gịnị", "gini", "ole", "ka", "m", "nwere", "ike", "akwụkwọ", "akwukwo", "ego", "maka", "na", "nke",
        "ndewo", "biko", "ị", "i", "gị", "gi", "anyị", "anyi", "ha", "ya", "si", "esi", "ga", "ga-esi", "ihe",
        "ọrụ", "oru", "paspọtụ", "paspotu", "ụgbọala", "ugboala", "ịnya", "inya", "ikike", "ọmụmụ", "omumu",
        "ndebanye", "aha", "nọmba", "nomba", "njirimara", "ụgwọ", "ugwo", "ebee", "otu", "mgbe", "ụlọọrụ", "uloru",
        "gọọmentị", "goomenti", "nwa", "nne", "nna", "afọ", "afo", "kọwaa", "kowaa", "usoro", "inweta", "nweta", "bụ", "bu",
        "efu", "n'efu", "echefuru", "lelee", "ekwentị", "ekwenti", "agwụla", "agwula", "megharịa", "megharia", "furu", "nwata",
        "ọnwụ", "onwu", "ime", "eme", "mere", "chọrọ", "choro", "eweta", "ahịa", "ahia", "ọnụ", "onu",
    },
    "en": {
        "the", "is", "are", "how", "what", "where", "when", "do", "does", "i", "my", "can", "need", "get", "for",
        "to", "a", "an", "of", "and", "much", "cost", "fee", "apply", "renew", "register", "documents", "required",
        "passport", "licence", "license", "birth", "certificate", "nin", "it", "this", "that", "with", "in", "on",
    },
}

# Hausa hooked letters and Yoruba/Igbo dotted vowels are strong single-character cues.
_CHAR_CUES = {
    "ha": set("ɓɗƙƴƁƊƘƳ"),
    "yo": set("ẹọṣẸỌṢ"),
    "ig": set("ịụṅỊỤṄ"),
}

# Nigerian Pidgin. Pidgin shares most of its vocabulary with English, so it is scored separately: words that only
# Pidgin uses ("unique"), Pidgin grammar patterns ("phrases") and words that are Pidgin only next to other cues ("weak").
# Softeners such as "abeg", "sha" and "o" are used in Nigerian English too, so on their own they never make a message Pidgin.
_PCM_STRONG = {"abeg", "abegi", "wetin", "dey", "sabi", "una", "sef", "pikin", "pikin's", "comot", "wahala", "oga", "shey",
               "abi", "wey", "dem", "don", "make", "nau", "naim", "wan", "fit", "am", "sha", "o", "go", "be", "na"}
_PCM_UNIQUE = {"wetin", "dey", "sabi", "una", "sef", "pikin", "comot", "wahala", "shey", "naim", "nau", "wey"}
_PCM_PHRASES = re.compile(
    r"(?<!\w)(how far|no wahala|na (im|so|free|wetin|how|who|where|which|the|my|fit|true)|how i go|how person go|how person fit|"
    r"i (don|wan|fit|dey)(?![\w'’])|i go (take|fit|do|pay|carry|collect|renew|check)\b|e (don|dey|go|fit|be|free|cost)(?![\w'’])|"
    r"dem (dey|don|go|fit|wan|no)(?![\w'’])|make i(?![\w'’])|make una|"
    r"no be\b|how much be\b|wetin be\b|which one be\b|una dey|e no (dey|go|fit)|no vex|"
    r"(do|renew|get|collect|check|carry|use|find|print|replace) am\b|for internet|this tin|dis tin|wetin i go|"
    r"(which|what) ((?!(do|does|did|can|could|should|will|would|must|shall|may|am)\b)\w+ ){0,2}i (need|go|fit|suppose)(?![\w'’])|(where|how|when) i (fit|suppose)(?![\w'’])|"
    r"(?<!i )don (die|loss|lose|lost|expire|expired|spoil|finish|old|born|reach|pay|do|apply|register|collect|enter|comot|change)\b|"
    r"how (we|una|dem|e|person) go\b|go take (get|do|collect|register|renew)\b)",
    re.I)


def pidgin_score(text: str) -> float:
    toks = _tokens(text)
    if not toks:
        return 0.0
    low = text.lower()
    unique = sum(1 for t in toks if t in _PCM_UNIQUE)
    phrases = len(_PCM_PHRASES.findall(low))
    if not unique and not phrases:
        return 0.0
    weak = sum(1 for t in toks if t in _PCM_STRONG and t not in _PCM_UNIQUE)
    return min(1.5, 0.45 * unique + 0.45 * phrases + 0.08 * weak)


# Glossary used to build an English retrieval query when Groq is not available (code-switching aware).
GLOSSARY: dict[str, str] = {
    # Hausa
    "fasfo": "passport", "fasfon": "passport", "fasfona": "passport", "lasisin tuƙi": "driver's licence",
    "lasisin tuki": "driver's licence", "lasisi": "licence", "lasisin": "licence", "tuƙi": "driving", "tuki": "driving",
    "takardar haihuwa": "birth certificate", "takardar shaidar haihuwa": "birth certificate", "haihuwa": "birth",
    "rajista": "registration", "rajistar": "registration", "rijista": "registration", "kuɗin": "fee cost",
    "kudin": "fee cost", "kuɗi": "fee cost", "kudi": "fee cost", "nawa": "how much", "takardu": "documents",
    "takardun": "documents", "takarda": "document", "yaya": "how", "ta yaya": "how", "menene": "what is",
    "ina": "where", "sabunta": "renew", "sabuntawa": "renewal", "ɓace": "lost", "bace": "lost", "sace": "stolen",
    "yaro": "child", "yara": "children", "ɗana": "my child", "dana": "my child", "shekaru": "years",
    "gyara": "modification correction", "gyaran": "modification correction", "canza": "change", "suna": "name",
    "ranar haihuwa": "date of birth", "lambar waya": "phone number", "wakili": "agent", "ofishin": "office",
    "kyauta": "free", "lokaci": "time", "tsawon": "how long", "mutuwa": "death", "babur": "motorcycle", "mota": "vehicle",
    "shaidar ƙasa": "national identity", "shaidar kasa": "national identity",
    # Yoruba
    "pásípọ̀ọ̀tù": "passport", "pasipootu": "passport", "ìwé ìrìnnà": "passport", "iwe irinna": "passport",
    "ìwé-àṣẹ awakọ̀": "driver's licence", "iwe-ase awako": "driver's licence", "lásìnsì": "licence",
    "ìwé-ẹ̀rí ìbí": "birth certificate", "iwe eri ibi": "birth certificate", "ìbí": "birth", "ibi": "birth",
    "èló": "how much", "elo": "how much", "owó": "fee cost", "owo": "fee cost", "ìforúkọsílẹ̀": "registration",
    "iforukosile": "registration", "báwo": "how", "bawo": "how", "kí ni": "what is", "kini": "what is",
    "níbo": "where", "nibo": "where", "ọmọ": "child", "omo": "child", "tún": "renew", "ọ̀fẹ́": "free", "ofe": "free",
    "nọ́mbà ìdánimọ̀": "national identification number", "nomba idanimo": "national identification number",
    # Pidgin
    "wetin": "what", "how i go take": "how do I", "how i go": "how do I", "pikin": "child", "dem dey collect money": "cost fee free",
    "dey charge": "cost fee", "na free": "is free cost", "abeg": "", "sef": "", "fit": "can", "wan": "want", "don expire": "expired renewal",
    "don lose": "lost", "for internet": "online portal",
    # Igbo
    "paspọtụ": "passport", "paspotu": "passport", "akwụkwọ ngafe": "passport", "ikike ịnya ụgbọala": "driver's licence",
    "ikike inya ugboala": "driver's licence", "laisensị": "licence", "akwụkwọ ọmụmụ": "birth certificate",
    "akwukwo omumu": "birth certificate", "ọmụmụ": "birth", "omumu": "birth", "ego ole": "how much",
    "ụgwọ": "fee cost", "ugwo": "fee cost", "ndebanye aha": "registration", "kedu ka": "how", "gịnị bụ": "what is",
    "gini bu": "what is", "ebee": "where", "nwa": "child", "n'efu": "free", "nọmba njirimara": "national identification number",
    "nomba njirimara": "national identification number",
}

# English intent synonyms appended to the retrieval query so lexical search sees the knowledge-base vocabulary.
EN_SYNONYMS: dict[str, str] = {
    "how much": "fee cost", "price": "fee cost", "cost": "fee", "pay": "fee payment", "how long": "validity duration time",
    "last": "validity", "expire": "renewal expired", "expired": "renewal", "lost": "lost stolen re-issue replace",
    "stolen": "lost re-issue", "missing": "lost", "baby": "child birth", "newborn": "child birth registration",
    "kid": "child", "children": "child minor", "for my child": "minor child", "my child": "minor child", "my son": "minor child", "my daughter": "minor child", "my baby": "minor child newborn", "renew": "renewal", "replace": "re-issue", "correct": "modification correction",
    "change": "modification change", "update": "modification update", "requirements": "documents required",
    "need": "requirements documents", "where": "office centre location", "track": "status tracking",
    "status": "tracking", "agent": "agent tout fraud", "free": "free cost", "fast": "processing time",
    "forgot": "retrieve forgot", "retrieve": "retrieve check", "check": "retrieve check", "apply": "application steps",
    "get": "apply obtain", "steps": "process steps", "process": "steps procedure", "office": "office centre",
    "late": "late registration attestation", "adult": "attestation late registration", "death": "death registration",
    "first time": "fresh new application steps", "start": "steps apply", "what next": "steps apply", "finished": "steps apply",
    "edit": "modification change", "modify": "modification", "birth date": "date of birth modification", "birthdate": "date of birth modification", "valid": "validity", "ready": "status tracking collect",
    "collect": "collect tracking", "not ready": "status tracking", "stolen": "lost re-issue", "fast track": "agent tout",
    "quickly": "agent tout fast", "someone": "agent", "contact": "office contact phone", "near me": "office location",
    "from kano": "any state office", "truck": "commercial", "trucks": "commercial", "bus": "commercial",
    "important": "uses required", "stand for": "what is", "mean": "what is", "eligible": "eligibility who can",
    "who can": "eligibility", "year old": "eligibility child age", "minimum age": "eligibility requirements age",
    "bring": "documents required", "acceptable": "documents accepted", "voter": "documents voter card",
    "id can i use": "documents accepted", "charging": "cost free agent", "charge": "cost fee", "pay for": "cost fee",
    "money": "cost fee", "agency": "issues responsible", "issues": "who issues", "which agency": "who issues",
    "spelling": "change of data correction", "after marriage": "change of name", "online": "online portal internet digital",
    "passed away": "death certificate", "died": "death certificate", "late father": "death", "late mother": "death", "burial": "death certificate",
    "wallet": "lost", "bag was stolen": "lost stolen", "procedure": "steps process", "process please": "steps", "payment": "cost fee",
    "naira": "cost fee", "k will": "agent fraud fee", "same day": "agent fast", "express": "agent fast", "carry": "documents bring",
    "carry along": "documents", "website": "online portal", "government body": "who issues agency", "old enough": "minimum age eligibility",
    "how old": "minimum age", "finished pages": "renewal replace booklet", "pages finished": "renewal", "expire": "validity expired renewal",
    "never had": "first time new application", "capture": "biometric capture processing", "booklet ready": "processing time collection",
    "when do i get": "processing time", "trailer": "commercial", "trailers": "commercial", "lorry": "commercial", "okada": "motorcycle",
    "keke": "tricycle motorcycle", "class a": "licence classes", "class b": "licence classes", "surname": "name", "spelt": "correction modification",
    "wrongly": "correction modification", "barred": "sim linkage", "officer asked": "cost free receipt", "asked for": "cost fee",
    "no birth certificate": "late registration attestation adult", "records": "who issues registration",
    "visa": "visa", "bank": "bank account", "sim": "sim card linkage",
    "renewal": "renew renewal", "code": "ussd 346 dial retrieve", "misplaced": "lost", "misplace": "lost",
    "customer care": "contact phone call help", "phone number for": "contact call help", "helpline": "contact phone call help",
    "must i": "requirements required", "do i need to": "requirements required", "daughter": "child minor", "son": "child minor",
    "years old": "child age", "website": "online portal", "web site": "online portal", "link": "online portal", "checking": "check retrieve", "dial": "ussd retrieve", "bribe": "tout agent unofficial payment report",
    "what of": "what about",
    "internet": "online portal", "portal": "online portal", "website": "online portal",
}
GLOSSARY.update({
    # Hausa verbs/nouns seen in the audit
    "sace": "stolen lost", "an sace": "stolen", "lasisina": "driver's licence", "katin": "card collect", "karɓi": "collect",
    "karbi": "collect", "shirya": "ready status tracking", "bibiyar": "track status", "bibiya": "track status",
    "kawo": "bring documents", "jariri": "newborn baby child", "mutuwar": "death", "mutuwa": "death", "mahaifina": "father",
    "wane lamba": "what code dial", "kira": "dial call", "ganin": "see check", "ta waya": "phone ussd",
    "sunana": "my name", "canza suna": "change name", "lambar waya": "phone number", "gyaran suna": "name change",
    "shafi": "page booklet", "ta ina zan fara": "where do I start first time", "fara": "start first time",
    "makarantar tuƙi": "driving school", "makarantar tuki": "driving school", "gama": "finished completed",
    "shekaru nawa": "minimum age how old", "shekara": "age years", "ke aiki": "valid validity", "aiki": "valid",
    "kasuwanci": "commercial", "jakadanci": "diplomatic", "manyan motoci": "trucks buses commercial",
    "al'umma": "civil registration", "rajistar al'umma": "civil registration", "wa ke ba da": "who issues",
    "me ake nufi": "what is meaning", "muhimmanci": "important uses", "wuni": "good afternoon hello",
    "ina wuni": "good afternoon hello", "taimako": "help", "madadina": "on my behalf can you", "za ka iya": "can you",
    "sarrafa": "process", "buƙatu": "applications", "bukatu": "applications", "duba": "check", "ofishin shige da fice": "immigration office passport office",
    "shige da fice": "immigration", "kusa da ni": "near me", "ba ni da": "I do not have first time", "ban taba": "never first time new",
    "me za ta kawo": "documents bring", "me zan kawo": "documents bring", "za ta kawo": "documents bring", "karbar kudi": "cost fee free",
    "karɓar kuɗi": "cost fee free", "karbar": "collect", "ba daidai ba": "correction modification", "kore": "green standard",
    "'yar shekara": "child age", "ɗan shekara": "child age", "dan shekara": "child age", "darussan": "driving school lessons",
    "mataki na gaba": "next steps", "walat": "lost stolen", "rasu": "death", "ta rasu": "death certificate", "ya rasu": "death certificate",
    "na haihu": "newborn birth registration", "jaririna": "my baby child", "watan jiya": "expired", "ya kare": "expired renewal",
    # Yoruba
    "ikú": "death", "iku": "death", "ìwé-ẹ̀rí ikú": "death certificate", "iwe eri iku": "death certificate",
    "sọnù": "lost", "sonu": "lost", "pàdánù": "lost", "padanu": "lost", "ti pari": "expired renewal", "pari": "expired renewal",
    "gbàgbé": "forgot retrieve", "gbagbe": "forgot retrieve", "fóònù": "phone ussd", "foonu": "phone ussd",
    "lásìnsì": "licence", "lasinsi": "licence", "lasinsi awako": "driver's licence", "lásìnsì awakọ̀": "driver's licence",
    "awakọ̀": "driver driving", "awako": "driver driving", "ìwé wo": "which documents", "iwe wo": "which documents",
    "nilo fun": "need requirements documents", "nílò fún": "need requirements documents", "ṣé o lè": "can you",
    "se o le": "can you", "tún": "renew", "tun": "renew", "ọmọ kékeré": "child minor", "omo kekere": "child minor",
    "ẹ n lẹ́": "hello", "e n le": "hello", "ẹ káàárọ̀": "good morning hello", "e kaaro": "good morning hello",
    # Igbo
    "ọnwụ": "death", "onwu": "death", "akwụkwọ ọnwụ": "death certificate", "furu efu": "lost", "e zuru": "stolen",
    "agwụla": "expired renewal", "agwula": "expired renewal", "megharịa": "renew renewal", "megharia": "renew renewal",
    "echefuru": "forgot retrieve", "lelee": "check retrieve", "ekwentị": "phone ussd", "ekwenti": "phone ussd",
    "nwata": "child minor", "maka nwa": "for my child minor", "chọrọ": "need requirements", "choro": "need requirements",
    "eweta": "bring documents", "ọnụ ahịa": "price fee cost", "onu ahia": "price fee cost", "usoro": "steps process",
    "inweta": "get obtain", "ị nwere ike": "can you", "i nwere ike": "can you", "kọwaa": "explain what is", "kowaa": "explain what is",
    "kú": "death", "ku": "death", "mú lọ": "bring documents", "mu lo": "bring documents", "fẹ́ ṣe": "wants to do enrol", "fe se": "wants to do enrol",
    "aláwọ̀ ewé": "green standard", "alawo ewe": "green standard", "bí ọmọ": "newborn birth", "bi omo": "newborn birth", "wọ́lẹ́ẹ̀tì": "wallet lost",
    "jí": "stolen", "ji": "stolen", "nwụrụ": "death", "nwuru": "death", "ga-eweta": "documents bring", "ime nin": "enrol NIN",
    "a mụrụ m nwa": "newborn birth registration", "amuru m nwa": "newborn birth registration", "ndụ": "green standard", "zuru": "stolen lost",
    "ime": "do", "eme": "do", "ndewo": "hello", "nweta": "get obtain apply", "enweta": "get obtain", "ga-esi nweta": "how do I get apply",
    "ịrịọ": "apply application", "irio": "apply application", "na-efu": "cost fee", "ọ bụ n'efu": "is it free cost",
    "gba": "get obtain apply", "ṣe lè gba": "how do I get apply", "se le gba": "how do I get apply", "ń gba": "get obtain", "n gba": "get obtain",
    "ìgbésẹ̀": "steps", "igbese": "steps", "jẹ́ ọ̀fẹ́": "is it free cost", "je ofe": "is it free cost", "san owó": "pay fee cost", "san owo": "pay fee cost",
    "modification": "modification", "slip": "slip", "kedu ka ị mere": "hello how are you", "haihuwar": "birth", "yaron": "child", "yarana": "my children", "fasfonka": "passport", "kyauta": "free cost", "matsayin": "status tracking", "matsayi": "status tracking", "duba matsayin": "check status track",
                 "yanar gizo": "online portal internet", "intanet": "online internet", "bukata": "need requirements", "buƙata": "need requirements", "bukatar": "requirements",
                 "lokacin": "time duration", "yaushe": "when time", "ƙare": "expired renewal", "kare": "expired renewal"})

# Nigerian Pidgin vocabulary (kept separate so the audit can trace it).
GLOSSARY.update({
    "dey take": "processing time how long", "how long e dey take": "processing time how long", "e free": "is it free cost",
    "na free": "is free cost", "e cost": "cost fee", "how much be": "how much fee cost", "na how much": "how much fee cost",
    "collect money": "cost fee", "dem dey collect": "cost fee", "pay money": "cost fee", "loss": "lost", "don loss": "lost",
    "e loss": "lost", "don lost": "lost", "steal": "stolen", "dem steal": "stolen", "thief": "stolen", "tiff": "stolen",
    "spoil": "damaged re-issue", "don spoil": "damaged re-issue", "papa": "father", "mama": "mother", "die": "death",
    "don die": "death certificate", "wetin i go do": "what do I do steps", "wetin i need": "documents required",
    "sharp sharp": "fast agent", "quick quick": "fast agent", "fast fast": "fast agent", "run am": "agent fast",
    "wey loss": "lost", "carry go": "documents bring", "my pikin": "my child minor", "small pikin": "child minor",
    "pikin": "child", "born pikin": "newborn birth", "just born": "newborn birth registration", "don old": "adult late",
    "renew am": "renew renewal", "do am": "do apply", "check am": "check retrieve", "see am": "check retrieve",
    "find am": "retrieve", "print am": "print slip", "e don expire": "expired renewal", "don finish": "finished expired",
    "una": "", "oga": "", "sha": "", "o": "", "biko": "", "jare": "", "abeg": "", "sef": "",
})

# SMS spellings and common misspellings, rewritten IN PLACE (token by token) before anything else, so that
# "hw much is d pasport" becomes "how much is the passport" and phrase rules ("how much") still fire.
SMS_MAP: dict[str, str] = {
    "pls": "please", "plz": "please", "pliz": "please", "hw": "how", "hiw": "how", "wat": "what", "wht": "what", "wot": "what",
    "d": "the", "da": "the", "dis": "this", "dat": "that", "u": "you", "ur": "your", "r": "are", "2": "to", "4": "for",
    "gud": "good", "abt": "about", "dnt": "do not", "wen": "when", "wia": "where", "whr": "where", "hv": "have",
    "bcos": "because", "bcoz": "because", "cos": "because", "cert": "certificate", "certs": "certificates", "licens": "licence",
    "lisence": "licence", "liscence": "licence", "licience": "licence", "lincense": "licence", "lincence": "licence",
    "pasport": "passport", "passpot": "passport", "paspot": "passport", "passprt": "passport", "certifcate": "certificate",
    "cerificate": "certificate", "certificat": "certificate", "reg": "registration", "regist": "registration",
    "wanna": "want to", "gonna": "going to", "nd": "and", "n": "and", "&": "and", "thnx": "thanks", "tnx": "thanks",
    "thx": "thanks", "tanks": "thanks", "tank": "thank", "pls.": "please", "abi": "", "ehn": "", "ehen": "",
    "sumtin": "something", "smtin": "something", "nw": "now", "nah": "na", "naa": "na", "kindly": "please", "biz": "business",
    "knw": "know", "kno": "know", "4get": "forget", "4got": "forgot", "4gotten": "forgotten", "dont": "do not",
    "cant": "cannot", "wont": "will not", "didnt": "did not", "doesnt": "does not", "isnt": "is not", "pple": "people",
    "ppl": "people", "nxt": "next", "tmrw": "tomorrow", "2moro": "tomorrow", "yr": "year", "yrs": "years", "b4": "before",
    "renual": "renewal", "renuwal": "renewal", "renewel": "renewal", "renwal": "renewal", "renue": "renew", "renu": "renew",
    "requirment": "requirement", "requirments": "requirements", "registar": "register", "docments": "documents",
    "documets": "documents", "stollen": "stolen", "stolled": "stolen", "lisense": "licence", "modifcation": "modification",
    "oya": "", "mumu": "", "bros": "", "broda": "", "sis": "", "aunty": "", "uncle": "", "sir": "", "ma": "", "madam": "",
}


def normalise_sms(text: str) -> str:
    """Token-level rewrite of SMS spellings. Keeps punctuation; unknown tokens are left as typed."""
    def repl(m: re.Match) -> str:
        w = m.group(0)
        r = SMS_MAP.get(w.lower())
        return w if r is None else r
    out = re.sub(r"(?<![\w'’])[\w&]+(?![\w'’])", repl, text)
    return re.sub(r"\s+", " ", out).strip()


_FOLLOWUP_CUES = {
    "en": {"it", "that", "this", "those", "there", "how much", "how long", "and", "what about", "what of", "also", "same", "one", "is it", "do it", "will it"},
    "ha": {"nawa", "shi", "ita", "wannan", "kuma", "fa", "yaushe", "tsawon", "ina", "wadanne", "kyauta", "nawa ne"},
    "yo": {"èló", "elo", "rẹ̀", "re", "náà", "naa", "ìyẹn", "iyen", "nkọ́", "nko", "èló ni"},
    "ig": {"ego ole", "ya", "nke ahụ", "nke ahu", "kwanụ", "kwanu", "ole"},
    "pcm": {"am", "e", "dat one", "that one", "wetin about", "how about", "na", "sef", "how much", "e free", "e dey"},
}


@dataclass
class Detection:
    language: str
    confidence: float
    scores: dict[str, float]


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _tokens(text: str) -> list[str]:
    return re.findall(r"[\w'ʼ’\-]+", text.lower())


def detect_language(text: str) -> Detection:
    """Lexicon + orthography detector. Returns the most likely supported language with a 0..1 confidence.
    Pidgin is decided first: it reuses English words, so English markers always score high on Pidgin text."""
    toks = _tokens(text)
    if not toks:
        return Detection("en", 0.0, {})
    scores: dict[str, float] = {code: 0.0 for code in SUPPORTED}
    hits_by: dict[str, int] = {}
    for code, marks in _MARKERS.items():
        hits = sum(1 for t in toks if t in marks or _strip_accents(t) in marks)
        hits_by[code] = hits
        scores[code] += hits / max(len(toks), 1)
    cue_langs = set()
    for code, chars in _CHAR_CUES.items():
        n = sum(1 for ch in text if ch in chars)
        if n:
            cue_langs.add(code)
            scores[code] += min(0.6, 0.25 + 0.1 * n)
    if not cue_langs:
        scores["pcm"] = round(pidgin_score(text), 3)
    pcm = scores["pcm"]
    if pcm >= 0.4 and all(scores[c] < pcm or hits_by.get(c, 0) <= 1 for c in ("ha", "yo", "ig")):
        confidence = max(0.5, min(1.0, 0.4 + pcm * 0.5))
        return Detection("pcm", round(confidence, 3), {k: round(v, 3) for k, v in scores.items()})
    best = max(scores, key=lambda c: (scores[c], c != "en"))  # ties go to the indigenous language
    second = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0.0
    margin = scores[best] - second
    confidence = max(0.0, min(1.0, 0.4 + margin * 1.5)) if scores[best] > 0 else 0.0
    if scores[best] == 0:
        best = "en"
    return Detection(best, round(confidence, 3), {k: round(v, 3) for k, v in scores.items()})


def glossary_normalise(text: str) -> str:
    """Replace indigenous-language service terms with English equivalents (longest phrases first).
    Keeps original tokens as well so native-language entries still match lexically."""
    out = text.lower()
    additions: list[str] = []
    consumed = out
    for phrase in sorted(GLOSSARY, key=len, reverse=True):
        pattern = rf"(?<![\w'ʼ’]){re.escape(phrase)}(?![\w'ʼ’])"
        if re.search(pattern, consumed):
            additions.append(GLOSSARY[phrase])
            consumed = re.sub(pattern, " ", consumed)  # avoid matching sub-phrases twice
    if additions:
        out = f"{out} {' '.join(dict.fromkeys(' '.join(additions).split()))}"
    return re.sub(r"\s+", " ", out).strip()


def looks_like_followup(text: str, language: str) -> bool:
    toks = _tokens(text)
    if len(toks) <= 4:
        return True
    low = text.lower()
    cues = _FOLLOWUP_CUES.get(language, set()) | _FOLLOWUP_CUES["en"]
    return any(c in low for c in cues) and len(toks) <= 9


DOMAIN_TOPIC = {
    "nin": "NIN",
    "passport": "passport",
    "drivers_licence": "driver's licence",
    "civil_registration": "birth registration",
    "general": "Tambaya NG",
}


# Object-like sub-topics carried into a follow-up (never intent-like ones such as fees or documents,
# which would override the new question's own intent).
SUBTOPIC = {
    "modify": "modification correction", "renewal": "renewal", "reissue": "lost re-issue", "minor": "child",
    "change": "change of data", "commercial": "commercial", "late": "late registration", "death": "death",
    "slip": "slip", "enrol": "enrolment registration", "fresh": "new application",
}


def build_offline_retrieval_query(message: str, language: str, previous_queries: list[str], previous_domain: str | None = None,
                                  previous_key: str | None = None, followup: bool | None = None) -> str:
    """Offline fallback for step 3 of the algorithm: glossary normalisation plus follow-up context.
    For follow-ups the previous turn's TOPIC (domain terms) is appended, not its whole question, so the
    new intent ("how much", "for my child") stays dominant."""
    q = glossary_normalise(normalise_sms(message) if language in ("en", "pcm") else message)
    low = " " + re.sub(r"[^\w\s'ʼ’ɓɗƙƴẹọṣịụṅàáèéìíòóùúẹ̀ẹ́ọ̀ọ́]+", " ", q.lower()) + " "
    extra = [syn for phrase, syn in EN_SYNONYMS.items() if f" {phrase} " in low]
    if extra:
        q = f"{q} {' '.join(dict.fromkeys(' '.join(extra).split()))}"
    if followup is None:
        followup = looks_like_followup(message, language)
    if (previous_domain or previous_queries) and followup:
        topic = DOMAIN_TOPIC.get(previous_domain or "", "")
        if previous_key:
            parts = previous_key.split("-")[1:]
            topic += " " + " ".join(SUBTOPIC.get(p, "") for p in parts if p in SUBTOPIC)
        if not topic.strip() and previous_queries:
            topic = previous_queries[-1]
        q = f"{q} {topic.strip()}"
    return q[:600]


# The intent part of an entry key, carried into a topic switch ("how much is NIN modification?" then "and passport?").
_KEY_INTENT = {
    "fees": "how much does it cost fee", "cost": "how much does it cost fee", "documents": "documents required",
    "requirements": "requirements documents", "renewal": "renew renewal", "processing": "how long processing time",
    "validity": "how long validity", "minor": "child minor", "reissue": "lost re-issue", "lost": "lost replace",
    "where": "where office", "fresh": "how to apply steps", "enrol": "how to apply steps", "steps": "how to apply steps",
    "register": "how to register", "death": "death", "late": "late registration",
}
_HAS_INTENT = re.compile(r"\b(how much|cost|fee|price|charge|free|documents?|requirements?|need|renew|renewal|expire|how long|"
                         r"lost|loss|stolen|steal|where|office|child|pikin|baby|minor|apply|get|steps?|register|process|"
                         r"nawa|kudi|kuɗi|takardu|èló|elo|owó|ego ole|ụgwọ)\b", re.I)


def carry_intent(message: str, previous_key: str | None) -> str:
    """Intent words to add when the user switches service without stating a new intent."""
    if not previous_key or _HAS_INTENT.search(normalise_sms(message)):
        return ""
    for part in previous_key.split("-")[1:]:
        if part in _KEY_INTENT:
            return _KEY_INTENT[part]
    return ""
