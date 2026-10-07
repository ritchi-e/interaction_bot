"""Per-stream turn state machine for Deepgram Flux-compatible events.

Drives StartOfTurn / Update / EagerEndOfTurn / TurnResumed / EndOfTurn from
VAD speech/silence timing plus an optional smart-turn end-of-turn probability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class Event(Enum):
    START_OF_TURN = auto()
    UPDATE = auto()
    EAGER_END_OF_TURN = auto()
    TURN_RESUMED = auto()
    END_OF_TURN = auto()


@dataclass
class TurnConfig:
    # Milliseconds of VAD speech before StartOfTurn.
    start_speech_ms: float = 120.0
    # Throttle partial Update events.
    update_interval_ms: float = 150.0
    # Silence before considering EagerEndOfTurn / EndOfTurn.
    eager_silence_ms: float = 400.0
    eot_silence_ms: float = 550.0
    # Hard cap on silence before forcing EndOfTurn.
    eot_timeout_ms: float = 3500.0
    # Smart-turn probability thresholds (0–1). When smart-turn is unavailable,
    # silence alone is enough.
    eager_eot_threshold: float = 0.6
    eot_threshold: float = 0.85
    use_smart_turn: bool = True
    # Do not commit EndOfTurn while ASR text is still growing (unless timeout).
    transcript_stable_ms: float = 280.0


@dataclass
class TurnState:
    config: TurnConfig = field(default_factory=TurnConfig)
    in_turn: bool = False
    start_sent: bool = False
    speech_ms: float = 0.0
    silence_ms: float = 0.0
    transcript: str = ""
    last_update_ms: float = 0.0
    eager_sent: bool = False
    elapsed_ms: float = 0.0
    stable_ms: float = 0.0
    languages: list[str] = field(default_factory=lambda: ["hi"])

    def reset_turn(self) -> None:
        self.in_turn = False
        self.start_sent = False
        self.speech_ms = 0.0
        self.silence_ms = 0.0
        self.transcript = ""
        self.last_update_ms = 0.0
        self.eager_sent = False
        self.stable_ms = 0.0

    def on_audio(
        self,
        *,
        is_speech: bool,
        dt_ms: float,
        transcript: str,
        eot_prob: float | None,
    ) -> list[tuple[Event, dict[str, Any]]]:
        """Advance the state machine by ``dt_ms`` of audio.

        Returns zero or more Flux-style events as (Event, payload) pairs.
        """
        self.elapsed_ms += dt_ms
        events: list[tuple[Event, dict[str, Any]]] = []
        text = (transcript or "").strip()
        if text:
            if text == self.transcript:
                self.stable_ms += dt_ms
            else:
                self.transcript = text
                self.stable_ms = 0.0

        if is_speech:
            self.speech_ms += dt_ms
            self.silence_ms = 0.0
            if self.in_turn and self.eager_sent:
                events.append((Event.TURN_RESUMED, {"transcript": self.transcript}))
                self.eager_sent = False
            if not self.in_turn and self.speech_ms >= self.config.start_speech_ms:
                self.in_turn = True
            # Announce StartOfTurn only once we have ASR text. Firing it on
            # bare VAD hits lets line noise barge-in on the greeting and then
            # produces empty turns Dograh cannot use.
            if self.in_turn and self.transcript and not self.start_sent:
                events.append(
                    (
                        Event.START_OF_TURN,
                        {"transcript": self.transcript, "languages": list(self.languages)},
                    )
                )
                self.start_sent = True
                self.last_update_ms = self.elapsed_ms
            elif self.in_turn and self.start_sent and self.transcript:
                if self.elapsed_ms - self.last_update_ms >= self.config.update_interval_ms:
                    events.append(
                        (
                            Event.UPDATE,
                            {"transcript": self.transcript, "languages": list(self.languages)},
                        )
                    )
                    self.last_update_ms = self.elapsed_ms
            return events

        # Silence
        if not self.in_turn:
            self.speech_ms = 0.0
            return events

        self.silence_ms += dt_ms
        self.speech_ms = 0.0

        # Never started a real turn (VAD flicker, no ASR text) — just reset.
        if not self.start_sent:
            if self.silence_ms >= self.config.eot_silence_ms:
                self.reset_turn()
            return events

        timeout = max(self.config.eot_timeout_ms, self.config.eot_silence_ms)
        smart = eot_prob if (self.config.use_smart_turn and eot_prob is not None) else 1.0
        stable = self.stable_ms >= self.config.transcript_stable_ms

        if (
            not self.eager_sent
            and self.silence_ms >= self.config.eager_silence_ms
            and smart >= self.config.eager_eot_threshold
            and self.transcript.strip()
            and stable
        ):
            events.append(
                (
                    Event.EAGER_END_OF_TURN,
                    {"transcript": self.transcript, "languages": list(self.languages)},
                )
            )
            self.eager_sent = True

        end_ready = (
            self.silence_ms >= self.config.eot_silence_ms
            and smart >= self.config.eot_threshold
            and stable
        )
        force_end = self.silence_ms >= timeout
        if end_ready or force_end:
            if self.transcript.strip():
                events.append(
                    (
                        Event.END_OF_TURN,
                        {
                            "transcript": self.transcript,
                            "languages": list(self.languages),
                            "words": [],
                        },
                    )
                )
            self.reset_turn()
        return events


def flux_message(event: Event, payload: dict[str, Any]) -> dict[str, Any]:
    name = {
        Event.START_OF_TURN: "StartOfTurn",
        Event.UPDATE: "Update",
        Event.EAGER_END_OF_TURN: "EagerEndOfTurn",
        Event.TURN_RESUMED: "TurnResumed",
        Event.END_OF_TURN: "EndOfTurn",
    }[event]
    msg: dict[str, Any] = {
        "type": "TurnInfo",
        "event": name,
        "transcript": payload.get("transcript", ""),
    }
    if "languages" in payload:
        msg["languages"] = payload["languages"]
    if event == Event.END_OF_TURN and "words" in payload:
        msg["words"] = payload["words"]
    return msg
