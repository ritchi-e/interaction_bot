from dialogue.graph import advance, after_greeting, graph_for, redirect_line, scripted_line
from dialogue.style import apply_style, choose_tag
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
    assert "दस दशमलव" in spoken
    assert "बढ़िया" not in spoken


def test_first_no_offers_more_instead_of_thirty_seconds():
    graph = graph_for(CAMPAIGN)
    step, mode, _refusals = after_greeting(graph, classify("नहीं", graph))
    assert step == "persuade"
    spoken = scripted_line(graph, step, mode, "call")
    assert "तीस सेकंड" not in spoken
    assert "ऑफ़र" in spoken
    assert "बढ़िया" not in spoken
    assert "!" not in spoken


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


def test_declining_a_detail_moves_to_the_next_unsaid_step():
    graph = graph_for(CAMPAIGN)
    heard = "नहीं नहीं जानना योग्यता क्या है?"
    step, mode, _refusals = advance(graph, "need", classify(heard, graph))
    assert step == "pitch"
    assert mode == "ask"
    assert "पचास हज़ार" in graph.step(step).ask


def test_thanks_mixed_with_a_refusal_hangs_up_and_a_refusal_does_not_repeat():
    graph = graph_for(CAMPAIGN)
    assert classify("नहीं नहीं जानना है, thank you.", graph) == "done"
    assert classify("thank you, what about the EMI?", graph) == "question"
    step, mode, refusals = advance(graph, "pitch", classify("नहीं नहीं जानना.", graph))
    assert step == "book"
    assert mode == "ask"
    assert refusals == 0
    assert graph.step(step).ask != graph.step("pitch").reask


def test_thank_you_ends_instead_of_counting_as_yes():
    graph = graph_for(CAMPAIGN)
    heard = "ठीक है very very thank you."
    assert classify(heard, graph) == "done"
    step, mode, _refusals = advance(graph, "pitch", "done")
    assert step == "close"
    assert mode == "close"


def test_a_bare_car_is_off_topic_without_the_word_loan():
    graph = graph_for(CAMPAIGN)
    assert classify("Car का लेनी थी मैंने तो.", graph) == "off_topic"
    assert classify("कार्ड नहीं चाहिए", graph) != "off_topic"


def test_car_loan_redirects_without_the_canned_handoff():
    graph = graph_for(CAMPAIGN)
    step, mode, _refusals = advance(graph, "ask_time", classify("कार लोन चाहिए", graph))
    assert step == "ask_time"
    assert mode == "redirect"
    spoken = redirect_line(graph, step, "call-1:कार लोन")
    assert spoken != HANDOFF
    assert "बात नहीं" not in spoken
    assert "नहीं बताया" not in spoken
    assert "दो मिनट" in spoken


def test_style_tag_follows_the_moment_and_stays_at_the_end():
    assert choose_tag("हां बताइए", "ask", "cheerful", "पर्सनल लोन पचास हजार तक है") == "clear"
    assert choose_tag("Car का लेनी थी", "redirect", "", "यह इस कॉल पर नहीं बताया जा सकता") == "formal"
    assert choose_tag("हां जी", "ask", "cheerful", "क्या दो मिनट मिल सकते हैं?") == "happy"
    assert choose_tag("", "answer", "calm", "मुझे खेद है, मैं समझ गई।") == "sad"
    spoken = apply_style("मुझे खेद है, मैं समझ गई।", "sad")
    assert spoken.endswith("<sad>।")
    spoken = apply_style("मुझे गुस्सा आ रहा है, मैं शांत हूँ। <anger>", "chat")
    assert spoken.endswith("<chat>।")
    assert "<anger>" not in spoken
    assert spoken.count("<") == 1
    both = apply_style("पहली बात। दूसरी बात।", "clear")
    assert both == "पहली बात <clear>। दूसरी बात <clear>।"


def test_invented_price_is_still_blocked():
    from guard import validate_sentence

    facts = "Prices (say these amounts only):\n- Rate: Rs 10.99"
    ok, reason = validate_sentence("The fee is Rs 999.", facts, [], [])
    assert ok is False
    assert reason == "unlisted_number"
