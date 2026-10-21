"""Move an appointment call from the greeting to a saved booking.

Each step asks for one detail. The call moves on only when that detail was
heard. The booked sentence is built from the row that was saved, not from
the words the model remembers.
"""

from __future__ import annotations

import datetime
import re

from dialogue.graph import DialogueGraph
from dialogue.slots import apply_period, extract_date, extract_name, extract_time, is_question

# "ठीक है" accepts the booking. It is not a request to hear it again.
_ACK = re.compile(
    r"^(?:theek hai|thik hai|theek|thik|tik hai|ok|okay|haan|ha|ji|yes|yeah|"
    r"हाँ|हां|जी|ठीक है|ठीक|बिल्कुल|अच्छा|achha|accha)[\s.!?।]*$",
    re.IGNORECASE,
)

PERIOD_ASK = "यह सुबह का समय है या शाम का?"
CHECKING = "Records में check कर रहा हूँ कि यह date available है या नहीं।"
# The voice turns this into silence. It is not a word to be spoken.
PAUSE = "<pause>"
TAKEN = "यह समय उपलब्ध नहीं है। कृपया कोई दूसरा समय बताइए।"
SAVE_FAILED = "अभी booking save नहीं हो पाई। कृपया समय फिर से बताइए।"
CHANGE_ASK = "क्या change करना है, नाम, तारीख, या समय?"
_CHANGE = re.compile(r"change|badal|badlo|बदल|गलत|wrong|दूसर", re.IGNORECASE)
_FINE = re.compile(r"ठीक है|theek hai|thik hai|tik hai|\bfine\b", re.IGNORECASE)
_WHICH_NAME = re.compile(r"\b(?:name|naam)\b|नाम", re.IGNORECASE)
_WHICH_DATE = re.compile(r"\b(?:date|tarikh)\b|तारीख", re.IGNORECASE)
_WHICH_TIME = re.compile(r"\b(?:time|samay)\b|समय|बजे", re.IGNORECASE)


def decide(graph: DialogueGraph, step: str, opened: bool, text: str, slots: dict, intent: str, today: datetime.date) -> dict:
    slots = dict(slots or {})
    text = (text or "").strip()
    if intent == "done":
        return _end(slots)
    if not text:
        if opened and step in graph.steps and step not in {"offer", "close"}:
            return _speak(graph, step, slots, reask=True)
        return _speak(graph, "offer", slots, reask=False)
    if not opened or step in {"", "offer"}:
        return _from_offer(graph, text, slots, intent, today)
    if step == "persuade":
        if intent == "no":
            return _end(slots)
        return _speak(graph, "name", slots, reask=False)
    if step == "confirm":
        if (
            intent == "done"
            or _ACK.match(text)
            or (intent == "yes" and not _CHANGE.search(text))
            or (_FINE.search(text) and not _CHANGE.search(text) and not is_question(text))
        ):
            return _end(slots)
        if intent == "no" or _CHANGE.search(text) or _WHICH_NAME.search(text) or _WHICH_DATE.search(text) or _WHICH_TIME.search(text):
            return _revise(graph, text, slots, today)
        if is_question(text):
            return {"action": "repeat", "step": "confirm", "slots": slots}
        return _end(slots)
    before = (slots.get("name"), slots.get("date"), slots.get("time"))
    if step == "name":
        name = extract_name(text)
        if name:
            slots["name"] = name
    # A date can arrive late, including "चौबीस तारीख" or "twenty fourth October".
    # Keep a date that was already accepted. Do not walk backwards to ask for it again.
    if step in {"date", "time", "confirm"}:
        found = extract_date(text, today)
        if found:
            slots["date"] = found
    if step == "time" or (slots.get("date") and _has_time(text)):
        _take_time(text, slots)
    if (slots.get("name"), slots.get("date"), slots.get("time")) != before or slots.get("pending_clock"):
        return _next(graph, slots)
    if is_question(text):
        return _speak(graph, step if step in graph.steps else "offer", slots, reask=True)
    return _speak(graph, step if step in graph.steps else "offer", slots, reask=True)


def _from_offer(graph, text, slots, intent, today):
    if intent == "no":
        return _speak(graph, "persuade", slots, reask=False)
    if intent != "yes":
        name = extract_name(text)
        found = extract_date(text, today)
        if name and not found:
            slots["name"] = name
            return _speak(graph, "date", slots, reask=False)
    if intent == "yes" or not is_question(text):
        return _speak(graph, "name", slots, reask=False)
    if is_question(text):
        return {"action": "answer", "step": "offer", "slots": slots}
    return _speak(graph, "offer", slots, reask=True)


def _revise(graph, text, slots, today):
    """They heard the booking and want a detail changed. Keep the saved row until the new one is checked."""
    name_hit = _WHICH_NAME.search(text) is not None
    date_hit = _WHICH_DATE.search(text) is not None
    time_hit = _WHICH_TIME.search(text) is not None
    if not name_hit and not date_hit and not time_hit:
        return {"action": "speak", "step": "confirm", "slots": slots, "text": CHANGE_ASK}
    if name_hit:
        found = extract_name(text)
        if found and not _WHICH_NAME.fullmatch(found) and not _CHANGE.search(found):
            slots["name"] = found
        else:
            slots.pop("name", None)
            return _speak(graph, "name", slots, reask=False)
    if date_hit:
        found = extract_date(text, today)
        slots.pop("time", None)
        slots.pop("pending_clock", None)
        if found:
            slots["date"] = found
        else:
            slots.pop("date", None)
            return _speak(graph, "date", slots, reask=False)
    if time_hit and not date_hit:
        slots.pop("time", None)
        slots.pop("pending_clock", None)
        _take_time(text, slots)
        if not slots.get("time") and not slots.get("pending_clock"):
            return _speak(graph, "time", slots, reask=False)
    return _next(graph, slots)


def _has_time(text: str) -> bool:
    return extract_time(text) is not None


def _take_time(text: str, slots: dict) -> None:
    parsed = extract_time(text)
    if parsed and parsed[0] == "time":
        slots.pop("pending_clock", None)
        slots["time"] = parsed[1]
        return
    if parsed and parsed[0] == "ambiguous":
        slots["pending_clock"] = parsed[1]
        slots.pop("time", None)
        return
    if slots.get("pending_clock"):
        clock = apply_period(str(slots.get("pending_clock")), text)
        if clock:
            slots.pop("pending_clock", None)
            slots["time"] = clock


def _next(graph: DialogueGraph, slots: dict) -> dict:
    if not slots.get("name"):
        return _speak(graph, "name", slots, reask=False)
    if not slots.get("date"):
        return _speak(graph, "date", slots, reask=False)
    if slots.get("time"):
        return {"action": "book", "step": "time", "slots": slots}
    if slots.get("pending_clock"):
        return {"action": "speak", "step": "time", "slots": slots, "text": PERIOD_ASK}
    return _speak(graph, "time", slots, reask=False)


def _speak(graph: DialogueGraph, step: str, slots: dict, reask: bool) -> dict:
    item = graph.step(step if step in graph.steps else graph.start)
    text = (item.reask if reask else item.ask) or item.ask or item.reask
    return {"action": "speak", "step": step, "slots": slots, "text": text}


def _end(slots: dict) -> dict:
    return {"action": "hangup", "step": "close", "slots": slots}
