"""Pull a name, a date, or a time out of one spoken turn.

The booking steps ask for one of these at a time. A turn that does not
contain that piece stays on the same step.
"""

from __future__ import annotations

import datetime
import re

from spoken_numbers import number_to_hindi

_NOT_A_NAME = {
    "hello", "hi", "hey", "namaste", "नमस्ते", "नमस्कार", "good morning",
    "good evening", "appointment", "booking", "book",
}
# Noise the recognizer inserts, such as "And you've included" or "Maybe", is not a name.
_NOT_NAME_WORD = {
    "a", "an", "and", "the", "you", "you've", "youve", "your", "included", "include",
    "have", "has", "had", "this", "that", "what", "with", "from", "for", "are", "was",
    "were", "been", "please", "hello", "yes", "no", "ok", "okay", "change", "to", "of",
    "it", "its", "it's", "i", "me", "my", "we", "they", "just", "only", "also",
    "maybe", "sorry", "wait", "thanks", "thank", "धन्यवाद",
}
# Words around a name. "मेरा नाम बदलकर निधि कर दो" still has the name निधि.
# "Hey, then, um, hey. आकाश चोपड़ा" is still आकाश चोपड़ा. "आपका" and "इतना" are not a name.
_NAME_FILLER = {
    "मेरा", "mera", "my", "नाम", "naam", "name", "is",
    "कर", "kar", "दो", "do", "दीजिए", "dijiye", "बताइए",
    "बदलकर", "बदल", "badal", "change", "please", "प्लीज",
    "रख", "रखना", "करना", "चाहिए",
    "ठीक", "theek", "thik", "सही", "sahi", "हाँ", "हां", "नहीं", "नही",
    "में", "mein", "रहन", "रहना", "रहता", "रहती", "रहते", "rehna", "rehta",
    "का", "की", "के", "को", "से", "पर", "पे", "जी", "ji",
    "है", "hai", "हूँ", "हूं", "hoon", "hun", "hu",
    "पूरा", "पूरी", "पूरे", "full", "complete",
    "आपका", "आपकी", "आपके", "आप", "अपना", "अपनी", "अपने", "aapka", "aap",
    "इतना", "इतनी", "इतने", "ऐसा", "ऐसी", "ऐसे", "यह", "ये", "वो", "वह",
    "तो", "बस", "sir", "madam", "yaar", "यार", "first", "last",
    "hey", "hi", "hello", "um", "uh", "hmm", "hm", "er", "ah", "oh",
    "then", "so", "like", "actually", "well", "yeah", "yep", "ok", "okay", "right",
}
# "क्या नाम अनिल है" is a name, not a question to ignore.
_NAME_IN_QUESTION = re.compile(
    r"^(?:क्या\s+)?(?:मेरा\s+|mera\s+|my\s+)?(?:नाम|name|naam)\s+(.+)$",
    re.IGNORECASE,
)
_NAME_AFTER_CHANGE = re.compile(
    r"(?:बदल\s*कर|बदल\s*के|badal\s*kar|change\s+to)\s+(.+)$",
    re.IGNORECASE,
)
_YES = re.compile(
    r"^(?:yes|yeah|yep|sure|ok|okay|haan|ha|ji|हाँ|हां|जी|ठीक|ठीक है|बिल्कुल)[\s.!?।]*$",
    re.IGNORECASE,
)
_NO = re.compile(
    r"^(?:no|nope|nah|nahi|nahin|na|नहीं|ना|नही)[\s.!?।]*$",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"(\?|क्या|कौन|कब|कैसे|क्यों|कितन|what|who|when|where|why|how)",
    re.IGNORECASE,
)
_NAME_LEAD = re.compile(
    r"^(?:मेरा नाम|नाम मेरा|mera naam|mera name|my name is|i am|i'm|this is|main|मैं)\s+",
    re.IGNORECASE,
)
# "है" ends in a vowel sign, which is not a word character, so \b never sees the end of it.
_NAME_TAIL = re.compile(
    r"(?:[\s,]+(?:"
    r"हूँ|हूं|है|hai|hoon|hun|hu|"
    r"bol raha hoon|bol rahi hoon|बोल रहा हूँ|बोल रहा हूं|बोल रही हूँ|speaking"
    r"))+[\s.!?।]*$",
    re.IGNORECASE,
)

