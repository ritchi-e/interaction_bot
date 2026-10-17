"""Load a campaign's directed steps and move one turn along them."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("context_guard")
_GRAPHS = Path(__file__).resolve().parent / "graphs"
_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_GRAPH_ERRORS: list[str] = []
# A no in front of a longer turn. A bare no is matched separately.
_LEADING_NO = re.compile(
    r"^(?:नहीं|नही|ना|no|nahi|nah)(?=\s|$|[,.!?।])",
    re.IGNORECASE,
)
_BARE_NO = re.compile(
    r"^(?:no|nope|nah|nahi|nahin|na|नहीं|ना|नही)[\s.!?।]*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Step:
    id: str
    goal: str
    ask: str
    reask: str
    on_yes: str
    on_no: str
    on_done: str
    terminal: bool
    tone: str


@dataclass(frozen=True)
class DialogueGraph:
    campaign_id: str
    start: str
    steps: dict[str, Step]
    off_topic_markers: tuple[str, ...]
    redirects: tuple[str, ...]
    speech: str = "hi"

    def step(self, step_id: str) -> Step:
        return self.steps[step_id]


def graph_problems(raw: dict) -> list[str]:
    """Reject a graph the runtime cannot follow. A bad file is not loaded."""
    problems = []
    campaign_id = str(raw.get("campaign_id") or "")
    if not _UUID.fullmatch(campaign_id):
        problems.append("campaign_id is not a UUID")
    steps = raw.get("steps")
    if not isinstance(steps, dict) or not steps:
        problems.append("steps is missing")
        return problems
    start = str(raw.get("start") or "")
    if start not in steps:
        problems.append(f"start {start!r} is not a step")
    for required in ("persuade", "close"):
        if required not in steps:
            problems.append(f"missing step {required}")
    close = steps.get("close")
    if isinstance(close, dict):
        if not close.get("terminal"):
            problems.append("close must be terminal")
        if str(close.get("ask") or "").strip():
            problems.append("close ask must be empty; the end step speaks the closing line")
    for step_id, item in steps.items():
        if not isinstance(item, dict):
            problems.append(f"{step_id} is not an object")
            continue
        for key in ("on_yes", "on_no", "on_done"):
            target = str(item.get(key) or "")
            if target and target not in steps:
                problems.append(f"{step_id}.{key} points to unknown step {target}")
    return problems


def load_graphs() -> dict[str, DialogueGraph]:
    global _GRAPH_ERRORS
    found: dict[str, DialogueGraph] = {}
    errors: list[str] = []
    if not _GRAPHS.is_dir():
        _GRAPH_ERRORS = errors
        return found
    for path in sorted(_GRAPHS.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        problems = graph_problems(raw)
        if problems:
            message = f"{path.name}: " + "; ".join(problems)
            errors.append(message)
            log.warning("dialogue graph not loaded: %s", message)
            continue
        steps = {}
        for step_id, item in (raw.get("steps") or {}).items():
            steps[step_id] = Step(
                id=step_id,
                goal=str(item.get("goal") or ""),
                ask=str(item.get("ask") or ""),
                reask=str(item.get("reask") or item.get("ask") or ""),
                on_yes=str(item.get("on_yes") or ""),
                on_no=str(item.get("on_no") or ""),
                on_done=str(item.get("on_done") or "close"),
                terminal=bool(item.get("terminal")),
                tone=str(item.get("tone") or "cheerful"),
            )
        graph = DialogueGraph(
            campaign_id=str(raw["campaign_id"]),
            start=str(raw.get("start") or "ask_time"),
            steps=steps,
            off_topic_markers=tuple(raw.get("off_topic_markers") or ()),
            redirects=tuple(raw.get("redirects") or ()),
            speech="hinglish" if raw.get("speech") == "hinglish" else "hi",
        )
        found[graph.campaign_id] = graph
        log.info("dialogue graph loaded campaign=%s file=%s", graph.campaign_id, path.name)
    _GRAPH_ERRORS = errors
    return found


_CACHE: dict[str, DialogueGraph] | None = None


def graph_report() -> dict:
    """Which campaign graphs loaded, and which files were rejected."""
    graph_for("")
    cache = _CACHE or {}
    return {"loaded": sorted(cache), "errors": list(_GRAPH_ERRORS)}


def graph_for(campaign_id: str) -> DialogueGraph | None:
    global _CACHE
    if _CACHE is None:
        _CACHE = load_graphs()
    return _CACHE.get((campaign_id or "").strip())


def after_greeting(graph: DialogueGraph, intent: str, refusals: int = 0) -> tuple[str, str, int]:
    """The greeting already asked to talk. Do not ask that again.

    A yes, a question, or an unclear reply moves straight to the offer.
    A bare no still gets one sales try. Goodbye still ends the call.
    """
    if intent in {"no", "done", "off_topic", "decline"}:
        return advance(graph, graph.start, intent, refusals)
    return graph.start, "ask", refusals


def advance(graph: DialogueGraph, step_id: str, intent: str, refusals: int = 0) -> tuple[str, str, int]:
    """Return the next step, what to say, and how many refusals have been heard.

    The first ``no`` gets one sales try. A second ``no`` ends the call.
    ``done`` (goodbye, thank you) still ends immediately.
    """
    step = graph.step(step_id if step_id in graph.steps else graph.start)
    if step.terminal:
        return step.id, "close", refusals
    if intent == "off_topic":
        return step.id, "redirect", refusals
    if intent == "decline":
        # They refused this detail. Say the next unsaid step, not this question again.
        nxt = step.on_yes or "close"
        if nxt == step.id:
            return "close", "close", refusals
        return (*_land(graph, nxt), refusals)
    if intent == "done":
        landed, mode = _land(graph, step.on_done or "close")
        return landed, mode, refusals
    if intent == "yes":
        landed, mode = _land(graph, step.on_yes or step.id)
        return landed, mode, refusals
    if intent == "no":
        if refusals >= 1:
            return "close", "close", refusals + 1
        return "persuade", "ask", refusals + 1
    return step.id, "answer", refusals


def _land(graph: DialogueGraph, step_id: str) -> tuple[str, str]:
    step = graph.step(step_id if step_id in graph.steps else "close")
    if step.terminal:
        return step.id, "close"
    return step.id, "ask"


def scripted_line(graph: DialogueGraph, step_id: str, mode: str, salt: str) -> str:
    """A fixed next line, so a yes cannot wander into a later fact."""
    step = graph.step(step_id if step_id in graph.steps else graph.start)
    question = step.ask if mode == "ask" else (step.reask or step.ask)
    # Speak the step itself. A stock opener ("बहुत बढ़िया") made every turn
    # sound the same, regardless of what the caller just said.
    return question.strip()


def redirect_line(graph: DialogueGraph, step_id: str, salt: str) -> str:
    step = graph.step(step_id if step_id in graph.steps else graph.start)
    question = step.reask or step.ask
    templates = graph.redirects or (
        "इस कॉल पर पर्सनल लोन की बात है। {reask}",
    )
    template = templates[abs(hash(salt)) % len(templates)]
    return template.format(reask=question).strip()


def declined_pending(text: str) -> bool:
    """A no to the question just asked, followed by something else.

    A bare no is handled by the graph. This is "no, it is for my child, how
    does the app work?" The pending question has already been answered.
    """
    raw = " ".join((text or "").split())
    if not raw or _BARE_NO.match(raw):
        return False
    return _LEADING_NO.match(raw) is not None


def line_only_asks(text: str) -> bool:
    """True when this line is only a question, with nothing explained first."""
    parts = [part.strip() for part in re.split(r"(?<=[.!?।])\s+", text or "") if part.strip()]
    if not parts:
        return False
    return all(_is_question(part) for part in parts)


def _is_question(text: str) -> bool:
    raw = text or ""
    return "?" in raw or "क्या" in raw or raw.endswith(("चाहेंगे", "चाहिए", "चाहोगे"))


def yes_should_explain(graph: DialogueGraph, step_id: str) -> bool:
    """A yes would otherwise land on another bare question.

    "Shall I tell you the features?" must be answered with the features,
    not with "what do you want to know?"
    """
    step = graph.step(step_id if step_id in graph.steps else graph.start)
    if not step.on_yes:
        return False
    nxt = graph.step(step.on_yes)
    if nxt.terminal or nxt.id == step.id:
        return False
    return line_only_asks(nxt.ask)


def next_unsaid_ask(graph: DialogueGraph, step_id: str) -> str:
    """The next step's question. Empty when the next step ends the call."""
    step = graph.step(step_id if step_id in graph.steps else graph.start)
    nxt = graph.step(step.on_yes) if step.on_yes else None
    if nxt is None or nxt.terminal or nxt.id == step.id:
        return ""
    return (nxt.ask or "").strip()


