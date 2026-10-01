from guard import caller_is_done, caller_wants_more, closing_line, is_farewell


def _user(text):
    return [{"role": "user", "content": text}]


def test_english_goodbye_ends_the_call():
    assert caller_is_done(_user("no that will be all"))
    assert caller_is_done(_user("goodbye"))
    assert not caller_is_done(_user("thank you"))


def test_hindi_goodbye_ends_the_call():
    assert caller_is_done(_user("बस, और कुछ नहीं"))
    assert caller_is_done(_user("नहीं"))
    assert caller_is_done(_user("bas"))
    assert caller_is_done(_user("alvida"))


def test_interest_does_not_end_the_call():
    assert caller_wants_more(_user("हाँ, ऑफर के बारे में बताइए"))
    assert not caller_is_done(_user("हाँ, ऑफर के बारे में बताइए"))
    assert caller_wants_more(_user("yes tell me about the offer"))
    assert not caller_is_done(_user("yes tell me about the offer"))


def test_closing_line_is_a_farewell_and_can_be_read_back():
    line = "आपके समय के लिए धन्यवाद। आपका दिन अच्छा रहे।"
    assert is_farewell(line)
    instruction = (
        "CAMPAIGN_ID: x\nNODE_ROLE: closing\n"
        "Say this closing line verbatim and then stop:\n" + line
    )
    assert closing_line(instruction) == line
    assert not is_farewell("डिलीवरी तीन से पाँच दिन में होती है।")
