# Write-up

## Scope

Every required feature works end to end, plus an AI summary per candidate. I spent the remaining
time on what the brief weights most (the AI module, bad input, tests) rather than extra features.
Deployment is a design ([DEPLOYMENT.md](DEPLOYMENT.md)); detail is in [DESIGN.md](DESIGN.md).

## Design choices

- **FastAPI + MongoDB.** Notes are append-only and always read with their candidate, so they're
  embedded in it. Notes are only ever `$push`ed; no endpoint edits or deletes one.
- **Layered backend** (`routes -> service -> repository`). Only the repository touches MongoDB; the
  service receives the summariser as a function, so tests swap in a fake.
- **Archive is a soft delete** (reversible, with Undo); **delete is permanent** and confirmed.
- **Sort by stage uses pipeline order**, not alphabetical.
- **Edit is included** so a new resume doesn't mean delete-and-re-add; the summary regenerates only
  when resume or cover-letter text changes.
- **`.txt` upload is read in the browser**, so the backend only ever handles text.

## The AI feature

All in `backend/app/ai/`, behind one function `summarise(resume, cover_letter)`:

1. **Clean:** strip control characters, cap at 20,000 characters (flagged), and remove `<resume>`
   tags so the text can't close its own wrapper.
2. **Pre-check:** no readable text means no model call.
3. **Prompt:** rules in Gemini's system instruction; applicant text sent separately, wrapped and
   described as untrusted data. The separate name/email/phone fields aren't sent, but resumes
   usually contain contact details, so the prompt forbids repeating them.
4. **Structured output:** a JSON schema (summary, skills, highlights, flags), low temperature,
   token cap, 30-second timeout.
5. **Validate and ground:** malformed output becomes "failed"; skills not in the resume as a whole
   term are dropped ("Java" isn't accepted from "JavaScript").

Output is **display-only**: it can't change a stage, it's rendered as plain text (a `<script>` is
shown, never run), it's labelled AI-generated, and flagged injections show a warning. Any failure
still saves the candidate, with a Regenerate button.

**Why gemini-3.5-flash:** fast and cheap, schema-based JSON, same cloud as the deployment design. I
measured first: one model was closed to new users; the newest took ~60 seconds per call.

**Limitations.** Grounding checks only skills, and only invented ones. Highlights and the summary
aren't verified, and false claims copied from the resume (the injection seed says "10 years at
Google") pass. Those rely on the system instruction, the warning flag, and output that can't act:
the design limits what an injection can do rather than trusting the model. Both injection resumes
and the normal seed resumes were run against real Gemini; the opt-in live tests check summary,
skills and highlights.

## Tests

53 tests, no database or API key needed (in-memory MongoDB, fake Gemini): sorting, filters,
archive views, append-only notes, 404s, "editing a phone doesn't call the AI", and empty, junk,
oversized and injected input, wrapper escape, invented or partial-word skills, bad JSON, timeouts.

## Tradeoffs

- **Synchronous** summaries on save: simpler than a queue, slower to save.
- Stage sorting **in Python**; at scale, a stored stage rank with sorting and paging in MongoDB.
- **Literal** grounding drops "NodeJS" vs "Node.js": better than showing an invented skill.
- Gemini's free tier (~5 a minute, ~20 a day) degrades to "failed + Regenerate", not errors.

## What I'd build next

1. **Authentication**, and Gemini via **Vertex AI** for production data handling.
2. **PDF/DOCX upload with OCR** for scanned PDFs, which extract as nothing.
3. **Background summaries** with retry, and job-description matching.
4. **Consent-based talent pool and retention**; recruiter-reviewed, AI-drafted candidate updates.