_MONTHS = {
    "january": 1, "jan": 1, "जनवरी": 1,
    "february": 2, "feb": 2, "फरवरी": 2,
    "march": 3, "mar": 3, "मार्च": 3,
    "april": 4, "apr": 4, "अप्रैल": 4,
    "may": 5, "मई": 5,
    "june": 6, "jun": 6, "जून": 6,
    "july": 7, "jul": 7, "जुलाई": 7,
    "august": 8, "aug": 8, "अगस्त": 8,
    "september": 9, "sep": 9, "sept": 9, "सितंबर": 9, "सितम्बर": 9,
    "october": 10, "oct": 10, "अक्टूबर": 10, "अक्तूबर": 10,
    "november": 11, "nov": 11, "नवंबर": 11, "नवम्बर": 11,
    "december": 12, "dec": 12, "दिसंबर": 12, "दिसम्बर": 12,
}
_MONTH_PATTERN = "|".join(sorted(_MONTHS, key=len, reverse=True))
_DATE_TEXT = re.compile(rf"(\d{{1,2}})\s+({_MONTH_PATTERN})\b", re.IGNORECASE)
_DATE_NUM = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b")
_TODAY = re.compile(r"\b(?:today|aaj|आज)\b", re.IGNORECASE)
_TOMORROW = re.compile(r"\b(?:tomorrow|kal|कल)\b", re.IGNORECASE)
_DAY_AFTER = re.compile(r"\b(?:day after tomorrow|parson|परसों)\b", re.IGNORECASE)

_CLOCK = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?\b",
    re.IGNORECASE,
)
_BAJE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(?:baje|बजे)")
_PERIOD = re.compile(r"(सुबह|दोपहर|शाम|रात|morning|afternoon|evening|night|am|pm|a\.m\.|p\.m\.)", re.IGNORECASE)
_HOUR_WORDS = {
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5,
    "छह": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10, "ग्यारह": 11, "बारह": 12,
    "das": 10, "dus": 10, "gyarah": 11, "gyaarah": 11, "barah": 12, "baarah": 12,
    "ek": 1, "do": 2, "teen": 3, "tin": 3, "char": 4, "chaar": 4,
    "paanch": 5, "panch": 5, "chhe": 6, "che": 6, "saat": 7, "sat": 7,
    "aath": 8, "nau": 9,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
}
_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def is_question(text: str) -> bool:
    return _QUESTION.search(text or "") is not None


def _devanagari_word(word: str) -> bool:
    return bool(word) and all("\u0900" <= character <= "\u097f" for character in word)


def _latin_word(word: str) -> bool:
    return bool(word) and all(character.isascii() and character.isalpha() for character in word)


def _name_words(words: list[str]) -> list[str]:
    """Keep the name and drop the recognizer's ums, heys, and आपका/इतना."""
    kept = []
    for word in words:
        folded = word.casefold()
        if folded in _NAME_FILLER or folded in _NOT_NAME_WORD or folded in _NOT_A_NAME:
            continue
        if _devanagari_word(word) or _latin_word(word):
            kept.append(word)
    devanagari = [word for word in kept if _devanagari_word(word)]
    # "Hey, um, आकाश चोपड़ा" is the Hindi name. A fully English "akaash chopra" stays English.
    if len(devanagari) >= 2:
        return devanagari
    return kept


def extract_name(text: str) -> str | None:
    raw = " ".join((text or "").replace("।", " ").replace("?", " ").replace("!", " ").split())
    if not raw or _YES.match(raw) or _NO.match(raw):
        return None
    asked = _NAME_IN_QUESTION.match(raw)
    if asked:
        raw = asked.group(1).strip()
    elif is_question(raw):
        return None
    if _TODAY.search(raw) or _TOMORROW.search(raw) or _DATE_TEXT.search(raw) or _DATE_NUM.search(raw):
        return None
    moved = _NAME_AFTER_CHANGE.search(raw)
    if moved:
        raw = moved.group(1)
    cleaned = _NAME_LEAD.sub("", raw)
    cleaned = _NAME_TAIL.sub("", cleaned).strip(" .,")
    if cleaned.casefold() in _NOT_A_NAME:
        return None
    words = [word.strip(".,'’") for word in cleaned.split() if word.strip(".,'’")]
    words = _name_words(words)
    if not words or len(words) > 4:
        return None
    if any(character.isdigit() for word in words for character in word):
        return None
    return " ".join(words)


