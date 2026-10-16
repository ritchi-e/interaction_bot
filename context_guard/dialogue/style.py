"""One Svara style tag at the end of a spoken line.

The self-hosted model reads these at the end of a sentence:
neutral, formal, chat, clear, happy, surprise, sad, fear, anger, disgust.
Fear, anger, and disgust make the agent sound hostile, so a caller who is
upset is answered with sad or neutral instead.
"""

from __future__ import annotations

import re

STYLE_TAGS = (
    "neutral",
    "formal",
    "chat",
    "clear",
    "happy",
    "surprise",
    "sad",
    "fear",
    "anger",
    "disgust",
)
_TAG_RE = re.compile(r"<(neutral|formal|chat|clear|happy|surprise|sad|fear|anger|disgust)>", re.IGNORECASE)
_UPSET = re.compile(r"गुस्स|घिन|चिल्ला|angry|furious|disgust|worst|बेकार", re.IGNORECASE)
_WORRIED = re.compile(r"डर|घबरा|चिंता|scared|afraid|worried", re.IGNORECASE)
_SURPRISED = re.compile(r"सच में|यकीन नहीं|अरे वाह|really\?|seriously|can't believe", re.IGNORECASE)
_AMOUNT = re.compile(r"\d|हज़ार|हजार|लाख|करोड़|प्रतिशत|रुपये|percent", re.IGNORECASE)
_CLOSING = re.compile(r"अलविदा|धन्यवाद|goodbye|thank you", re.IGNORECASE)
# The agent's own apology. A calm step must not flatten this to neutral.
_APOLOGY = re.compile(r"खेद|माफ़|माफ|क्षमा|sorry|forgive", re.IGNORECASE)


def choose_tag(user_text: str = "", mode: str = "", tone: str = "", sentence: str = "") -> str:
    """Pick the tag that matches this moment. One tag, not a stack."""
    heard = user_text or ""
    spoken = sentence or ""
    if _UPSET.search(heard):
        return "sad"
    if _APOLOGY.search(spoken):
        return "sad"
    if _WORRIED.search(heard):
        return "neutral"
    if _SURPRISED.search(heard):
        return "surprise"
    if _AMOUNT.search(spoken):
        return "clear"
    if mode == "redirect":
        return "formal"
    if mode in {"reask"} or tone == "calm":
        return "neutral"
    if mode == "close" or _CLOSING.search(spoken):
        return "formal"
    if tone == "cheerful" and mode == "ask":
        return "happy"
    if mode == "answer":
        return "chat"
    return "chat"


def strip_style(text: str) -> str:
    """Remove style tags. This voice speaks them as words instead of emotion."""
    return _TAG_RE.sub("", text or "").strip()


def apply_style(text: str, tag: str) -> str:
    """Put one tag at the end of each sentence, before the full stop.

    A tag after the full stop is split off and spoken as noise before the
    next sentence. A tag in the middle of a sentence is spoken as a word.
    """
    raw = (text or "").strip()
    if not raw:
        return raw
    cleaned = _TAG_RE.sub("", raw).strip()
    chosen = tag or "chat"
    if chosen in {"fear", "anger", "disgust"}:
        chosen = "sad" if chosen != "disgust" else "neutral"
    if chosen not in STYLE_TAGS:
        chosen = "chat"
    parts = [part.strip() for part in re.split(r"(?<=[.!?।])\s+", cleaned) if part.strip()]
    if not parts:
        return ""
    tagged = []
    for part in parts:
        mark = re.search(r"([.!?।]+)$", part)
        if mark:
            body = part[: mark.start()].rstrip()
            tagged.append(f"{body} <{chosen}>{mark.group(1)}")
        else:
            tagged.append(f"{part} <{chosen}>")
    return " ".join(tagged)
