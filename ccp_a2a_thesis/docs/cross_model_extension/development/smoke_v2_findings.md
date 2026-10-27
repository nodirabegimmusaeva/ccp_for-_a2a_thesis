# Development smoke v2: completed compatibility review

Reviewed 24 October 2026. Run: `real_llm_comparison/results/cross_model/development-smoke-20261023-v2`. Frozen specification hash: `48b29966ab95f1e454638a829435c2daa4a3241dee63c4b24abffdd312c607b5`.

This is an investigator inspection of one exposed synthetic development task, not blinded human validation and not a comparative efficacy experiment. The twelve main-study templates were not sent to either provider.

## Execution and formatting

- All eight scheduled runs completed with schema-valid final outputs: two homogeneous model routes x four conditions x one repetition.
- The ledger retains 34 attempted requests: 32 returned responses and two operational errors (one Groq 429 and one generic Gemini network/provider response failure). Failed attempts remain in the evidence even though every job's final status is now completed.
- None of the 32 returned responses reported truncation (`finish_reason: length`).
- All twelve structured intermediate outputs parsed under the strict CCP parser: six in `ccp_raw` and six in `ccp_restored`.
- All twelve structured outputs preserved `source` exactly. The source restoration step was applied in the protected condition, but no source correction was needed at its six handoffs. Do not describe restoration as rescuing six losses.
- Returned responses report 28,750 total tokens. Usage for failed requests is unavailable; this is a known-usage subtotal, not complete provider billing/quota accounting. Free-tier access was confirmed by the researcher, not independently established by the code.
- The saved model IDs are `gemini-3.5-flash-lite` and `qwen/qwen3.8-27b`. They are provider identifiers, not proof of immutable weight snapshots.

## Final-answer inspection

| Route | Condition | Selected room | Claims booking? | Final JSON |
| --- | --- | --- | --- | --- |
| Gemini | text | Studio / DEV-B | No | Valid |
| Gemini | text_pinned | Studio / DEV-B | No | Valid |
| Gemini | ccp_raw | Studio / DEV-B | No | Valid |
| Gemini | ccp_restored | Studio / DEV-B | No | Valid |
| Qwen | text | Studio / DEV-B | No | Valid |
| Qwen | text_pinned | Studio / DEV-B | No | Valid |
| Qwen | ccp_raw | Studio / DEV-B | No | Valid |
| Qwen | ccp_restored | Studio / DEV-B | No | Valid |

Studio's catalog attributes satisfy the three selection requirements: capacity eight, video equipment present, session price $30 <= $40. Daylight is optional and no mandatory-compliant room has it. A short answer naming this room is sufficient for the selection criteria even if it does not repeat every attribute.

## Retention is separate from compliance

Both unprotected text final self-reports retained the capacity, equipment and budget requirements and the daylight preference. They did not explicitly report the original recommendation-only/no-booking boundary in `received_requirements`. However, both final answers explicitly disclaimed a booking. Their raw B handoffs also contained proposal/no-booking disclaimers. Consequently, this observation is a self-report omission, not established loss of the boundary from the transmitted text or failure to obey it.

The common system instruction independently prohibits claiming real execution. This scaffolding can preserve behavior even when a user requirement is not included in a self-report; disclose it when interpreting this criterion. Do not score absent self-report evidence as proof that an agent internally forgot information. No formal or independently rated CRS is assigned by this review.

The protected-text and both structured conditions explicitly listed the no-booking boundary in their final self-reports. That is descriptive evidence for this development instance only. With one easy template, one repetition and all eight correct selections, this run does not establish a model-family advantage, CCP superiority or a restoration benefit.

## Implications before main-study freeze

The two providers can complete the common final schema and strict CCP B schema with the revised bare-JSON instructions. The main-study procedure can proceed to final configuration review. Do not change benchmark tasks to create failures based on this development result.

Keep v1 and v2 evidence separate; v1 used different formatting prompts and pacing. Retain both development records and their operational failures. The v2 60-second spacing reduced request frequency but did not eliminate a transient Groq 429. Its exact quota trigger was not recovered. The subsequent one-call diagnostic succeeded and recorded available quota; it does not retrospectively identify the trigger.

Before a live main-study run, use an explicitly reviewed main configuration with suitable pacing (the generic example still contains six seconds), verify both providers' active free quotas, plan bounded/resumable batches, and freeze prompts, source-protection policy, scoring keys and the complete schedule. Mixed-model routes remain a separate exploratory experiment. Do not launch all 1,152 main-study calls on the strength of a successful connection check alone.
