"""Text normalisation and clause splitting for low time-to-first-audio."""

from __future__ import annotations

import re

_CURRENCY = re.compile(r"(?:₹|Rs\.?|INR)\s?([\d,]+(?:\.\d+)?)")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s?%")
_NUMBER = re.compile(r"\b(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?\b")
_CLAUSE_SPLIT = re.compile(r"(?<=[.!?।,;:])\s+|\n+")
# Latin-script tokens (English loanwords / brand names) inside Hindi replies.
_LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'+.-]*")

# High-frequency telephony / banking loanwords → Hindi phonetic spellings.
# Indic-TTS FastPitch's char vocab is Devanagari-only (no a–z), so Latin text
# is otherwise silently dropped.
_LOANWORDS_HI = {
    "whatsapp": "व्हाट्सऐप",
    "teammate": "टीममेट",
    "team": "टीम",
    "mate": "मेट",
    "message": "मैसेज",
    "messages": "मैसेजेस",
    "call": "कॉल",
    "callback": "कॉलबैक",
    "phone": "फोन",
    "mobile": "मोबाइल",
    "email": "ईमेल",
    "sms": "एसएमएस",
    "otp": "ओटीपी",
    "emi": "ईएमआई",
    "loan": "लोन",
    "loans": "लोन्स",
    "bank": "बैंक",
    "fleeca": "फ्लीका",
    "account": "अकाउंट",
    "card": "कार्ड",
    "credit": "क्रेडिट",
    "debit": "डेबिट",
    "payment": "पेमेंट",
    "payments": "पेमेंट्स",
    "pay": "पे",
    "online": "ऑनलाइन",
    "app": "ऐप",
    "apps": "ऐप्स",
    "website": "वेबसाइट",
    "google": "गूगल",
    "facebook": "फेसबुक",
    "instagram": "इंस्टाग्राम",
    "youtube": "यूट्यूब",
    "zoom": "ज़ूम",
    "hello": "हैलो",
    "hi": "हाय",
    "ok": "ओके",
    "okay": "ओके",
    "yes": "येस",
    "no": "नो",
    "please": "प्लीज़",
    "sorry": "सॉरी",
    "thanks": "थैंक्स",
    "thank": "थैंक",
    "you": "यू",
    "sir": "सर",
    "madam": "मैडम",
    "miss": "मिस",
    "manager": "मैनेजर",
    "agent": "एजेंट",
    "customer": "कस्टमर",
    "support": "सपोर्ट",
    "service": "सर्विस",
    "number": "नंबर",
    "name": "नेम",
    "address": "एड्रेस",
    "pin": "पिन",
    "code": "कोड",
    "link": "लिंक",
    "form": "फॉर्म",
    "document": "डॉक्यूमेंट",
    "documents": "डॉक्यूमेंट्स",
    "kyc": "केवाईसी",
    "pan": "पैन",
    "aadhaar": "आधार",
    "aadhar": "आधार",
    "rupee": "रुपया",
    "rupees": "रुपये",
    "percent": "परसेंट",
    "percentage": "परसेंटेज",
    "interest": "इंटरेस्ट",
    "rate": "रेट",
    "offer": "ऑफर",
    "scheme": "स्कीम",
    "plan": "प्लान",
    "update": "अपडेट",
    "confirm": "कन्फर्म",
    "confirmation": "कन्फर्मेशन",
    "verified": "वेरिफाइड",
    "verify": "वेरिफाई",
    "option": "ऑप्शन",
    "options": "ऑप्शन्स",
    "minute": "मिनट",
    "minutes": "मिनट्स",
    "second": "सेकंड",
    "seconds": "सेकंड्स",
    "today": "टुडे",
    "tomorrow": "टुमॉरो",
    "morning": "मॉर्निंग",
    "evening": "ईवनिंग",
    "night": "नाइट",
    "weekend": "वीकेंड",
    "office": "ऑफिस",
    "branch": "ब्रांच",
    "chat": "चैट",
    "video": "वीडियो",
    "audio": "ऑडियो",
    "file": "फाइल",
    "pdf": "पीडीएफ",
    "id": "आईडी",
    "ai": "एआई",
    "bot": "बॉट",
    "voice": "वॉइस",
    "recording": "रिकॉर्डिंग",
}


