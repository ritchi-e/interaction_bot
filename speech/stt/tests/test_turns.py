from turns import Event, TurnConfig, TurnState, flux_message


def test_start_update_eager_end_happy_path():
    state = TurnState(
        config=TurnConfig(
            start_speech_ms=100,
            update_interval_ms=100,
            eager_silence_ms=200,
            eot_silence_ms=300,
            eot_timeout_ms=1200,
            eager_eot_threshold=0.5,
            eot_threshold=0.7,
            use_smart_turn=True,
            transcript_stable_ms=100,
        )
    )
    events = []
    # 120ms speech -> StartOfTurn
    events += state.on_audio(is_speech=True, dt_ms=120, transcript="नमस्ते", eot_prob=None)
    assert events[0][0] == Event.START_OF_TURN
    # more speech past update interval
    events += state.on_audio(is_speech=True, dt_ms=150, transcript="नमस्ते जी", eot_prob=None)
    assert any(e[0] == Event.UPDATE for e in events)
    # silence + high eot prob -> Eager then End
    events += state.on_audio(is_speech=False, dt_ms=220, transcript="नमस्ते जी", eot_prob=0.8)
    assert any(e[0] == Event.EAGER_END_OF_TURN for e in events)
    events += state.on_audio(is_speech=False, dt_ms=100, transcript="नमस्ते जी", eot_prob=0.9)
    assert any(e[0] == Event.END_OF_TURN for e in events)
    assert state.in_turn is False


def test_turn_resumed_after_eager():
    state = TurnState(
        config=TurnConfig(
            start_speech_ms=50,
            eager_silence_ms=100,
            eot_silence_ms=500,
            eot_timeout_ms=2000,
            eager_eot_threshold=0.5,
            eot_threshold=0.9,
            transcript_stable_ms=50,
        )
    )
    state.on_audio(is_speech=True, dt_ms=60, transcript="hello", eot_prob=None)
    state.on_audio(is_speech=False, dt_ms=120, transcript="hello", eot_prob=0.8)
    assert state.eager_sent
    resumed = state.on_audio(is_speech=True, dt_ms=40, transcript="hello there", eot_prob=None)
    assert resumed[0][0] == Event.TURN_RESUMED
    assert state.eager_sent is False


def test_hard_timeout_forces_end_without_smart_turn():
    state = TurnState(
        config=TurnConfig(
            start_speech_ms=50,
            eot_silence_ms=300,
            eot_timeout_ms=400,
            eager_silence_ms=200,
            use_smart_turn=False,
            transcript_stable_ms=50,
        )
    )


def test_unstable_transcript_delays_end_until_stable_or_timeout():
    state = TurnState(
        config=TurnConfig(
            start_speech_ms=50,
            eager_silence_ms=100,
            eot_silence_ms=200,
            eot_timeout_ms=800,
            eager_eot_threshold=0.5,
            eot_threshold=0.7,
            use_smart_turn=True,
            transcript_stable_ms=300,
        )
    )
    state.on_audio(is_speech=True, dt_ms=60, transcript="अभी तो", eot_prob=None)
    # ASR still growing during silence — must not EndOfTurn yet.
    events = state.on_audio(is_speech=False, dt_ms=250, transcript="अभी तो नहीं", eot_prob=0.95)
    assert not any(e[0] == Event.END_OF_TURN for e in events)
    events = state.on_audio(is_speech=False, dt_ms=250, transcript="अभी तो नहीं चाहिए", eot_prob=0.95)
    assert not any(e[0] == Event.END_OF_TURN for e in events)
    # Stable long enough + silence -> end.
    events = state.on_audio(
        is_speech=False, dt_ms=350, transcript="अभी तो नहीं चाहिए", eot_prob=0.95
    )
    assert any(e[0] == Event.END_OF_TURN for e in events)
    state.on_audio(is_speech=True, dt_ms=60, transcript="ok", eot_prob=None)
    events = state.on_audio(is_speech=False, dt_ms=420, transcript="ok", eot_prob=None)
    assert any(e[0] == Event.END_OF_TURN for e in events)


def test_flux_message_shape():
    msg = flux_message(Event.END_OF_TURN, {"transcript": "hi", "languages": ["en"], "words": []})
    assert msg["type"] == "TurnInfo"
    assert msg["event"] == "EndOfTurn"
    assert msg["transcript"] == "hi"
    assert msg["languages"] == ["en"]