def name_is_clear(name: str) -> bool:
    """A first and last name. Hindi or English letters both count. One word does not."""
    words = [word for word in (name or "").split() if word]
    if len(words) < 2:
        return False
    for word in words:
        if word.casefold() in _NAME_FILLER or word.casefold() in _NOT_NAME_WORD or len(word) < 2:
            return False
        if not (_devanagari_word(word) or _latin_word(word)):
            return False
    return True


# Spoken days, longest first so चौबीस matches before चार and twenty fourth before fourth.
_HI_DAYS = (
    ("इकतीस", 31), ("उनतीस", 29), ("अट्ठाईस", 28), ("अठ्ठाईस", 28), ("सत्ताईस", 27),
    ("छब्बीस", 26), ("पच्चीस", 25), ("चौबीस", 24), ("तेईस", 23), ("बाईस", 22),
    ("इक्कीस", 21), ("उन्नीस", 19), ("अठारह", 18), ("सत्रह", 17), ("सोलह", 16),
    ("पंद्रह", 15), ("पन्द्रह", 15), ("चौदह", 14), ("तेरह", 13), ("ग्यारह", 11),
    ("बारह", 12), ("तीस", 30), ("बीस", 20), ("बाइस", 22), ("नौ", 9), ("आठ", 8), ("सात", 7),
    ("छह", 6), ("पांच", 5), ("पाँच", 5), ("चार", 4), ("तीन", 3), ("दो", 2),
    ("दस", 10), ("एक", 1),
)
_EN_DAYS = (
    ("thirty first", 31), ("thirty-first", 31),
    ("twenty ninth", 29), ("twenty-ninth", 29), ("twenty eighth", 28), ("twenty-eighth", 28),
    ("twenty seventh", 27), ("twenty-seventh", 27), ("twenty sixth", 26), ("twenty-sixth", 26),
    ("twenty fifth", 25), ("twenty-fifth", 25), ("twenty fourth", 24), ("twenty-fourth", 24),
    ("twenty third", 23), ("twenty-third", 23), ("twenty second", 22), ("twenty-second", 22),
    ("twenty first", 21), ("twenty-first", 21),
    ("nineteenth", 19), ("eighteenth", 18), ("seventeenth", 17), ("sixteenth", 16),
    ("fifteenth", 15), ("fourteenth", 14), ("thirteenth", 13), ("twelfth", 12),
    ("eleventh", 11), ("thirtieth", 30), ("twentieth", 20), ("tenth", 10),
    ("ninth", 9), ("eighth", 8), ("seventh", 7), ("sixth", 6), ("fifth", 5),
    ("fourth", 4), ("third", 3), ("second", 2), ("first", 1),
    ("thirty", 30), ("twenty", 20),
)
_DAY_DIGIT = re.compile(r"(?<!\d)(\d{1,2})(?:st|nd|rd|th)?(?!\d)", re.IGNORECASE)
_DATE_WORD = re.compile(r"तारीख|tarikh|date", re.IGNORECASE)
_TIME_WORD = re.compile(r"बजे|baje|सुबह|शाम|दोपहर|रात|morning|evening|\bam\b|\bpm\b", re.IGNORECASE)


def _plain(text: str) -> str:
    return (text or "").replace("\u093c", "")


def extract_date(text: str, today: datetime.date) -> str | None:
    raw = _plain(text)
    if _TODAY.search(raw):
        return today.isoformat()
    if _DAY_AFTER.search(raw):
        return (today + datetime.timedelta(days=2)).isoformat()
    if _TOMORROW.search(raw):
        return (today + datetime.timedelta(days=1)).isoformat()
    named = _DATE_TEXT.search(raw)
    if named:
        day = int(named.group(1))
        month = _MONTHS[named.group(2).lower()]
        return _safe_date(today.year, month, day, today)
    numeric = _DATE_NUM.search(raw)
    if numeric:
        day = int(numeric.group(1))
        month = int(numeric.group(2))
        year = int(numeric.group(3)) if numeric.group(3) else today.year
        if year < 100:
            year += 2000
        return _safe_date(year, month, day, today)
    # "दो हज़ार चौबीस" is the year 2024, not the 24th of this month.
    spoken_year, year_span = _spoken_year(raw)
    date_text = raw
    if year_span is not None:
        date_text = raw[: year_span[0]] + " " + raw[year_span[1] :]
    month = _month_in(date_text)
    day = _spoken_day(date_text, month)
    if day is None:
        if spoken_year is not None and spoken_year < today.year:
            return "past"
        return None
    if month is None:
        # "सुबह दस बजे" is a time. A bare day still counts when they are giving a date.
        if _TIME_WORD.search(raw) and not _DATE_WORD.search(raw):
            return None
        if not _DATE_WORD.search(raw) and len(raw.split()) > 4:
            return None
        year, month_number = today.year, today.month
        try:
            if datetime.date(year, month_number, day) < today:
                month_number += 1
                if month_number == 13:
                    month_number, year = 1, year + 1
        except ValueError:
            return None
        return _safe_date(year, month_number, day, today)
    return _safe_date(spoken_year or today.year, month, day, today)


