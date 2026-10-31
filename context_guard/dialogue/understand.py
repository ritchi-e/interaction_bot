"""Read one booking turn with the language model.

The model only reads what the caller said and fills typed fields. It does not
write the reply. The booking code checks every field (past dates, a real
clock, a first and a last name) before anything is saved, and picks the next
line from the campaign graph.

If the model is slow or down, the word rules in slots.py read the turn instead.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field

import httpx

from dialogue.slots import apply_period, extract_date, extract_name, extract_time, is_question, name_is_clear

log = logging.getLogger("context_guard")

UPSTREAM = os.environ.get("UPSTREAM_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
UPSTREAM_KEY = os.environ.get("UPSTREAM_LLM_API_KEY", "")
# gpt-4o-mini got weekdays wrong ("next Monday") and was slower; nano misread years.
MODEL = os.environ.get("BOOKING_LLM_MODEL") or "gpt-4.1-mini"
TIMEOUT = float(os.environ.get("BOOKING_LLM_TIMEOUT", "3.5"))

INTENTS = ("answer", "yes", "no", "done", "change", "question", "unclear")
FIELDS = ("name", "date", "time")

# Short replies need no model call.
_ACK = re.compile(
    r"^(?:theek hai|thik hai|theek|thik|ok|okay|haan|ha|ji|yes|yeah|"
    r"हाँ|हां|जी|जी हाँ|जी हां|ठीक है|ठीक|बिल्कुल|सही|सही है)[\s.!?।]*$",
    re.IGNORECASE,
)
_NO = re.compile(r"^(?:no|nope|nahi|nahin|na|नहीं|नही|ना)[\s.!?।]*$", re.IGNORECASE)
_CLOCK = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")

_client: httpx.AsyncClient | None = None


@dataclass
class Heard:
    intent: str = "unclear"
    first_name: str = ""
    last_name: str = ""
    name_sure: bool = True
    date: str = ""
    date_issue: str = ""
    year: int | None = None
    time: str = ""
    clock: str = ""
    change: list[str] = field(default_factory=list)
    source: str = "rules"

    @property
    def name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part).strip()

    def has_detail(self) -> bool:
        return bool(self.first_name or self.last_name or self.date or self.date_issue or self.time or self.clock)


_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "intent", "first_name", "last_name", "name_sure", "date", "date_issue",
        "year", "time", "period_said", "clock_without_period", "change",
    ],
    "properties": {
        "intent": {"type": "string", "enum": list(INTENTS)},
        "first_name": {"type": "string"},
        "last_name": {"type": "string"},
        "name_sure": {"type": "boolean"},
        "date": {"type": "string"},
        "date_issue": {"type": "string", "enum": ["", "year_only", "unclear"]},
        "year": {"type": ["integer", "null"]},
        "time": {"type": "string"},
        "period_said": {"type": "boolean"},
        "clock_without_period": {"type": "string"},
        "change": {"type": "array", "items": {"type": "string", "enum": list(FIELDS)}},
    },
}

_RULES = """You read one turn of a phone call. The caller is booking an appointment. They speak Hindi, English, or Hinglish. The text is a speech-to-text transcript and can contain filler, echoes of the agent's question, or misheard words.

Return only what the caller actually said in THIS turn. Leave a field empty when they did not say it in this turn. "booking_so_far" is context only: do NOT copy the name, date, or time from it into your answer. If the caller only gives a time, first_name, last_name, and date stay "".

intent:
- answer: they gave a detail (name, date, or time), or answered the question asked.
- yes: agreement or "all fine" with nothing to change ("हाँ", "ठीक है", "नहीं, सब ठीक है", "bilkul").
- no: refusal or "no" to the question asked.
- done: they are finished and saying goodbye or thanks ("धन्यवाद", "thank you", "bye") with nothing to change. "नहीं सब ठीक है, धन्यवाद" is done.
- change: they want to change a detail already booked or already given.
- question: they ask something and give no detail.
- unclear: none of the above.

Name:
- Only a person's own name. Drop filler and words echoed from the question: पूरा, नाम, मेरा, है, जी, hey, um, so, first name, last name, आपका, इतना.
- first_name is the first given name. last_name is everything after it (middle and surname): "आशुतोष रवि गुप्ता" -> first "आशुतोष", last "रवि गुप्ता".
- Keep the script and spelling as transcribed. Do not translate or transliterate.
- If the booking already has a first name and the caller now says only a surname, return the known first name as first_name and the surname as last_name.
- name_sure is false when the words might not be a name at all (garbled transcript, a common word, part of a sentence). Otherwise true.

Date (field "date", format YYYY-MM-DD):
- Today is {today} ({weekday}). Time zone Asia/Kolkata.
- Calendar for weekday words (use it, do not compute weekdays yourself):
{calendar}
- A day and month with no year: use the current year, even if that day already passed this year. The system tells the caller when a date has passed.
- A day with no month: the next such day on or after today (this month, else next month).
- Relative words: आज today, कल tomorrow, परसों day after tomorrow, अगले सोमवार next Monday, etc.
- Spoken Hindi numbers: चौबीस 24, बाइस/बाईस 22, सत्ताईस 27, etc.
- "दो हज़ार चौबीस", "2 hazar chaubis", "two thousand twenty four" are the YEAR 2024, not a day. Put it in "year".
- If they gave only a year, or a month without a day: date "", date_issue "year_only" (with year) or "unclear".
- If they said a full date with a year, use that year exactly, even if it is in the past.

