from dialogue.graph import advance, after_greeting, graph_for, redirect_line, scripted_line
from dialogue.intent import classify

CAMPAIGN = "86916f80-f2fe-4911-ad0a-e9847eb2db9d"
HANDOFF = "यह जानकारी मेरे पास नहीं है। एक टीममेट आपको व्हाट्सऐप पर मैसेज करेंगे या वापस कॉल करेंगे."


def test_first_no_sells_once_and_the_second_no_closes():
    graph = graph_for(CAMPAIGN)
    assert classify("नहीं", graph) == "no"
    step, mode, refusals = advance(graph, graph.start, "no", 0)
    assert step == "persuade"
    assert mode == "ask"
    assert refusals == 1
    step, mode, refusals = advance(graph, step, "no", refusals)
    assert step == "close"
    assert mode == "close"
    assert refusals == 2


def test_yes_after_the_greeting_gives_the_offer_instead_of_asking_again():
    graph = graph_for(CAMPAIGN)
    step, mode, refusals = after_greeting(graph, classify("हाँ", graph))
    assert step == "pitch"
    assert mode == "ask"
    assert refusals == 0
    spoken = scripted_line(graph, step, mode, "call")
    assert "दो मिनट" not in spoken
    assert "तीस सेकंड" not in spoken
    assert "ऑफ़र" not in spoken or "दस दशमलव" in spoken


def test_first_no_offers_more_instead_of_thirty_seconds():
    graph = graph_for(CAMPAIGN)
    step, mode, _refusals = after_greeting(graph, classify("नहीं", graph))
    assert step == "persuade"
    spoken = scripted_line(graph, step, mode, "call")
    assert "तीस सेकंड" not in spoken
    assert "ऑफ़र" in spoken


def test_yes_moves_to_the_need_question():
    graph = graph_for(CAMPAIGN)
    step, mode, _refusals = advance(graph, "ask_time", classify("हाँ", graph))
    assert step == "need"
    assert mode == "ask"


def test_yes_tell_me_still_advances():
    graph = graph_for(CAMPAIGN)
    heard = "हां जी मिल सकते हैं बताइए."
    step, mode, _refusals = advance(graph, "ask_time", classify(heard, graph))
    assert step == "need"
    assert mode == "ask"


def test_declining_a_detail_reasks_instead_of_closing_or_wandering():
    graph = graph_for(CAMPAIGN)
    heard = "नहीं नहीं जानना योग्यता क्या है?"
    step, mode, _refusals = advance(graph, "need", classify(heard, graph))
    assert step == "need"
    assert mode == "reask"


def test_car_loan_redirects_without_the_canned_handoff():
    graph = graph_for(CAMPAIGN)
    step, mode, _refusals = advance(graph, "ask_time", classify("कार लोन चाहिए", graph))
    assert step == "ask_time"
    assert mode == "redirect"
    spoken = redirect_line(graph, step, "call-1:कार लोन")
    assert spoken != HANDOFF
    assert "दो मिनट" in spoken


def test_invented_price_is_still_blocked():
    from guard import validate_sentence

    facts = "Prices (say these amounts only):\n- Rate: Rs 10.99"
    ok, reason = validate_sentence("The fee is Rs 999.", facts, [], [])
    assert ok is False
    assert reason == "unlisted_number"
