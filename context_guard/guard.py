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
        "description": (
            "Call this only when the caller's question cannot be answered from the facts "
            "without inventing a price, date, product, or policy. Do not call this when the "
            "offer, prices, or FAQs already cover the topic in different words."
        ),
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


# English, Hindi, and the romanised Hindi Deepgram often returns on these calls.
# A bare "thank you" is intentionally absent: people say it mid-conversation.
DONE_RE = re.compile(
    r"("
    r"\b(that will be all|that'?s all|that is all|nothing else|no more questions|"
    r"goodbye|good bye|\bbye\b|that'?s it|that is it|no thanks|no thank you|"
    r"i'?m good|im good|all good|that'?s fine|nothing more)\b"
    r"|और कुछ नहीं|कुछ नहीं|नहीं चाहिए|बस इतना|बस हो गया|रहने दो|"
    r"अलविदा|गुड ?बाय|कॉल काट|फोन रख"
    r"|\b(bas itna|bas ho gaya|aur kuch nahi|kuch nahi|nahi chahiye|"
    r"rehne do|alvida|alvida|ok bye)\b"
    r")",
    re.IGNORECASE,
)

# The whole utterance is a refusal, with nothing else asked.
BARE_NO_RE = re.compile(r"^(no|nope|nah|nahi|nahin|na|नहीं|ना)[\s.!?।]*$", re.IGNORECASE)

WANT_RE = re.compile(
    r"("
    r"\b(yes|yeah|yep|sure|please|tell me|know more|more about|offer|sale|"
    r"what|how|price|delivery|return)\b"
    r"|हाँ|हां|बताओ|बताइए|बता दीजिए|और बता|कीमत|डिलीवरी|रिटर्न|सेल|ऑफर"
    r")",
    re.IGNORECASE,
)

FAREWELL_RE = re.compile(
    r"(आपके समय के लिए धन्यवाद|आपका दिन अच्छा|आपका दिन शुभ|"
    r"thank you for your time|have a (great|good|nice) day|"
    r"good\s*bye|\bgoodbye\b|take care|शुभ दिन|अलविदा)",
    re.IGNORECASE,
)


def _last_user_text(messages):
    last = ""
    for message in messages or []:
        if message.get("role") == "user":
            last = message_text(message)
    return last


def caller_is_done(messages):
    """The caller ended the conversation. A lone thank-you is not enough."""
    last = _last_user_text(messages).strip()
    if DONE_RE.search(last):
        return True
    if BARE_NO_RE.match(last):
        return True
    return bool(re.fullmatch(r"(bas|bass|बस)[\s.!?।]*", last, re.IGNORECASE))


def is_farewell(text):
    """The model is signing off instead of calling the hang-up function."""
    return bool(FAREWELL_RE.search(text or ""))


def closing_line(instruction):
    """The one sentence the end-of-call node is supposed to speak."""
    marker = "Say this closing line verbatim and then stop:"
    if marker not in (instruction or ""):
        return ""
    return instruction.split(marker, 1)[1].strip()


def caller_wants_more(messages):
    """They agreed to hear the offer or asked a question. Do not hang up."""
    last = _last_user_text(messages)
    if DONE_RE.search(last):
        return False
    return bool(WANT_RE.search(last))


def without_end_call(body):
    updated = dict(body)
    kept = []
    for tool in body.get("tools") or []:
        name = ((tool.get("function") or {}).get("name")) or ""
        if name == "done":
            continue
        kept.append(tool)
    updated["tools"] = kept
    return updated


def closing_instruction(messages):
    """The end-of-call node. Its prompt must be spoken, not replaced with the facts."""
    for message in messages or []:
        if message.get("role") != "system":
            continue
        text = message_text(message)
        if "NODE_ROLE: closing" in text:
            return text
    return ""


def force_sampling(body, include_handoff=True):
    requested = body.get("max_tokens") or MAX_TOKENS
    try:
        requested = int(requested)
    except (TypeError, ValueError):
        requested = MAX_TOKENS
    tools = list(body.get("tools") or [])
    if include_handoff and not any(
        (tool.get("function") or {}).get("name") == "request_handoff" for tool in tools
    ):
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
    """Release only finished sentences.

    Mulberry speaks one complete utterance at a time. Cutting a line into
    pieces makes English words inside Hindi come out separately and unclear.
    """
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