Time (24-hour HH:MM):
- सुबह = morning, दोपहर = afternoon (12-15), शाम = evening (16-19), रात = night.
- साढ़े X = X:30, सवा X = X:15, पौने X = (X-1):45, डेढ़/ded/dedh = 1:30, ढाई/dhai = 2:30.
- "एक बज के 30 मिनट" = 1:30. "चार पंद्रह" = 4:15. "दस बजकर तीस" = 10:30.
- "ded baje dopahar" / "दोपहर डेढ़ बजे" = 13:30. "शाम साढ़े चार" = 16:30. "सुबह सवा नौ" = 09:15.
- STT often writes साढ़े as "start" or "started" right before an hour: "सुबह start है दस बजे" = 10:30.
- period_said is true only if THIS turn says सुबह/दोपहर/शाम/रात/morning/evening/am/pm, uses a 24-hour clock (e.g. 16:00), or the booking holds an hour waiting for morning or evening and this turn supplies it. Otherwise false.
- If period_said is true, fill "time" (24-hour) and leave clock_without_period "".
- If period_said is false, leave "time" "" and put the 12-hour clock in clock_without_period as H:MM (e.g. "4:15"). Do not assume morning or evening.
- A pending clock in the booking plus "सुबह का" / "शाम को" in this turn makes a full time.

