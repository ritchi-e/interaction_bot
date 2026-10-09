"""Load a campaign's directed steps and move one turn along them."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_GRAPHS = Path(__file__).resolve().parent / "graphs"


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


@dataclass(frozen=True)
class DialogueGraph:
    campaign_id: str
    start: str
    steps: dict[str, Step]
    off_topic_markers: tuple[str, ...]
    redirects: tuple[str, ...]

    def step(self, step_id: str) -> Step:
        return self.steps[step_id]


def load_graphs() -> dict[str, DialogueGraph]:
    found: dict[str, DialogueGraph] = {}
    if not _GRAPHS.is_dir():
        return found
    for path in sorted(_GRAPHS.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
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
            )
        graph = DialogueGraph(
            campaign_id=str(raw["campaign_id"]),
            start=str(raw.get("start") or "ask_time"),
            steps=steps,
            off_topic_markers=tuple(raw.get("off_topic_markers") or ()),
            redirects=tuple(raw.get("redirects") or ()),
        )
        found[graph.campaign_id] = graph
    return found


_CACHE: dict[str, DialogueGraph] | None = None


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
        return step.id, "reask", refusals
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
    if mode == "reask":
        openings = ("ठीक है। ", "कोई बात नहीं। ", "अच्छा। ")
    else:
        openings = ("जी। ", "अच्छा। ", "ठीक है। ")
    opening = openings[abs(hash(salt)) % len(openings)]
    return (opening + question).strip()


def redirect_line(graph: DialogueGraph, step_id: str, salt: str) -> str:
    step = graph.step(step_id if step_id in graph.steps else graph.start)
    question = step.reask or step.ask
    templates = graph.redirects or (
        "यह इस कॉल पर नहीं बताया जा सकता। {reask}",
    )
    template = templates[abs(hash(salt)) % len(templates)]
    return template.format(reask=question).strip()


def step_block(graph: DialogueGraph, step_id: str, mode: str) -> str:
    step = graph.step(step_id if step_id in graph.steps else graph.start)
    question = step.ask or step.reask
    again = step.reask or step.ask
    if mode == "ask":
        instruction = (
            "The caller just answered the previous question. Ask only the next "
            "question, in your own words, in one or two sentences. Do not repeat "
            f"the greeting. Next question: {question}"
        )
    else:
        instruction = (
            "Answer only from FACTS, in one sentence, then ask the current "
            f"question again: {again} If the answer is not in FACTS, do not use "
            "a canned handoff line. Say you cannot cover that on this call, in "
            f"fresh wording, and ask: {again}"
        )
    return (
        "CURRENT_STEP:\n"
        f"- id: {step.id}\n"
        f"- goal: {step.goal}\n"
        f"- {instruction}\n"
        "- Stay on this step. Do not jump to a later question.\n"
    )
