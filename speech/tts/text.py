"""Text normalisation and clause splitting for low time-to-first-audio."""

from __future__ import annotations

import re

_CURRENCY = re.compile(r"(?:₹|Rs\.?|INR)\s?([\d,]+(?:\.\d+)?)")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s?%")
_NUMBER = re.compile(r"\b(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?\b")
_CLAUSE_SPLIT = re.compile(r"(?<=[.!?।,;:])\s+|\n+")


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


# Compact Hindi cardinals for common sale amounts; fall back to digit reading.
_HI_ONES = [
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
]


def number_to_hindi(n: int) -> str:
    if n < 0:
        return "माइनस " + number_to_hindi(-n)
    if n <= 10:
        return _HI_ONES[n]
    if n < 100:
        return " ".join(_HI_ONES[int(d)] for d in str(n) if d.isdigit())
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


def normalize(text: str, language: str = "hi") -> str:
    text = " ".join((text or "").split())
    if not text:
        return ""
    lang = (language or "hi").lower()
    to_words = number_to_english if lang.startswith("en") else number_to_hindi

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
            spoken = f"{to_words(int(whole))} point {' '.join(to_words(int(d)) for d in frac if d.isdigit())}"
        else:
            spoken = to_words(int(raw))
        return f"{spoken} percent" if lang.startswith("en") else f"{spoken} प्रतिशत"

    text = _PERCENT.sub(percent, text)

    def number(m: re.Match) -> str:
        whole = int(m.group(1).replace(",", ""))
        frac = m.group(2)
        spoken = to_words(whole)
        if frac:
            spoken += " point " + " ".join(to_words(int(d)) for d in frac)
        return spoken

    text = _NUMBER.sub(number, text)
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
