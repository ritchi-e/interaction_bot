"""Hindi online-learning campaign: graph wiring and turn rules.

The phone, STT, and TTS are not part of these tests. They check the classifier,
the graph, and the fact guard that the live call uses.
"""

from dialogue.graph import (
    advance,
    after_greeting,
    declined_pending,
    graph_for,
    graph_problems,
    line_only_asks,
    next_unsaid_ask,
    redirect_line,
    replace_repeated_question,
    scripted_line,
    yes_should_explain,
)
from dialogue.intent import classify
from dialogue.style import apply_style
from guard import caller_is_done, validate_sentence

CAMPAIGN = "95905289-b76e-4286-b81a-701259ebb50a"
FACTS = (
    "यह ऑनलाइन पढ़ाई सहायक विद्यार्थियों को पढ़ाई से जुड़े सवाल समझने में मदद करता है। "
    "इस अभियान में कीमत की पुष्टि उपलब्ध नहीं है।"
)
FORBIDDEN = ["गारंटीड परीक्षा परिणाम", "अपुष्ट कीमत"]


def _graph():
    graph = graph_for(CAMPAIGN)
    assert graph is not None
    return graph


def test_graph_is_loaded_for_this_campaign_only():
    graph = _graph()
    assert graph.campaign_id == CAMPAIGN
    assert graph.start == "pitch"
    assert graph.step("close").terminal
    assert graph.step("close").ask == ""
    assert graph_for("00000000-0000-4000-8000-000000000000") is None


def test_invalid_graph_is_rejected():
    problems = graph_problems(
        {
            "campaign_id": "not-a-uuid",
            "start": "missing",
            "steps": {"pitch": {"on_yes": "nowhere"}},
        }
    )
    assert any("UUID" in item for item in problems)
    assert any("persuade" in item for item in problems)
    assert any("nowhere" in item for item in problems)


def test_hindi_and_hinglish_yes_and_no():
    graph = _graph()
    for heard in ("हाँ, बताइए", "हां बताओ", "haan bataiye", "yes"):
        assert classify(heard, graph) == "yes", heard
    for heard in ("नहीं", "नही", "nahi", "no"):
        assert classify(heard, graph) == "no", heard
    assert classify("यह क्या करता है?", graph) == "question"
    assert classify("price kitni hai?", graph) == "question"


def test_yes_at_pitch_speaks_the_benefit_step():
    graph = _graph()
    step, mode, _refusals = advance(graph, "pitch", classify("हाँ, बताइए", graph))
    assert step == "benefit"
    assert mode == "ask"
    spoken = scripted_line(graph, step, mode, "call")
    assert spoken == graph.step("benefit").ask
    assert "कीमत" not in spoken


def test_greeting_yes_does_not_skip_the_pitch():
    graph = _graph()
    step, mode, _refusals = after_greeting(graph, classify("हाँ, बताइए", graph))
    assert step == "pitch"
    assert mode == "ask"
    assert "सुनना चाहेंगे" in scripted_line(graph, step, mode, "call")


def test_repeated_refusal_from_every_step():
    graph = _graph()
    for step_id, step in graph.steps.items():
        if step.terminal:
            continue
        landed, mode, refusals = advance(graph, step_id, "no", 0)
        assert landed == "persuade", step_id
        assert mode == "ask"
        assert refusals == 1
        landed, mode, refusals = advance(graph, landed, "no", refusals)
        assert landed == "close", step_id
        assert mode == "close"
        assert refusals == 2


def test_not_interested_is_one_attempt_then_the_next_no_ends():
    graph = _graph()
    step, mode, refusals = advance(graph, "pitch", classify("मुझे दिलचस्पी नहीं है", graph))
    assert step == "persuade"
    assert "कोई बात नहीं" in scripted_line(graph, step, mode, "call")
    step, mode, _refusals = advance(graph, step, classify("नहीं, बिल्कुल नहीं", graph), refusals)
    assert step == "close"
    assert mode == "close"


def test_mat_batao_does_not_count_as_the_global_no():
    graph = _graph()
    assert classify("मत बताओ", graph) == "decline"
    step, mode, refusals = advance(graph, "benefit", "decline", 0)
    assert step == "interest"
    assert mode == "ask"
    assert refusals == 0
    assert "सुविधाओं" in scripted_line(graph, step, mode, "call")


