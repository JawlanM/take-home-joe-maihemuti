# Write-up

## What I built and what I left out

A working end-to-end slice of every required feature: add, list with stage/role filters,
sort by date or pipeline stage, detail view, any-to-any stage moves, append-only notes,
archive and delete, and an AI summary per candidate. I spent the remaining time on the parts
the brief weights most (the AI module, its handling of bad input, and tests) rather than on
extra features. Authentication and real deployment are out of scope; a deployment design is in
[DEPLOYMENT.md](DEPLOYMENT.md).

## Design choices

- **FastAPI + MongoDB.** A candidate is one self-contained record, and notes are append-only
  and always read with their candidate, so they're embedded in the candidate document: no
  joins, and the append-only rule is enforced by only ever using `$push` (there is no
  endpoint to edit or delete a note).
- **Layered backend:** `routes -> service -> repository`. Routes only translate HTTP; the
  service holds the rules; the repository is the only code that touches MongoDB. The service
  receives the summariser as a function, so tests swap in a fake.
- **Archive vs delete.** Archive is a soft delete (hidden from the list by default, data kept,
  reversible). Delete is permanent and confirmed in the UI.
- **Sort by stage means pipeline order**, not alphabetical (which would put Interview first).
  There's a test for exactly that.
- **Edit is included** although the brief doesn't list it, so a candidate who sends a new
  resume can be updated without delete-and-re-add (which would lose their notes). The summary
  regenerates only when the resume or cover-letter text changes; editing a phone number
  doesn't cost an AI call.
- **`.txt` upload is read in the browser** into the text box, so the user sees exactly what's
  saved and the backend only ever handles text.

## The AI feature

Everything lives in `backend/app/ai/`, behind one function:
`summarise(resume_text, cover_letter_text) -> summary`. It runs five steps:

1. **Clean the input:** Unicode normalisation, strip control characters, collapse whitespace,
   cap at 20,000 characters (and flag the summary as truncated), and remove any `<resume>`
   tags so the text can't close its own wrapper.
2. **Pre-check:** if there's almost nothing readable, return "no readable text" without
   calling the model.
3. **Prompt:** the rules go in Gemini's *system instruction*; the applicant's text goes
   separately, wrapped in `<resume>` tags and described as untrusted data that is never an
   instruction. The model is told to report only what's stated, never include personal
   details, and to set a `suspicious_content` flag if the text tries to instruct it. Only the
   resume and cover letter are sent; name, email and phone never leave the app.
4. **Structured output:** Gemini must return JSON matching a schema (summary, skills,
   highlights, two flags). Low temperature, output-token cap, 30-second timeout.
5. **Validate and ground:** the JSON is parsed strictly (anything malformed becomes
   "failed"), and any skill that doesn't literally appear in the resume is dropped.

The output is **display-only**: it can't change the candidate's stage or trigger anything,
React renders it as plain text (so a `<script>` in a resume is shown, never run), it's
labelled as AI-generated, and a visible warning appears when `suspicious_content` is set.
Any failure (network, timeout, rate limit, bad output) becomes a "failed" summary with a
Regenerate button; saving the candidate never fails because of the AI.

**Why Gemini (gemini-3.5-flash):** fast and cheap for short summaries, supports schema-based
JSON output, and it's on the same cloud as the deployment design. I measured before choosing:
an older model is closed to new users, and the newest Flash model took about 60 seconds per
call, so I picked the version that answered in a few seconds.

**Honest limitation.** No prompt-based defence is perfect. Grounding catches *invented*
skills, but not false claims copied from the resume itself: the blunt injection literally
contains "10 years at Google", so a substring check passes it. That case is handled by the
system instruction, the warning flag, and the fact that the output can't *do* anything. The
design limits what a successful injection can achieve instead of trusting the model to refuse.

## Tests

47 backend tests run without a database or API key (in-memory MongoDB, fake Gemini). They
target behaviour that could plausibly break: pipeline-order sorting, filters, archived
visibility, append-only notes, 404s, "edit contact details doesn't call the AI", and for the AI
module: empty/junk/oversized input, wrapper-tag escape, invented skills, malformed JSON,
timeouts and setup errors. Two opt-in live tests run the injection resumes against real Gemini
and check the injected claims don't appear and the warning flag is set.

## Tradeoffs

- Summaries are generated **synchronously** when saving (a few seconds). Simpler than a
  background job plus polling; the cost is a slower save.
- Sorting by stage happens **in Python**, fine at this scale; at thousands of candidates I'd
  store a stage rank and sort and paginate in MongoDB.
- Skill grounding is a **literal substring match**, so "Node.js" vs "NodeJS" would be dropped.
  I preferred dropping a real skill over showing an invented one.
- The Gemini free tier allows ~5 requests per minute and ~20 per day; bulk loads are paced,
  and when a limit is hit the app degrades to "failed + Regenerate" rather than erroring.

## What I'd build next

1. **Authentication and roles** (Identity-Aware Proxy first, then per-user audit of notes and stage changes).
2. **Background summary generation** with a queue and automatic retry on rate limits.
3. **PDF/DOCX resume upload**, with text extraction kept on the server.
4. **Job-description matching:** compare each candidate against the role's requirements, with the same grounding rules.
5. **Talent pool and retention:** keep archived candidates who consent for future roles, and auto-delete the rest after a retention period.
6. Pagination and server-side search once the list grows.
