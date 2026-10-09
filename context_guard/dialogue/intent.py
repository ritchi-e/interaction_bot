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


def classify(text: str, graph: DialogueGraph) -> str:
    raw = " ".join((text or "").split())
    folded = raw.casefold()
    if any(marker.casefold() in folded for marker in graph.off_topic_markers):
        return "off_topic"
    if _DECLINE.search(raw):
        return "decline"
    # A bare no is a refusal, not a goodbye. The graph gets one sales try.
    if _NO.match(raw):
        return "no"
    if caller_is_done([{"role": "user", "content": raw}]):
        return "done"
    if _YES_LEAD.match(raw) and not _INFO.search(raw):
        return "yes"
    if _QUESTION.search(raw) or _INFO.search(raw):
        return "question"
    return "unclear"