_YEAR_PHRASE = re.compile(
    r"(?:दो\s*हजार|do\s*hazar|2\s*hazar|two\s*thousand)\s+"
    r"((?:twenty[\s-]+)?(?:\d{1,2}|[A-Za-z\u0900-\u097F]+))",
    re.IGNORECASE,
)
_YEAR_NUM = re.compile(r"\b(20\d{2})\b")
_YEAR_TAIL = {
    "chaubi": 24, "chaubis": 24, "chaubees": 24,
    "chhabbis": 26, "chabbis": 26,
    "pachchis": 25, "pachees": 25,
    "teis": 23, "baees": 22, "ikkis": 21,
    "twenty four": 24, "twenty six": 26, "twenty five": 25,
    "twenty three": 23, "twenty two": 22, "twenty one": 21, "twenty": 20,
}
_THOUSAND_AFTER = re.compile(r"\s*(?:हजार|hazar|thousand)\b", re.IGNORECASE)


def _spoken_year(text: str) -> tuple[int | None, tuple[int, int] | None]:
    """A year such as दो हजार चौबीस or 2 hazar chaubis. Not a day of the month."""
    plain = _plain(text)
    match = _YEAR_PHRASE.search(plain)
    if match:
        token = match.group(1).strip().casefold().replace("-", " ")
        offset = _YEAR_TAIL.get(token)
        if offset is None and token.isdigit() and int(token) <= 99:
            offset = int(token)
        if offset is None:
            for word, number in _HI_DAYS:
                if match.group(1).strip() == word and number <= 99:
                    offset = number
                    break
        if offset is not None:
            return 2000 + offset, (match.start(), match.end())
    digit = _YEAR_NUM.search(plain)
    if digit:
        return int(digit.group(1)), (digit.start(), digit.end())
    return None, None


def _month_in(text: str) -> int | None:
    for name in sorted(_MONTHS, key=len, reverse=True):
        if re.search(rf"(?<![A-Za-z\u0900-\u097F]){re.escape(name)}(?![A-Za-z\u0900-\u097F])", text, re.IGNORECASE):
            return _MONTHS[name]
    return None


def _spoken_day(text: str, month: int | None) -> int | None:
    found = []
    for word, day in _HI_DAYS:
        match = re.search(rf"(?<![\u0900-\u097F]){re.escape(word)}(?![\u0900-\u097F])", text)
        if match:
            found.append((match.start(), match.end(), day))
    folded = text.lower()
    for word, day in _EN_DAYS:
        match = re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", folded)
        if match:
            found.append((match.start(), match.end(), day))
    for match in _DAY_DIGIT.finditer(text):
        day = int(match.group(1))
        if 1 <= day <= 31:
            found.append((match.start(), match.end(), day))
    found = [
        item for item in found
        if not any(other[0] <= item[0] and other[1] >= item[1] and other[1] - other[0] > item[1] - item[0] for other in found)
    ]
    if not found:
        return None
    anchor = None
    if month is not None:
        for name, number in _MONTHS.items():
            if number == month:
                at = folded_find(text, name)
                if at is not None:
                    anchor = at
                    break
    if anchor is None:
        word = _DATE_WORD.search(text)
        anchor = word.start() if word else None
    if anchor is not None:
        before = [item for item in found if item[0] <= anchor]
        if before:
            return max(before, key=lambda item: item[0])[2]
    return found[0][2]