def test_a_question_does_not_advance_the_step():
    graph = _graph()
    step, mode, _refusals = advance(graph, "benefit", classify("क्या यह शिक्षक की जगह लेता है?", graph))
    assert step == "benefit"
    assert mode == "answer"


def test_off_topic_stays_and_uses_the_current_reask():
    graph = _graph()
    heard = "कार लोन चाहिए"
    assert classify(heard, graph) == "off_topic"
    step, mode, _refusals = advance(graph, "interest", classify(heard, graph))
    assert step == "interest"
    assert mode == "redirect"
    spoken = redirect_line(graph, step, "call:कार")
    assert graph.step("interest").reask in spoken
    assert "लोन" not in spoken
    assert "पढ़ाई" in spoken or "सहायक" in spoken


def test_unsupported_price_is_blocked_and_no_amount_is_allowed():
    ok, reason = validate_sentence("कीमत 500 रुपये है।", FACTS, FORBIDDEN, [])
    assert ok is False
    assert reason == "unlisted_number"
    ok, reason = validate_sentence(
        "इस अभियान में कीमत की पुष्टि उपलब्ध नहीं है।",
        FACTS,
        FORBIDDEN,
        [],
    )
    assert ok, reason
    ok, reason = validate_sentence("नतीजा गारंटीड परीक्षा परिणाम है।", FACTS, FORBIDDEN, [])
    assert ok is False
    assert reason == "forbidden_topic"


def test_stop_busy_and_goodbye_end_the_call():
    graph = _graph()
    for heard in (
        "बस करो, कॉल काटो",
        "ठीक है, धन्यवाद, बाय",
        "मैं अभी व्यस्त हूँ",
        "मुझे दोबारा कॉल मत करना",
    ):
        assert classify(heard, graph) == "done", heard
        step, mode, _refusals = advance(graph, "faq", "done")
        assert step == "close"
        assert mode == "close"
    assert caller_is_done([{"role": "user", "content": "thank you, what about the EMI?"}]) is False


def test_emotion_tag_is_once_per_sentence_and_not_in_the_middle():
    spoken = apply_style(scripted_line(_graph(), "pitch", "ask", "call"), "happy")
    assert spoken.count("<") == spoken.count(">")
    assert "<happy>" in spoken
    assert not spoken.endswith("<happy>")
    assert spoken.endswith("?")
    assert " <happy>?" in spoken or spoken.endswith("<happy>?")
    assert spoken.index("<happy>") > spoken.index("चाहेंगे") - 1 or " <happy>" in spoken


def test_empty_or_partial_transcript_does_not_move_the_step():
    graph = _graph()
    assert classify("", graph) == "unclear"
    assert classify("ह", graph) == "unclear"
    step, mode, refusals = advance(graph, "pitch", "unclear", 0)
    assert step == "pitch"
    assert mode == "answer"
    assert refusals == 0


def test_a_no_plus_a_new_question_does_not_repeat_the_usefulness_question():
    heard = "नहीं मेरे बच्चे के लिए होगी तो आप बता सकते हैं कि यह app में चलता है या website में चलता है?"
    graph = _graph()
    assert declined_pending(heard)
    step, mode, _refusals = advance(graph, "benefit", classify(heard, graph))
    assert step == "benefit"
    assert mode == "answer"
    reply = (
        "इस जानकारी की अभी पुष्टि उपलब्ध नहीं है। "
        "क्या पढ़ाई में ऐसा सहायक आपके लिए उपयोगी हो सकता है?"
    )
    swapped = replace_repeated_question(
        reply,
        graph.step("benefit").ask,
        graph.step("benefit").reask,
        next_unsaid_ask(graph, "benefit"),
    )
    assert "उपयोगी हो सकता है" not in swapped
    assert "पुष्टि उपलब्ध नहीं है" in swapped
    assert "सुविधाओं" in swapped


def test_the_voice_does_not_receive_the_word_it_repeats():
    from spoken_numbers import speakable_hindi

    spoken = speakable_hindi("क्या पढ़ाई में ऐसी मदद आपके लिए उपयोगी होगी?")
    assert "होगी" not in spoken
    assert spoken.endswith("उपयोगी है?")
    graph = _graph()
    assert line_only_asks(graph.step("interest").ask)
    assert line_only_asks(graph.step("faq").ask)
    assert not line_only_asks(graph.step("benefit").ask)
    assert yes_should_explain(graph, "benefit")
    assert yes_should_explain(graph, "interest")
    assert not yes_should_explain(graph, "pitch")