change: the fields the caller wants to change in this turn (name, date, time). Empty when nothing is to be changed.
"""


def _system_prompt(today: datetime.date) -> str:
    days = [today + datetime.timedelta(days=offset) for offset in range(15)]
    calendar = "\n".join(f"  {day.isoformat()} {day.strftime('%A')}" for day in days)
    return (
        _RULES.replace("{today}", today.isoformat())
        .replace("{weekday}", today.strftime("%A"))
        .replace("{calendar}", calendar)
    )


def _user_prompt(step: str, last_bot: str, slots: dict, text: str) -> str:
    known = {
        "name": slots.get("name") or "",
        "first_name_heard": slots.get("given_name") or "",
        "name_waiting_for_yes": slots.get("pending_name") or "",
        "date": slots.get("date") or "",
        "time": slots.get("time") or "",
        "hour_waiting_for_morning_or_evening": slots.get("pending_clock") or "",
    }
    return json.dumps(
        {
            "step": step or "offer",
            "agent_just_said": re.sub(r"<[^>]+>", "", last_bot or "").strip(),
            "booking_so_far": known,
            "caller_said": text,
        },
        ensure_ascii=False,
    )


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=TIMEOUT)
    return _client


async def understand(text: str, step: str, slots: dict, last_bot: str, today: datetime.date, rule_intent: str) -> Heard:
    raw = " ".join((text or "").split())
    if not raw:
        return Heard(intent="unclear")
    if rule_intent == "done":
        return Heard(intent="done", source="rules")
    if _ACK.match(raw) and not slots.get("pending_clock"):
        return Heard(intent="yes", source="rules")
    if _NO.match(raw):
        return Heard(intent="no", source="rules")
    if not UPSTREAM_KEY:
        return from_rules(raw, step, slots, today, rule_intent)
    started = time.perf_counter()
    try:
        response = await _http().post(
            f"{UPSTREAM}/chat/completions",
            headers={"Authorization": f"Bearer {UPSTREAM_KEY}"},
            json={
                "model": MODEL,
                "temperature": 0,
                "max_tokens": 200,
                "messages": [
                    {"role": "system", "content": _system_prompt(today)},
                    {"role": "user", "content": _user_prompt(step, last_bot, slots, raw)},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "booking_turn", "strict": True, "schema": _SCHEMA},
                },
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        heard = _without_echo(_from_model(json.loads(content)), slots)
        _period_check(heard, raw, slots)
    except Exception as exc:  # noqa: BLE001 - any failure falls back to the word rules
        log.warning("booking understand failed, using rules: %s", exc)
        return from_rules(raw, step, slots, today, rule_intent)
    # "हाँ, क्या details चाहिए?" right after the offer is a yes, not a FAQ.
    if heard.intent == "question" and rule_intent == "yes" and not heard.has_detail():
        heard.intent = "yes"
    log.info(
        "booking understand ms=%.0f step=%s intent=%s name=%r sure=%s date=%s issue=%s year=%s time=%s clock=%s change=%s",
        (time.perf_counter() - started) * 1000,
        step,
        heard.intent,
        heard.name,
        heard.name_sure,
        heard.date,
        heard.date_issue,
        heard.year,
        heard.time,
        heard.clock,
        heard.change,
    )
    return heard


def _from_model(data: dict) -> Heard:
    intent = data.get("intent") if data.get("intent") in INTENTS else "unclear"
    date = str(data.get("date") or "").strip()
    try:
        datetime.date.fromisoformat(date) if date else None
    except ValueError:
        date = ""
    clock_24 = str(data.get("time") or "").strip()
    match = _CLOCK.match(clock_24)
    clock_24 = f"{int(match.group(1)):02d}:{match.group(2)}" if match else ""
    pending = str(data.get("clock_without_period") or "").strip()
    match = _CLOCK.match(pending)
    pending = f"{int(match.group(1))}:{match.group(2)}" if match and 1 <= int(match.group(1)) <= 12 else ""
    if clock_24 and not data.get("period_said"):
        hour, minute = (int(part) for part in clock_24.split(":"))
        if 1 <= hour % 12 <= 11 and not pending:
            pending = f"{hour % 12}:{minute:02d}"
        clock_24 = ""
    year = data.get("year")
    return Heard(
        intent=intent,
        first_name=_clean_name(data.get("first_name")),
        last_name=_clean_name(data.get("last_name")),
        name_sure=bool(data.get("name_sure", True)),
        date=date,
        date_issue=str(data.get("date_issue") or ""),
        year=int(year) if isinstance(year, int) else None,
        time=clock_24,
        clock="" if clock_24 else pending,
        change=[item for item in (data.get("change") or []) if item in FIELDS],
        source="llm",
    )


_PERIOD_WORD = re.compile(
    r"सुबह|दोपहर|शाम|रात|morning|afternoon|evening|night|noon|\b[ap]\.?m\b|"
    r"subah|subha|dopahar|dophar|shaam|sham|raat",
    re.IGNORECASE,
)


def _period_check(heard: Heard, text: str, slots: dict) -> None:
    """Morning or evening must be said, not assumed. A 24-hour clock or 12 is fine."""
    if not heard.time or slots.get("pending_clock") or _PERIOD_WORD.search(text):
        return
    hour, minute = (int(part) for part in heard.time.split(":"))
    if hour == 12 or re.search(rf"\b{hour}:{minute:02d}\b", text):
        return
    heard.time = ""
    heard.clock = f"{hour % 12 or 12}:{minute:02d}"


def _without_echo(heard: Heard, slots: dict) -> Heard:
    """Drop fields the model copied from the booking instead of hearing them now."""
    if heard.name and heard.name == (slots.get("name") or ""):
        heard.first_name = heard.last_name = ""
        heard.change = [item for item in heard.change if item != "name"]
    if heard.date and heard.date == (slots.get("date") or ""):
        heard.date = ""
        heard.year = None
        heard.change = [item for item in heard.change if item != "date"]
    if heard.time and heard.time == (slots.get("time") or ""):
        heard.time = ""
        heard.change = [item for item in heard.change if item != "time"]
    if heard.intent in {"answer", "change"} and not heard.has_detail() and not heard.change:
        heard.intent = "yes" if slots.get("time") else "unclear"
    return heard


def _clean_name(value) -> str:
    text = " ".join(str(value or "").replace("।", " ").split()).strip(" .,!?")
    if any(character.isdigit() for character in text):
        return ""
    return text


_WHICH = {
    "name": re.compile(r"\b(?:name|naam)\b|नाम", re.IGNORECASE),
    "date": re.compile(r"\b(?:date|tarikh)\b|तारीख", re.IGNORECASE),
    "time": re.compile(r"\b(?:time|samay)\b|समय|बजे", re.IGNORECASE),
}
_CHANGE = re.compile(r"change|badal|badlo|बदल|गलत|wrong|दूसर", re.IGNORECASE)


def from_rules(text: str, step: str, slots: dict, today: datetime.date, rule_intent: str) -> Heard:
    """The old word rules, used only when the model cannot be reached."""
    heard = Heard(source="rules")
    change = _CHANGE.search(text) is not None
    if step == "name" or (step in {"", "offer"} and rule_intent != "yes"):
        name = extract_name(text)
        if name:
            words = name.split()
            given = slots.get("given_name") or ""
            if given and len(words) == 1 and words[0] != given:
                heard.first_name, heard.last_name = given, words[0]
            else:
                heard.first_name, heard.last_name = words[0], " ".join(words[1:])
            heard.name_sure = name_is_clear(name) or bool(given)
    found = extract_date(text, today)
    if found == "past":
        heard.date_issue = "past"
    elif found:
        heard.date = found
    parsed = extract_time(text)
    if parsed and parsed[0] == "time":
        heard.time = parsed[1]
    elif parsed and parsed[0] == "ambiguous":
        heard.clock = parsed[1]
    elif slots.get("pending_clock"):
        clock = apply_period(str(slots["pending_clock"]), text)
        if clock:
            heard.time = clock
    if change:
        heard.change = [name for name, pattern in _WHICH.items() if pattern.search(text)]
    if rule_intent == "done":
        heard.intent = "done"
    elif change:
        heard.intent = "change"
    elif heard.has_detail():
        heard.intent = "answer"
    elif rule_intent in {"yes", "no"}:
        heard.intent = rule_intent
    elif is_question(text):
        heard.intent = "question"
    return heard