def folded_find(text: str, name: str) -> int | None:
    match = re.search(re.escape(name), text, re.IGNORECASE)
    return match.start() if match else None


_HALF = re.compile(
    r"साढ़े|साढे|साडे|(?<![A-Za-z])(?:saadhe|saade|sadhe|sade|started|start)(?![A-Za-z])",
    re.IGNORECASE,
)
_SAWA = re.compile(r"सवा|(?<![A-Za-z])(?:sawa|savva)(?![A-Za-z])", re.IGNORECASE)
_PAUNE = re.compile(r"पौने|(?<![A-Za-z])(?:paune|pone)(?![A-Za-z])", re.IGNORECASE)
_DEDH = re.compile(r"डेढ़|डेढ|(?<![A-Za-z])(?:dedh|derh|ded)(?![A-Za-z])", re.IGNORECASE)
_MINUTE_WORDS = (
    ("पैंतालीस", 45), ("पैतालीस", 45),
    ("पन्द्रह", 15), ("पंद्रह", 15), ("pandrah", 15), ("pandrah", 15),
    ("तीस", 30), ("tees", 30),
)
_OFFSET_MIN = re.compile(
    r"(?:बजकर|बज\s*के|baje?\s*ke|bajkar)\s*(\d{1,2}|तीस|पंद्रह|पन्द्रह|पैंतालीस|पैतालीस)",
    re.IGNORECASE,
)
_MIN_NUM = re.compile(r"(\d{1,2})\s*(?:mins?|minutes?|मिनट)", re.IGNORECASE)


def _word_at(text: str, word: str):
    return re.search(
        rf"(?<![\w\u0900-\u097F]){re.escape(word)}(?![\w\u0900-\u097F])",
        text,
        re.IGNORECASE,
    )


def _as_minute(token: str) -> int | None:
    token = (token or "").strip()
    for word, minute in _MINUTE_WORDS:
        if token.casefold() == word.casefold():
            return minute
    if token.isdigit():
        minute = int(token)
        if 0 <= minute <= 59:
            return minute
    return None


def _hour_word(text: str) -> tuple[int, int] | None:
    found = []
    for word, hour in sorted(_HOUR_WORDS.items(), key=lambda item: len(item[0]), reverse=True):
        match = _word_at(text, word)
        if match and _THOUSAND_AFTER.match(_plain(text[match.end():])) is None:
            found.append((match.start(), match.end(), hour))
    found = [
        item for item in found
        if not any(other[0] <= item[0] and other[1] >= item[1] and other[1] - other[0] > item[1] - item[0] for other in found)
    ]
    if not found:
        return None
    start, end, hour = min(found)
    return hour, end


def _clock_parts(raw: str) -> tuple[int, int] | None:
    minute = None
    offset = _OFFSET_MIN.search(raw)
    if offset:
        minute = _as_minute(offset.group(1))
    else:
        numbered = _MIN_NUM.search(raw)
        if numbered:
            minute = _as_minute(numbered.group(1))
    spoken = _hour_word(raw)
    if spoken:
        hour, end = spoken
        if minute is None:
            for word, value in _MINUTE_WORDS:
                match = _word_at(raw, word)
                if match and match.start() >= end:
                    minute = value
                    break
        if minute is None:
            extra = re.match(r"\s+(\d{1,2})\b", raw[end:])
            if extra and 0 < int(extra.group(1)) <= 59:
                minute = int(extra.group(1))
        return hour, 0 if minute is None else minute
    match = _CLOCK.search(raw) or _BAJE.search(raw)
    if match is not None and _THOUSAND_AFTER.match(_plain(raw[match.end():])):
        match = None
    if match is None:
        return None
    hour = int(match.group(1))
    clock_minute = int(match.group(2) or 0)
    if minute is not None:
        clock_minute = minute
    elif match.group(2) is None:
        extra = re.match(r"\s*(\d{1,2})\b", raw[match.end():])
        if extra and 0 < int(extra.group(1)) <= 59:
            clock_minute = int(extra.group(1))
    return hour, clock_minute


