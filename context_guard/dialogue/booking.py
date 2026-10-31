"""Move an appointment call from the greeting to a saved booking.

The language model reads each turn into typed fields (dialogue/understand.py).
This file decides what those fields mean for the call: it rejects past dates,
waits for a first and a last name, asks for morning or evening, and books only
when name, date, and time are all present. The booked sentence is built from
the row that was saved, not from the words the model remembers.
"""

from __future__ import annotations

import datetime

from dialogue.graph import DialogueGraph
from dialogue.understand import Heard

PERIOD_ASK = "Exact time बता दीजिए, कितने बजे का चाहिए, सुबह या शाम के साथ।"
CHECKING = "रिकॉर्ड्स में check कर रही हूँ कि यह date available है या नहीं।"
# The voice turns this into silence. It is not a word to be spoken.
PAUSE = "<pause>"
TAKEN = "यह समय उपलब्ध नहीं है। कोई और समय बता दीजिए।"
SAVE_FAILED = "अभी save नहीं हुआ। समय एक बार फिर बता दीजिए।"
CHANGE_ASK = "क्या बदलना है, नाम, तारीख, या समय?"
PAST_DATE = "यह तारीख निकल चुकी है। आगे की कोई तारीख बता दीजिए।"
PAST_YEAR = "हम अभी {year} में हैं। आगे की कोई तारीख बता दीजिए, दिन और महीना।"
DATE_INCOMPLETE = "पूरी तारीख बता दीजिए, दिन और महीना।"
PAST_TIME = "आज का यह समय निकल चुका है। कोई आगे का समय बता दीजिए।"


def decide(
    graph: DialogueGraph,
    step: str,
    opened: bool,
    text: str,
    slots: dict,
    heard: Heard,
    today: datetime.date,
) -> dict:
    slots = dict(slots or {})
    text = (text or "").strip()
    if heard.intent == "done":
        return _end(slots)
    if not text:
        if opened and step in graph.steps and step not in {"offer", "close"}:
            return _speak(graph, step, slots, reask=True)
        return _speak(graph, "offer", slots, reask=False)
    if not opened or step in {"", "offer"}:
        if heard.intent == "no":
            return _speak(graph, "persuade", slots, reask=False)
        if heard.intent == "question" and not heard.has_detail():
            return {"action": "answer", "step": "offer", "slots": slots}
        return _take(graph, step or "offer", slots, heard, today) or _next(graph, slots)
    if step == "persuade":
        if heard.intent == "no":
            return _end(slots)
        return _take(graph, step, slots, heard, today) or _next(graph, slots)
    if step == "confirm":
        return _confirm(graph, slots, heard, today)
    if step == "name" and slots.get("pending_name") and not heard.name:
        if heard.intent == "yes":
            slots["name"] = slots.pop("pending_name")
            slots.pop("given_name", None)
            return _next(graph, slots)
        if heard.intent in {"no", "change"}:
            slots.pop("pending_name", None)
            return _speak(graph, "name", slots, reask=True)
    before = (slots.get("name"), slots.get("date"), slots.get("time"), slots.get("pending_clock"))
    held = _take(graph, step, slots, heard, today)
    if held:
        return held
    if (slots.get("name"), slots.get("date"), slots.get("time"), slots.get("pending_clock")) != before:
        return _next(graph, slots)
    if step == "name" and slots.get("given_name"):
        return _last_name_ask(slots)
    if step == "name" and slots.get("pending_name"):
        return {"action": "speak", "step": "name", "slots": slots, "text": f"मैंने {slots['pending_name']} सुना। सही है?"}
    if step == "time" and slots.get("pending_clock"):
        return {"action": "speak", "step": "time", "slots": slots, "text": PERIOD_ASK}
    return _speak(graph, step if step in graph.steps else "offer", slots, reask=True)


