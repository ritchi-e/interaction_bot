from dialogue.graph import graph_for, scripted_line, step_block

CAMPAIGN = "44dec4df-a595-4af0-a4a3-e5c0684609c2"


def test_hinglish_lines_keep_english_words_in_latin():
    graph = graph_for(CAMPAIGN)
    assert graph is not None
    assert graph.speech == "hinglish"
    spoken = scripted_line(graph, "pitch", "ask", "call")
    assert "students" in spoken
    assert "विद्यार्थी" not in spoken
    benefit = scripted_line(graph, "benefit", "ask", "call")
    assert "Play Store" in benefit
    assert "download" in benefit
    assert "ऐप" not in benefit


def test_hinglish_answer_instruction_names_the_mix():
    graph = graph_for(CAMPAIGN)
    block = step_block(graph, "faq", "answer", "")
    assert "Hinglish" in block
    assert "Latin" in block