_ONES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _en_under_1000(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n < 100:
        t, o = divmod(n, 10)
        return _TENS[t] + (f" {_ONES[o]}" if o else "")
    h, r = divmod(n, 100)
    return _ONES[h] + " hundred" + (f" {_en_under_1000(r)}" if r else "")


def number_to_english(n: int) -> str:
    if n < 0:
        return "minus " + number_to_english(-n)
    if n < 1000:
        return _en_under_1000(n)
    if n < 100_000:
        th, r = divmod(n, 1000)
        return number_to_english(th) + " thousand" + (f" {number_to_english(r)}" if r else "")
    if n < 10_000_000:
        lakh, r = divmod(n, 100_000)
        return number_to_english(lakh) + " lakh" + (f" {number_to_english(r)}" if r else "")
    cr, r = divmod(n, 10_000_000)
    return number_to_english(cr) + " crore" + (f" {number_to_english(r)}" if r else "")


# Full 0–99 Hindi cardinals. Digit-by-digit ("दो एक" for 21) sounds wrong on
# age/tenure lines; Indic-TTS needs the spoken form ("इक्कीस").
_HI_0_99 = [
    "शून्य",
    "एक",
    "दो",
    "तीन",
    "चार",
    "पाँच",
    "छह",
    "सात",
    "आठ",
    "नौ",
    "दस",
    "ग्यारह",
    "बारह",
    "तेरह",
    "चौदह",
    "पंद्रह",
    "सोलह",
    "सत्रह",
    "अठारह",
    "उन्नीस",
    "बीस",
    "इक्कीस",
    "बाईस",
    "तेईस",
    "चौबीस",
    "पच्चीस",
    "छब्बीस",
    "सत्ताईस",
    "अट्ठाईस",
    "उनतीस",
    "तीस",
    "इकतीस",
    "बत्तीस",
    "तैंतीस",
    "चौंतीस",
    "पैंतीस",
    "छत्तीस",
    "सैंतीस",
    "अड़तीस",
    "उनतालीस",
    "चालीस",
    "इकतालीस",
    "बयालीस",
    "तैंतालीस",
    "चवालीस",
    "पैंतालीस",
    "छियालीस",
    "सैंतालीस",
    "अड़तालीस",
    "उनचास",
    "पचास",
    "इक्यावन",
    "बावन",
    "तिरपन",
    "चौवन",
    "पचपन",
    "छप्पन",
    "सत्तावन",
    "अट्ठावन",
    "उनसठ",
    "साठ",
    "इकसठ",
    "बासठ",
    "तिरसठ",
    "चौंसठ",
    "पैंसठ",
    "छियासठ",
    "सड़सठ",
    "अड़सठ",
    "उनहत्तर",
    "सत्तर",
    "इकहत्तर",
    "बहत्तर",
    "तिहत्तर",
    "चौहत्तर",
    "पचहत्तर",
    "छिहत्तर",
    "सतत्तर",
    "अठहत्तर",
    "उनासी",
    "अस्सी",
    "इक्यासी",
    "बयासी",
    "तिरासी",
    "चौरासी",
    "पचासी",
    "छियासी",
    "सतासी",
    "अठासी",
    "नवासी",
    "नब्बे",
    "इक्यानवे",
    "बानवे",
    "तिरानवे",
    "चौरानवे",
    "पचानवे",
    "छियानवे",
    "सत्तानवे",
    "अट्ठानवे",
    "निन्यानवे",
]

# Devanagari digits → ASCII so "२१" expands like "21".
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def number_to_hindi(n: int) -> str:
    if n < 0:
        return "माइनस " + number_to_hindi(-n)
    if n < 100:
        return _HI_0_99[n]
    if n < 1000:
        h, r = divmod(n, 100)
        head = number_to_hindi(h) + " सौ"
        return head + (f" {number_to_hindi(r)}" if r else "")
    if n < 100_000:
        th, r = divmod(n, 1000)
        head = number_to_hindi(th) + " हज़ार"
        return head + (f" {number_to_hindi(r)}" if r else "")
    if n < 10_000_000:
        lakh, r = divmod(n, 100_000)
        head = number_to_hindi(lakh) + " लाख"
        return head + (f" {number_to_hindi(r)}" if r else "")
    cr, r = divmod(n, 10_000_000)
    head = number_to_hindi(cr) + " करोड़"
    return head + (f" {number_to_hindi(r)}" if r else "")


def _latin_to_devanagari(word: str) -> str:
    """Approximate English→Hindi phonetics for out-of-vocab Latin tokens.

    Indic-TTS FastPitch only knows Devanagari glyphs; unknown Latin letters are
    discarded. This is a lightweight grapheme map tuned for Indian-English
    loanwords (not a full G2P). Prefer ``_LOANWORDS_HI`` for important terms.
    """
    w = word.lower().strip("'+.-")
    if not w:
        return word
    # Letter names for single Latin initials (EMI → handled via loanwords; A → ए).
    if len(w) == 1 and w.isalpha():
        return {
            "a": "ए",
            "b": "बी",
            "c": "सी",
            "d": "डी",
            "e": "ई",
            "f": "एफ",
            "g": "जी",
            "h": "एच",
            "i": "आई",
            "j": "जे",
            "k": "के",
            "l": "एल",
            "m": "एम",
            "n": "एन",
            "o": "ओ",
            "p": "पी",
            "q": "क्यू",
            "r": "आर",
            "s": "एस",
            "t": "टी",
            "u": "यू",
            "v": "वी",
            "w": "डब्ल्यू",
            "x": "एक्स",
            "y": "वाई",
            "z": "ज़ेड",
        }.get(w, w)

    # Consonant digraphs / endings first (longest match).
    cons_rules = (
        ("tion", "शन"),
        ("sion", "शन"),
        ("sch", "स्क"),
        ("tch", "च"),
        ("wh", "व्ह"),
        ("th", "थ"),
        ("sh", "श"),
        ("ch", "च"),
        ("ph", "फ"),
        ("gh", "ग"),
        ("ck", "क"),
        ("ng", "ंग"),
        ("qu", "क्व"),
    )
    # Vowel groups → (independent, matra)
    vowel_rules = (
        ("ee", "ई", "ी"),
        ("oo", "ऊ", "ू"),
        ("aa", "आ", "ा"),
        ("ii", "ई", "ी"),
        ("uu", "ऊ", "ू"),
        ("ai", "ऐ", "ै"),
        ("ay", "ए", "े"),
        ("au", "औ", "ौ"),
        ("aw", "ऑ", "ॉ"),
        ("oi", "ऑइ", "ॉइ"),
        ("oy", "ऑइ", "ॉइ"),
        ("ou", "आउ", "ाउ"),
        ("ow", "आउ", "ाउ"),
        ("ea", "ई", "ी"),
        ("oa", "ओ", "ो"),
        ("ie", "ई", "ी"),
        ("ei", "ए", "े"),
        ("ue", "यू", "ू"),
        ("a", "अ", "ा"),
        ("e", "ए", "े"),
        ("i", "इ", "ि"),
        ("o", "ओ", "ो"),
        ("u", "उ", "ु"),
    )
    consonants = {
        "b": "ब",
        "c": "क",
        "d": "द",
        "f": "फ",
        "g": "ग",
        "h": "ह",
        "j": "ज",
        "k": "क",
        "l": "ल",
        "m": "म",
        "n": "न",
        "p": "प",
        "q": "क",
        "r": "र",
        "s": "स",
        "t": "ट",
        "v": "व",
        "w": "व",
        "x": "क्स",
        "y": "य",
        "z": "ज़",
    }

    out: list[str] = []
    i = 0
    prev_consonant = False
    while i < len(w):
        if w[i].isdigit():
            out.append(w[i])
            prev_consonant = False
            i += 1
            continue
        matched = False
        for src, dst in cons_rules:
            if w.startswith(src, i):
                out.append(dst)
                prev_consonant = True
                i += len(src)
                matched = True
                break
        if matched:
            continue
        for src, indep, matra in vowel_rules:
            if w.startswith(src, i):
                out.append(matra if prev_consonant else indep)
                prev_consonant = False
                i += len(src)
                matched = True
                break
        if matched:
            continue
        ch = w[i]
        if ch in consonants:
            out.append(consonants[ch])
            prev_consonant = True
            i += 1
            continue
        i += 1
    return "".join(out) or word


def latin_loanwords_to_hindi(text: str) -> str:
    """Replace Latin-script tokens with Devanagari so Indic-TTS can speak them."""

    def repl(m: re.Match) -> str:
        raw = m.group(0)
        key = raw.lower().strip("'+.-")
        if key in _LOANWORDS_HI:
            return _LOANWORDS_HI[key]
        # CamelCase / brand splits: WhatsApp → already whole-word; TeamMate → teammate via lower.
        return _latin_to_devanagari(raw)

    return _LATIN_WORD.sub(repl, text)


def normalize(text: str, language: str = "hi") -> str:
    text = " ".join((text or "").split())
    if not text:
        return ""
    # Campaign / LLM text often mixes Devanagari numerals (२१) with ASCII (21).
    text = text.translate(_DEVANAGARI_DIGITS)
    lang = (language or "hi").lower()
    to_words = number_to_english if lang.startswith("en") else number_to_hindi
    decimal_word = "point" if lang.startswith("en") else "दशमलव"

    def currency(m: re.Match) -> str:
        raw = m.group(1).replace(",", "")
        whole = int(float(raw))
        if lang.startswith("en"):
            return f"{to_words(whole)} rupees"
        return f"{to_words(whole)} रुपये"

    text = _CURRENCY.sub(currency, text)

    def percent(m: re.Match) -> str:
        raw = m.group(1)
        if "." in raw:
            whole, frac = raw.split(".", 1)
            spoken = (
                f"{to_words(int(whole))} {decimal_word} "
                f"{' '.join(to_words(int(d)) for d in frac if d.isdigit())}"
            )
        else:
            spoken = to_words(int(raw))
        return f"{spoken} percent" if lang.startswith("en") else f"{spoken} प्रतिशत"

    text = _PERCENT.sub(percent, text)

    def number(m: re.Match) -> str:
        whole = int(m.group(1).replace(",", ""))
        frac = m.group(2)
        spoken = to_words(whole)
        if frac:
            spoken += f" {decimal_word} " + " ".join(to_words(int(d)) for d in frac)
        return spoken

    text = _NUMBER.sub(number, text)
    # Hindi FastPitch cannot emit Latin glyphs — transliterate loanwords.
    if lang.startswith("hi"):
        text = latin_loanwords_to_hindi(text)
        text = text.replace("।", ".")
    return text


def split_clauses(text: str, first_max_words: int = 8) -> list[str]:
    """Split for pipelined TTS: first clause short for fast first audio."""
    text = " ".join((text or "").split())
    if not text:
        return []
    parts = [p.strip() for p in _CLAUSE_SPLIT.split(text) if p and p.strip()]
    if not parts:
        parts = [text]

    first = parts[0]
    words = first.split()
    if len(words) > first_max_words:
        head = " ".join(words[:first_max_words])
        tail = " ".join(words[first_max_words:])
        rest = ([tail] if tail else []) + parts[1:]
        return [head, *rest]
    return parts