def _confirm(graph, slots, heard, today):
    if heard.intent == "yes":
        return _end(slots)
    wants = list(heard.change)
    if heard.intent == "change" or wants or heard.has_detail():
        return _revise(graph, slots, heard, wants, today)
    if heard.intent == "no":
        return {"action": "speak", "step": "confirm", "slots": slots, "text": CHANGE_ASK}
    if heard.intent == "question":
        return {"action": "repeat", "step": "confirm", "slots": slots}
    return _end(slots)


def _revise(graph, slots, heard, wants, today):
    """They heard the booking and want a detail changed. Keep the saved row until the new one is checked."""
    if heard.name:
        wants.append("name")
    if heard.date or heard.date_issue:
        wants.append("date")
    if heard.time or heard.clock:
        wants.append("time")
    if not wants:
        return {"action": "speak", "step": "confirm", "slots": slots, "text": CHANGE_ASK}
    if "date" in wants and not (heard.date or heard.date_issue):
        slots.pop("date", None)
        slots.pop("time", None)
        slots.pop("pending_clock", None)
    if "time" in wants and not (heard.time or heard.clock):
        slots.pop("time", None)
        slots.pop("pending_clock", None)
    if "name" in wants and not heard.name:
        slots.pop("name", None)
        return _speak(graph, "name", slots, reask=False)
    held = _take(graph, "confirm", slots, heard, today)
    if held:
        return held
    return _next(graph, slots)


def _take(graph, step, slots, heard, today):
    """Copy what was heard into the booking. Return a line only when the caller must be asked again."""
    if heard.name:
        held = _take_name(graph, step, slots, heard)
        if held:
            return held
    if heard.date_issue == "past":
        return {"action": "speak", "step": "date", "slots": slots, "text": PAST_DATE}
    if heard.date_issue == "year_only" and not heard.date:
        if heard.year and heard.year < today.year:
            return {"action": "speak", "step": "date", "slots": slots, "text": PAST_YEAR.format(year=_year_words(today.year))}
        return {"action": "speak", "step": "date", "slots": slots, "text": DATE_INCOMPLETE}
    if heard.date:
        found = datetime.date.fromisoformat(heard.date)
        if found < today:
            return {"action": "speak", "step": "date", "slots": slots, "text": PAST_DATE}
        if slots.get("date") != heard.date:
            slots["date"] = heard.date
    elif heard.date_issue == "unclear" and step == "date":
        return {"action": "speak", "step": "date", "slots": slots, "text": DATE_INCOMPLETE}
    if heard.time:
        slots["time"] = heard.time
        slots.pop("pending_clock", None)
    elif heard.clock:
        slots.pop("time", None)
        slots["pending_clock"] = heard.clock
    return None


def _take_name(graph, step, slots, heard):
    first = heard.first_name.strip()
    last = heard.last_name.strip()
    given = slots.get("given_name") or ""
    if not first and last and given:
        first = given
    if first and not last:
        if given and first != given:
            first, last = given, first
        else:
            slots.pop("name", None)
            slots.pop("pending_name", None)
            slots["given_name"] = first
            return _last_name_ask(slots)
    full = f"{first} {last}".strip()
    slots.pop("given_name", None)
    if not heard.name_sure:
        slots.pop("name", None)
        slots["pending_name"] = full
        return {"action": "speak", "step": "name", "slots": slots, "text": f"{full}, सही?"}
    slots.pop("pending_name", None)
    slots["name"] = full
    return None


def _last_name_ask(slots):
    return {
        "action": "speak",
        "step": "name",
        "slots": slots,
        "text": f"मैंने {slots['given_name']} सुना। Last name भी बता दीजिए।",
    }


def _year_words(year: int) -> str:
    from spoken_numbers import number_to_hindi

    return number_to_hindi(year)


def _next(graph: DialogueGraph, slots: dict) -> dict:
    if not slots.get("name"):
        if slots.get("given_name"):
            return _last_name_ask(slots)
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
