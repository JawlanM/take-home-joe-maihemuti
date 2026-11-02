# Learning Log: Google Gemini SDK (`google-genai`)

**Why this was new:** I'd once called an LLM API with a raw key, but never used Google's
`google-genai` SDK, structured output, system instructions, or handled model limits and failures
properly. It's also the core of the AI feature, so learning it well mattered most.

## What I read

- Gemini API docs: text generation, **structured output** (passing a Pydantic model as
  `response_schema`), **system instructions**, and the **rate limits** page.
- The SDK's own types (`GenerateContentConfig`, `HttpOptions`, `ThinkingConfig`) by reading them in
  the installed package when the docs didn't answer something.
- `client.models.list()` output, to see which models my key could actually use.

## What confused me

- **The model I picked didn't exist for me.** `gemini-2.5-flash` returned a 404: "no longer
  available to new users". Listing models first would have saved time.
- **Newest wasn't usable.** `gemini-3.8-flash` took about 60 seconds per call and hit
  `504 DEADLINE_EXCEEDED`. `gemini-3.5-flash` answered in a few seconds. I had to measure, not assume.
- **Aliases.** I requested `gemini-3.5-flash`, but the quota error named `gemini-3.6-flash`, so the
  name I pass isn't always the exact model that runs.
- **Units and types.** `HttpOptions(timeout=...)` is in milliseconds, not seconds, and
  `thinking_level` wants the `ThinkingLevel` enum, not the string `"low"` (the type checker caught it).
- **A schema guarantees shape, not truth.** Structured output gave valid JSON every time, but the
  content can still follow injected instructions, so I still validate and ground the output.
- **Free-tier limits.** 5 requests a minute and 20 a day. Loading 10 seed candidates in a row
  produced `429 RESOURCE_EXHAUSTED` and `503 UNAVAILABLE`, which is why the seed loader now pauses.

## What I'd tell the next engineer

1. Call `models.list()` before choosing a model, then **pin the model name in config**, not code.
2. Time a real request before committing to a model; "latest" can be the slowest.
3. **Set a timeout explicitly** (milliseconds) and treat every error as a normal outcome, not an
   exception that reaches the user.
4. Keep the SDK behind one thin wrapper (`app/ai/gemini.py`) so tests can use a fake and the
   provider can change without touching the rest of the app.
5. Treat model output as untrusted input: parse strictly, check it against the source, never let it
   trigger actions.
6. Check which quota tier your key is on before any bulk run, and read the error messages: Gemini's
   429s say exactly which limit you hit and when to retry.
