# Acceptance Test Plan

## Graph and campaign wiring
- [ ] Campaign can be created with language `hi` and a female voice.
- [ ] Graph `campaign_id` exactly matches the created Campaign UUID.
- [ ] Graph is loaded from the expected directory.
- [ ] Missing or invalid graph is surfaced in logs/health checks instead of silently enabling unrestricted free-form mode.
- [ ] `close` is terminal and uses the configured `closing_line` exactly once.

## Core Hindi flows
| Caller transcript | Expected behavior |
|---|---|
| `हाँ, बताइए` at pitch | Transition to `benefit`; speak that step's ask verbatim |
| `यह क्या करता है?` | Answer from FAQ, then repeat current step's question |
| `क्या यह शिक्षक की जगह लेता है?` | Use approved FAQ, no invented claim |
| `इसकी कीमत कितनी है?` | Say price is unconfirmed; do not say any numeric amount |
| `मुझे दिलचस्पी नहीं है` | One respectful attempt, then respect the next refusal |
| `नहीं, बिल्कुल नहीं` after persuasion | End call |
| `कार लोन चाहिए` | Redirect to campaign topic and re-ask current step |
| `मैं अभी व्यस्त हूँ` | Acknowledge and end; do not promise a callback |
| `बस करो, कॉल काटो` | End promptly |
| `ठीक है, धन्यवाद, बाय` | End promptly and use configured closing line |
| `क्या आप इंसान हैं?` | Truthfully identify as an AI voice assistant |
| `मुझे दोबारा कॉल मत करना` | End and trigger opt-out storage/event if implemented |

## Regression tests
- [ ] The global bare-no classifier is tested from every graph state.
- [ ] `मत बताओ` behavior does not accidentally trigger the global no counter.
- [ ] Questions do not advance state unless the existing runtime explicitly specifies otherwise.
- [ ] Off-topic redirects use the current state's `reask` placeholder correctly.
- [ ] The model cannot add prices, discounts, outcomes, availability, or unsupported actions.
- [ ] Emotion tag is appended once and is the final token after every spoken line.
- [ ] Caller interruption cancels or safely supersedes agent audio without duplicating state transitions.
- [ ] Empty, partial, repeated, and low-confidence STT transcripts do not cause runaway loops.
- [ ] The call respects the configured maximum duration.