def extract_time(text: str) -> tuple[str, str] | None:
    """Return ('time', 'HH:MM') or ('ambiguous', 'H:MM') when morning or evening is missing."""
    raw = text or ""
    period = _period(raw)
    if _DEDH.search(raw) and _hour_word(raw) is None:
        return _finish_time(1, 30, period, word_only=True)
    parts = _clock_parts(raw)
    if parts is None:
        return None
    _, year_span = _spoken_year(raw)
    if year_span is not None and _clock_parts(raw[: year_span[0]] + " " + raw[year_span[1] :]) is None:
        return None
    hour, minute = parts
    if _HALF.search(raw):
        minute = 30
    elif _SAWA.search(raw):
        minute = 15
    elif _PAUNE.search(raw):
        minute = 45
        hour = 12 if hour == 1 else hour - 1
    if minute > 59 or hour > 23 or hour < 0:
        return None
    if hour > 12:
        return ("time", f"{hour:02d}:{minute:02d}")
    return _finish_time(hour, minute, period, word_only=False)


def apply_period(pending: str, text: str) -> str | None:
    period = _period(text)
    if not period or not pending:
        return None
    hour_text, minute_text = pending.split(":")
    finished = _finish_time(int(hour_text), int(minute_text), period, word_only=False)
    if finished and finished[0] == "time":
        return finished[1]
    return None


def changed_confirmation(previous: dict, name: str, date_iso: str, time_hm: str) -> tuple[bool, str]:
    """Speak only the detail that changed. The first booking still uses confirmation()."""
    previous = previous or {}
    same_date = previous.get("date") == date_iso
    same_time = previous.get("time") == time_hm
    parts = []
    if not same_date:
        year, month, day = (int(part) for part in date_iso.split("-"))
        parts.append(f"तारीख {number_to_hindi(day)} {_MONTH_NAMES[month]} कर दी है।")
    if not same_time:
        hour, minute = (int(part) for part in time_hm.split(":"))
        parts.append(f"समय {_speak_clock(hour, minute)} कर दिया है।")
    if same_date and same_time:
        parts.append(f"नाम {name} कर दिया है।")
    question = "ठीक है?"
    return (not same_date or not same_time), " ".join(parts) + " " + question


def confirmation(name: str, date_iso: str, time_hm: str) -> str:
    year, month, day = (int(part) for part in date_iso.split("-"))
    hour, minute = (int(part) for part in time_hm.split(":"))
    spoken_day = number_to_hindi(day)
    spoken_time = _speak_clock(hour, minute)
    return (
        f"आपका appointment book हो गया है। नाम {name} है। "
        f"तारीख {spoken_day} {_MONTH_NAMES[month]} {number_to_hindi(year)} है। "
        f"समय {spoken_time} है। यह Yugaantar conference में chairperson से मिलने का appointment है। "
        f"सब ठीक है, या कुछ बदलना है?"
    )


def _safe_date(year: int, month: int, day: int, today: datetime.date) -> str | None:
    try:
        found = datetime.date(year, month, day)
    except ValueError:
        return None
    # A named date that has already passed is not next year. The caller is asked again.
    if found < today:
        return "past"
    return found.isoformat()


def _period(text: str) -> str:
    match = _PERIOD.search(text or "")
    if not match:
        return ""
    word = match.group(1).lower()
    if word in {"सुबह", "morning"} or word.startswith("a"):
        return "am"
    return "pm"


def _finish_time(hour: int, minute: int, period: str, word_only: bool) -> tuple[str, str] | None:
    if hour == 0 or hour > 12:
        if 0 <= hour <= 23:
            return ("time", f"{hour:02d}:{minute:02d}")
        return None
    if not period:
        return ("ambiguous", f"{hour}:{minute:02d}")
    if period == "am":
        clock = 0 if hour == 12 else hour
    else:
        clock = hour if hour == 12 else hour + 12
    if word_only and not period:
        return ("ambiguous", f"{hour}:{minute:02d}")
    return ("time", f"{clock:02d}:{minute:02d}")


def _speak_clock(hour: int, minute: int) -> str:
    if hour == 0:
        period, clock = "रात", 12
    elif hour < 12:
        period, clock = "सुबह", hour
    elif hour == 12:
        period, clock = "दोपहर", 12
    elif hour < 16:
        period, clock = "दोपहर", hour - 12
    else:
        period, clock = "शाम", hour - 12
    if minute:
        return f"{period} {number_to_hindi(clock)} बजकर {number_to_hindi(minute)} मिनट"
    return f"{period} {number_to_hindi(clock)} बजे"
