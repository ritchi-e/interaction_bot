"""Keep spoken replies inside the campaign facts.

This module has no model calls. The proxy and the tests both use it, so a
sentence that names a price, a competitor, or a forbidden topic is rejected
before any audio is generated.
"""

import re
import unicodedata

DIGIT_TABLE = str.maketrans("०१२३४५६७८९", "0123456789")
SENTENCE_MARK = re.compile(r"[.!?।]")
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

HANDOFF_TOOL = {
    "type": "function",
    "function": {
        "name": "request_handoff",
        "description": "Call this when the caller's question is not answered by the FACTS.",
        "parameters": {
            "type": "object",
            "properties": {"reason": {"type": "string"}},
            "required": ["reason"],
        },
    },
}

SAFE_FALLBACK = "I don't have the details of this call. A teammate will follow up with you."
ID_RE = re.compile(
    r"(CAMPAIGN_ID|CALL_REQUEST_ID):\s*"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)
MAX_TOKENS = 120


def message_text(message):
    content = message.get("content") or ""
    if isinstance(content, list):
        return " ".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return str(content)


def extract_ids(messages):
    campaign_id = ""
    call_request_id = ""
    for message in messages or []:
        for kind, value in ID_RE.findall(message_text(message)):
            if kind == "CAMPAIGN_ID":
                campaign_id = value
            else:
                call_request_id = value
    return campaign_id, call_request_id


def prepare_messages(messages, prompt):
    """Drop every incoming system message. The compiled prompt is the only one."""
    rest = [message for message in messages or [] if message.get("role") != "system"]
    return [{"role": "system", "content": prompt}, *rest]


def force_sampling(body):
    requested = body.get("max_tokens") or MAX_TOKENS
    try:
        requested = int(requested)
    except (TypeError, ValueError):
        requested = MAX_TOKENS
    tools = list(body.get("tools") or [])
    if not any((tool.get("function") or {}).get("name") == "request_handoff" for tool in tools):
        tools.append(HANDOFF_TOOL)
    updated = dict(body)
    updated["temperature"] = 0.2
    updated["max_tokens"] = min(requested, MAX_TOKENS)
    updated["tools"] = tools
    return updated


def numbers_in(text):
    cleaned = str(text or "").translate(DIGIT_TABLE)
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", cleaned)
    found = set()
    for match in NUMBER_RE.finditer(cleaned):
        raw = match.group()
        found.add(raw)
        if "." in raw:
            found.add(raw.rstrip("0").rstrip("."))
    return found


def script_ok(text):
    for char in text or "":
        if char.isspace() or char.isdigit() or char in "₹.,!?;:'\"-()/&%+@#*:":
            continue
        code = ord(char)
        if 0x0041 <= code <= 0x024F or 0x0900 <= code <= 0x097F:
            continue
        if unicodedata.category(char).startswith(("P", "S", "N", "Z")):
            continue
        return False
    return True


def contains_term(sentence, term):
    term = (term or "").strip()
    if not term:
        return False
    if term.isascii():
        return re.search(rf"(?i)\b{re.escape(term)}\b", sentence) is not None
    return term.casefold() in sentence.casefold()


def validate_sentence(sentence, facts, forbidden, competitors):
    if not script_ok(sentence):
        return False, "script"
    for competitor in competitors or []:
        if contains_term(sentence, competitor):
            return False, "competitor"
    for topic in forbidden or []:
        if contains_term(sentence, topic):
            return False, "forbidden_topic"
    allowed = numbers_in(facts)
    for number in numbers_in(sentence):
        if number not in allowed:
            return False, "unlisted_number"
    return True, ""


def split_sentences(text):
    parts = re.split(r"(?<=[.!?।])\s+", (text or "").strip())
    return [part.strip() for part in parts if part.strip()]


def take_complete(buffer):
    complete = []
    rest = buffer
    while rest:
        match = SENTENCE_MARK.search(rest)
        if match is None:
            break
        sentence = rest[: match.end()].strip()
        rest = rest[match.end() :].lstrip()
        if sentence:
            complete.append(sentence)
    return complete, rest


def guard_text(text, facts, forbidden, competitors, handoff):
    kept = []
    violations = []
    for sentence in split_sentences(text):
        ok, reason = validate_sentence(sentence, facts, forbidden, competitors)
        if ok:
            kept.append(sentence)
            continue
        violations.append({"sentence": sentence, "reason": reason})
        kept.append(handoff)
        break
    return " ".join(kept).strip(), violations
