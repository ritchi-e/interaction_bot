"""Speak amounts as words so Voxtral does not read 5000 as five zero zero zero.

Loanwords stay in Latin. This is only the number expansion from speech/tts/text.py.
"""

from __future__ import annotations

import re

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

_CURRENCY = re.compile(r"(?:₹|Rs\.?|INR)\s?([\d,]+(?:\.\d+)?)")
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s?%")
_NUMBER = re.compile(r"\b(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?\b")


SAMPLE_RATE = 24000
SENTENCE_GAP = b"\x00" * int(SAMPLE_RATE * 0.4) * 2
_SENTENCE_END = re.compile(r"(?<=[.!?।])\s+")


def split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in _SENTENCE_END.split(text or "") if part.strip()]
    return parts or ([text] if text else [])


def expand_numbers(text: str, language: str) -> str:
    """Expand digits for Hindi or English. Leave every other word unchanged."""
    text = " ".join((text or "").split())
    if not text:
        return ""
    text = text.translate(_DEVANAGARI_DIGITS)
    hindi = not (language or "").lower().startswith("en")
    to_words = number_to_hindi if hindi else number_to_english
    point = "दशमलव" if hindi else "point"
    rupees = "रुपये" if hindi else "rupees"
    percent = "प्रतिशत" if hindi else "percent"

    def currency(match: re.Match) -> str:
        raw = match.group(1).replace(",", "")
        whole = int(float(raw))
        return f"{to_words(whole)} {rupees}"

    text = _CURRENCY.sub(currency, text)

    def percent_words(match: re.Match) -> str:
        raw = match.group(1)
        if "." in raw:
            whole, frac = raw.split(".", 1)
            spoken = f"{to_words(int(whole))} {point} " + " ".join(
                to_words(int(digit)) for digit in frac if digit.isdigit()
            )
        else:
            spoken = to_words(int(raw))
        return f"{spoken} {percent}"

    text = _PERCENT.sub(percent_words, text)

    def number(match: re.Match) -> str:
        whole = int(match.group(1).replace(",", ""))
        frac = match.group(2)
        spoken = to_words(whole)
        if frac:
            spoken += f" {point} " + " ".join(to_words(int(digit)) for digit in frac)
        return spoken

    return _NUMBER.sub(number, text)
