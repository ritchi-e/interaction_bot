from guard import caller_is_done, caller_wants_more, closing_line, is_farewell, take_complete


def _user(text):
    return [{"role": "user", "content": text}]


def test_english_goodbye_ends_the_call():
    assert caller_is_done(_user("no that will be all"))
    assert caller_is_done(_user("goodbye"))
    assert caller_is_done(_user("thank you"))
    assert caller_is_done(_user("thanks"))


def test_hindi_goodbye_ends_the_call():
    assert caller_is_done(_user("बस, और कुछ नहीं"))
    assert caller_is_done(_user("नहीं"))
    assert caller_is_done(_user("bas"))
    assert caller_is_done(_user("alvida"))
    assert caller_is_done(_user("धन्यवाद"))
    assert caller_is_done(_user("dhanyawad"))
    assert caller_is_done(_user("ठीक है धन्यवाद"))
    assert caller_is_done(_user("ok thank you"))


def test_thanks_with_a_question_does_not_end_the_call():
    assert not caller_is_done(_user("thank you, what about the EMI?"))
    assert not caller_is_done(_user("धन्यवाद, ईएमआई कितनी होगी?"))


def test_hangup_in_last_clause_ends_even_if_earlier_question_stale():
    # Cumulative/stale STT often keeps the previous question in the same string.
    assert caller_is_done(
        _user("आज जी बताइए प्लीज लिमिट बता सकते हैं। धन्यवाद")
    )
    assert caller_is_done(
        _user("एज लिमिट क्या है वो सब नहीं चाहिए")
    )
    assert caller_is_done(_user("age limit kya hai not interested"))
    assert not caller_wants_more(
        _user("आज जी बताइए। ठीक है धन्यवाद")
    )


def test_soft_deferral_in_tail_ends_the_call():
    assert caller_is_done(_user("अभी नहीं"))
    assert caller_is_done(_user("baad mein"))
    assert caller_is_done(_user("limit batao, बाद में"))


def test_interest_does_not_end_the_call():
    assert caller_wants_more(_user("हाँ, ऑफर के बारे में बताइए"))
    assert not caller_is_done(_user("हाँ, ऑफर के बारे में बताइए"))
    assert caller_wants_more(_user("yes tell me about the offer"))
    assert not caller_is_done(_user("yes tell me about the offer"))


def test_an_unfinished_phrase_waits_for_the_sentence_to_end():
    spoken, rest = take_complete("one two three four five six seven eight")
    assert spoken == []
    assert rest == "one two three four five six seven eight"


def test_closing_line_is_a_farewell_and_can_be_read_back():
    line = "आपके समय के लिए धन्यवाद। आपका दिन अच्छा रहे।"
    assert is_farewell(line)
    instruction = (
        "CAMPAIGN_ID: x\nNODE_ROLE: closing\n"
        "Say this closing line verbatim and then stop:\n" + line
    )
    assert closing_line(instruction) == line
    assert not is_farewell("डिलीवरी तीन से पाँच दिन में होती है।")
