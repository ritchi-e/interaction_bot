from spoken_numbers import SENTENCE_GAP, expand_numbers, split_sentences


def test_five_thousand_is_words_in_english_and_hindi():
    assert expand_numbers("The limit is 5000.", "English") == "The limit is five thousand."
    assert expand_numbers("लिमिट 5000 है", "Hindi") == "लिमिट पाँच हज़ार है"
    assert expand_numbers("लिमिट ५००० है", "Hindi") == "लिमिट पाँच हज़ार है"


def test_two_sentences_are_split_for_a_pause():
    parts = split_sentences("जी। क्या आपको पर्सनल लोन चाहिए?")
    assert parts == ["जी।", "क्या आपको पर्सनल लोन चाहिए?"]
    assert len(SENTENCE_GAP) == int(24000 * 0.4) * 2


def test_decimal_rate_is_not_read_digit_by_digit_as_a_whole():
    assert "ten point nine nine" in expand_numbers("rate 10.99", "English")
    assert "दस दशमलव नौ नौ" in expand_numbers("रेट 10.99", "Hindi")
    spoken = expand_numbers("ब्याज दर सालाना १०.९९ प्रतिशत से शुरू होती है।", "Hindi")
    assert "दस दशमलव नौ नौ" in spoken
    assert "१०.९९" not in spoken
    assert "10.99" not in spoken
