"""Classify one caller turn against the current campaign graph."""

from __future__ import annotations

import re

from dialogue.graph import DialogueGraph
from guard import caller_is_done

# Devanagari vowel signs are not word characters, so \b does not see the end of हाँ.
_YES_LEAD = re.compile(
    r"^(?:yes|yeah|yep|sure|ok|okay|haan|ha|ji)\b"
    r"|^(?:हाँ|हां|जी हाँ|जी हां|ठीक है|बिल्कुल|ठीक|जी)(?=\s|$|[,.!?।])",
    re.IGNORECASE,
)
_NO = re.compile(
    r"^("
    r"no|nope|nah|nahi|nahin|na|not interested|"
    r"नहीं|ना|नही|नहीं चाहिए|मुझे नहीं चाहिए|रुचि नहीं"
    r")[\s.!?।]*$",
    re.IGNORECASE,
)
# Refusing the detail just offered. This is not a no to the whole call.
_DECLINE = re.compile(
    r"(नहीं जानना|नही जानना|जानना नहीं|मत बता|मत बताओ|"
    r"don't want to know|do not want to know|not want to know)",
    re.IGNORECASE,
)
# "Go on" is a yes. It is not a new question and must not repeat the last offer.
_CONTINUE = re.compile(
    r"^(?:बताइए|बताओ|बताइये|बोलिए|बोलो|सुनाइए|सुनाओ|आगे बढ़िए|आगे|"
    r"और|और बताइए|अच्छा और|हाँ बताइए|हां बताइए|जी बताइए)"
    r"[\s.!?।]*$",
    re.IGNORECASE,
)
# They already heard this part. Move to the next step instead of saying it again.
_ALREADY = re.compile(
    r"बता चुके|बता चुकी|फिर से क्यों|दोबारा|फिर से बता|already told",
    re.IGNORECASE,
)
# A real information question. "बताइए" after a yes only means "go on".
_INFO = re.compile(
    r"(कितन|कैसे|क्यों|what|how|why|when|rate|emi|interest|ब्याज|"
    r"राशि|योग्यता|eligibility|प्रक्रिया|process)",
    re.IGNORECASE,
)
_QUESTION = re.compile(
    r"(\?|क्या|कितन|कैसे|क्यों|what|how|why|when|rate|emi|interest|ब्याज)",
    re.IGNORECASE,
)


def marker_hit(text: str, marker: str) -> bool:
    """Match a product word without catching a longer word that contains it.

    "car" matches "Car का लेनी थी" and not "card". "कार" matches "कार के लिए"
    and not "कार्ड".
    """
    raw = (marker or "").strip()
    if not raw:
        return False
    folded = (text or "").casefold()
    needle = raw.casefold()
    if re.fullmatch(r"[a-z]+", needle) and len(needle) <= 8:
        return re.search(rf"(?<![a-z]){re.escape(needle)}(?![a-z])", folded) is not None
    if re.search(r"[\u0900-\u097F]", raw) and " " not in raw and len(raw) <= 6:
        return re.search(
            rf"(?<![\u0900-\u097F]){re.escape(needle)}(?![\u0900-\u097F])",
            folded,
        ) is not None
    return needle in folded


_GOODBYE_WORD = re.compile(
    r"thank|धन्यवाद|शुक्रिया|bye|बाय|अलविदा|कॉल काट|फोन काट|goodbye",
    re.IGNORECASE,
)
# A refusal of the offer, not a question. The first one is one sales try.
_NOT_INTERESTED = re.compile(
    r"दिलचस्पी नहीं|बिल्कुल नहीं|not interested",
    re.IGNORECASE,
)


def classify(text: str, graph: DialogueGraph) -> str:
    raw = " ".join((text or "").split())
    # A bare no is one sales try. It is also a bare-no goodbye for calls
    # that have no graph, so it has to be decided here before that rule.
    if _NO.match(raw) or (_NOT_INTERESTED.search(raw) and not _QUESTION.search(raw)):
        return "no"
    # "नहीं जानना, thank you" is a goodbye. "मत बताओ" alone is not.
    finished = caller_is_done([{"role": "user", "content": raw}])
    detail_only = bool(_DECLINE.search(raw)) and not _GOODBYE_WORD.search(raw)
    if finished and not detail_only:
        return "done"
    if any(marker_hit(raw, marker) for marker in graph.off_topic_markers):
        return "off_topic"
    if _DECLINE.search(raw):
        return "decline"
    if _ALREADY.search(raw):
        return "yes"
    if (_YES_LEAD.match(raw) or _CONTINUE.match(raw)) and not _INFO.search(raw):
        return "yes"
    if _QUESTION.search(raw) or _INFO.search(raw):
        return "question"
    return "unclear"