def replace_repeated_question(text: str, ask: str, reask: str, replacement: str) -> str:
    """Drop a sentence that asks the question the caller already answered."""
    parts = [part.strip() for part in re.split(r"(?<=[.!?।])\s+", text or "") if part.strip()]
    if not parts:
        return text or ""
    targets = [piece for piece in (_flat(ask), _flat(reask)) if piece]
    kept = []
    swapped = False
    for part in parts:
        flat = _flat(part)
        same = bool(flat) and any(flat == target or target in flat or flat in target for target in targets)
        if same:
            if not swapped and replacement:
                kept.append(replacement)
                swapped = True
            continue
        kept.append(part)
    return " ".join(kept).strip()


def _flat(text: str) -> str:
    bare = re.sub(r"<[^>]+>", "", text or "")
    bare = re.sub(r"[।.!?…,]", "", bare)
    return " ".join(bare.split())


def step_block(graph: DialogueGraph, step_id: str, mode: str, follow: str = "", avoid_repeat: bool = False) -> str:
    step = graph.step(step_id if step_id in graph.steps else graph.start)
    question = step.ask or step.reask
    again = step.reask or step.ask
    hinglish = graph.speech == "hinglish"
    kind = "Hinglish" if hinglish else "Hindi"
    mix = ""
    if hinglish:
        mix = (
            " Speak everyday Hinglish. Hindi words in Devanagari, English words in Latin. "
            "Say student, app, download, exam, online, and assistant in Latin, not as formal Hindi."
        )
    if step.tone == "cheerful" and mode != "reask":
        mood = (
            "The caller is still with you. Answer what they just said, in short "
            "warm sentences. Do not start with बहुत बढ़िया, बहुत अच्छा, or very good."
        )
    else:
        mood = (
            "The caller refused, declined a detail, or this step is not a "
            "celebration. Be calm and brief. No exclamation. Do not say बहुत बढ़िया, "
            "अच्छा!, or सुनिए!."
        )
    if mode == "ask":
        instruction = (
            "The caller just answered the previous question. Ask only the next "
            "question, in your own words, in one or two short sentences. Do not repeat "
            f"the greeting. Next question: {question} {mood}"
        )
    elif follow:
        instruction = (
            "They agreed to what you just offered. Tell them more about that "
            f"same thing, from FACTS, in two short {kind} sentences. Use facts "
            "that were not already in the question they just heard. Do not ask "
            "any question in this reply. Do not change the subject, and do not "
            "say you will tell them later. "
            f"What they agreed to: {follow} {mood}"
        )
    else:
        if avoid_repeat:
            nxt = next_unsaid_ask(graph, step.id)
            follow_up = (
                f"If you ask one follow-up, ask only this: {nxt}"
                if nxt
                else "Do not ask another question."
            )
            instruction = (
                "They already answered the question you just asked, and then asked "
                "something else. If their question is written in FACTS, say that "
                "answer now. If it is not in FACTS, say only the handoff line. "
                "Do not ask that question again. "
                f"{follow_up} {mood}"
            )
        else:
            instruction = (
                "They asked a question. If the answer is written in FACTS, say that "
                f"answer now, in one or two short {kind} sentences, using those words. "
                "Do not say you cannot tell them yet. Do not say you will explain it "
                "later. Do not start with a different topic, including the interest "
                "rates, when they asked about something else. After the answer, one "
                f"short question is enough. Do not repeat this if they refused it: {again} {mood}"
            )
    return (
        "CURRENT_STEP:\n"
        f"- id: {step.id}\n"
        f"- goal: {step.goal}\n"
        f"- {instruction}{mix}\n"
        "- An allowed question is answered in this reply, even when a later step also covers it.\n"
        "- Do not invent a fact that is not in FACTS.\n"
    )
