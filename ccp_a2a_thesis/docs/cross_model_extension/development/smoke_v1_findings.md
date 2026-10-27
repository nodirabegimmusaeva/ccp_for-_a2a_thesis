# Development smoke v1: diagnostic findings

Inspected 23 October 2026. Source: `real_llm_comparison/results/cross_model/development-smoke-20261023-v1/state.json`. Development-only, one synthetic room-selection task; no benchmark task was generated.

The session stopped after seven attempted requests: six returned responses and one Groq HTTP 429 (`rate_limit_exceeded`, Retry-After 22 seconds). Gemini completed B1/B2/B3/C in the protected-CCP condition; Qwen completed B1/B2 in the text condition before the B3 rate-limit rejection. The full eight-run schedule was not completed.

Gemini's final response correctly selected Studio/DEV-B, described capacity eight, video equipment and the $30 price, treated daylight as optional, and did not claim an actual booking. The response was a JSON object wrapped in Markdown code fences. Its reported requirements included all task requirements and the optional preference. The strict final parser rejected the wrapping. Do not equate this structural rejection with a wrong selection or lost constraints.

All three Gemini intermediate protected-CCP outputs were also rejected by strict parsing, triggering source restoration. The structural source-change flags therefore include unparseable wrapping; they are not three demonstrated semantic omissions. Retain the raw outputs for inspection.

All six returned responses had `finish_reason: stop`; none was reported truncated. The six responses reported 5,470 total tokens combined. The failed request has no recorded token usage, so this is a known-usage subtotal, not proof of complete provider usage accounting.

Development adjustments for v2:

- Explicitly request bare JSON without Markdown/code fences at all CCP B stages and for C in every condition. Strict parsers remain unchanged; no hidden code-fence stripping or output repair is introduced.
- Use a separate development configuration with 60 seconds between calls to the same provider. This is conservative pacing, not proof of the account's exact token/minute quota or a guarantee against another 429. Service time and pacing remain separately recorded. A new process resets its local pacing clock; respect provider Retry-After guidance before restarting after a limit.
- Prepare a fresh v2 manifest and preserve v1, including its invalid final output and failed API attempt. Do not continue a frozen run with changed prompts/configuration or silently replace the failed evidence.

The twelve main-study task templates remain unchanged and unfrozen. These development findings do not support a comparison of model quality or CCP efficacy.
