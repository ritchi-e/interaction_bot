"""Locum (Dr. Locum) campaign: graph wiring and interest recording steps."""

from dialogue.graph import advance, after_greeting, graph_for, graph_problems, scripted_line
from dialogue.intent import classify

CAMPAIGN = "4e377637-2559-4707-9963-b13652dc7f96"


def _graph():
    graph = graph_for(CAMPAIGN)
    assert graph is not None
    return graph


def test_locum_graph_loads():
    graph = _graph()
    assert graph.campaign_id == CAMPAIGN
    assert graph.start == "pitch"
    assert "interest" in graph.steps
    assert graph.step("close").terminal
    assert graph.step("close").ask == ""
    assert not graph_problems(
        {
            "campaign_id": CAMPAIGN,
            "start": "pitch",
            "steps": {
                name: {
                    "ask": step.ask,
                    "reask": step.reask,
                    "on_yes": step.on_yes,
                    "on_no": step.on_no,
                    "on_done": step.on_done,
                    "terminal": step.terminal,
                }
                for name, step in graph.steps.items()
            },
        }
    )


def test_yes_at_pitch_lands_on_job():
    graph = _graph()
    step, mode, _ = advance(graph, "pitch", classify("हाँ, बताइए", graph))
    assert step == "job"
    assert mode == "ask"
    spoken = scripted_line(graph, step, mode, "call")
    assert "{job_title}" in spoken
    assert "Dr. Locum" in spoken


def test_yes_at_job_lands_on_interest():
    graph = _graph()
    step, mode, _ = advance(graph, "job", classify("हाँ", graph))
    assert step == "interest"
    assert mode == "ask"
    assert "दिलचस्पी" in graph.step("interest").ask


def test_yes_at_interest_ends_call():
    graph = _graph()
    step, mode, _ = advance(graph, "interest", classify("हाँ, दिलचस्पी है", graph))
    assert step == "close"
    assert mode == "close"


def test_no_at_interest_gets_one_persuade():
    graph = _graph()
    step, mode, refusals = advance(graph, "interest", classify("नहीं", graph))
    assert step == "persuade"
    assert mode == "ask"
    assert refusals == 1
    step, mode, refusals = advance(graph, "persuade", classify("नहीं", graph), refusals)
    assert step == "close"
    assert mode == "close"


def test_greeting_yes_starts_at_pitch():
    graph = _graph()
    step, mode, _ = after_greeting(graph, classify("हाँ", graph))
    assert step == "pitch"
    assert mode == "ask"
