# Agent Handoff: Hindi Voice Campaign Package

## Goal
Add a sample Hindi outbound campaign and a graph-driven conversation to the existing calling agent. The sample campaign is an online learning assistant introduction. Keep this as a test/demo campaign until product facts and consent language are approved.

## Files
- `campaign_form.json`: values to enter into the Campaign/CampaignContext/AgentProfile form. It is a handoff representation, not guaranteed to be a direct database import format.
- `context_guard/dialogue/graphs/online_learning_hindi.json`: dialogue graph in the described graph schema.
- `llm_system_prompt.md`: proposed LLM runtime prompt to merge into the existing prompt architecture.
- `test_plan.md`: manual and automated acceptance tests.

## Required setup
1. Create the campaign using `campaign_form.json` values.
2. Copy the actual campaign UUID from the created Campaign record.
3. Replace `REPLACE_WITH_ACTUAL_CAMPAIGN_UUID` in the graph's `campaign_id`.
4. Put the graph at `context_guard/dialogue/graphs/online_learning_hindi.json`.
5. Restart/reload the graph registry if the application caches graph files.
6. Verify graph lookup resolves this campaign UUID and does not fall back to free-form answering.
7. Confirm `language=hi` selects the Hindi STT configuration and the selected Svara voice is female.
8. Check the actual runtime's handling of `on_no`, terminal steps, closing line, emotion tags, and redirects before deploying.

## Important runtime mismatch to verify
The described global classifier routes the first bare "no" to `persuade` and the second bare "no" to hangup, regardless of the current step's `on_no`. Therefore `on_no` values in this graph may not be used for a first refusal. Decide whether this global behavior is intentional. Add tests for refusal at every state.

## Improvements recommended
- Use a strict typed schema for graph validation at startup. Reject unknown step references, missing `pitch`, missing `persuade`, or malformed `close`.
- Validate that `campaign_id` is a UUID and exactly matches one campaign.
- Add a dry-run mode that accepts caller text and shows classification, current state, next state, selected line, and reason without calling STT/TTS.
- Log per turn: campaign ID, state before/after, intent class, transition reason, LLM latency, STT final transcript, and TTS latency. Redact personal data.
- Keep graph transition logic deterministic. Use the LLM for factual answers and limited intent classification only if deterministic rules cannot resolve the turn.
- Add explicit states/actions for opt-out, human handoff, busy caller, and unsupported question if the runtime supports these. Do not promise a callback or message unless an action exists.
- Use a test set of Hindi and Hinglish utterances, including ASR variants, interruptions, short answers, and disfluencies.
- Keep prompts and graph lines short for latency and natural TTS. Confirm emotion tags are appended once by the runtime and are always the final token.
- Ensure a request to stop calls is recorded in an actual opt-out mechanism if one exists. Do not rely only on the dialogue transcript.

## Before production
Replace the sample product with a real approved campaign. Confirm legal basis/consent, calling-hour rules, caller identity disclosure, opt-out requirements, data retention, and any applicable telecom/DND requirements with the responsible compliance owner. Do not treat this demo package as legal approval.
