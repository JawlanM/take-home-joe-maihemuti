# Write-up

## Scope

Every required feature works end to end: add, list with stage/role filters, sort by date or
pipeline stage, detail view, any-to-any stage moves, append-only notes, archive and delete, and
an AI summary per candidate. I put the remaining time into what the brief weights most: the AI
module, how it handles bad input, and tests, rather than extra features. Deployment is a design
([DEPLOYMENT.md](DEPLOYMENT.md)); full detail is in [DESIGN.md](DESIGN.md).

## Design choices

- **FastAPI + MongoDB.** Notes are append-only and always read with their candidate, so they're
  embedded in the candidate document. Append-only is enforced by design: notes are only ever
  `$push`ed and no endpoint edits or deletes one.
- **Layered backend** (`routes -> service -> repository`). Only the repository touches MongoDB;
  the service receives the summariser as a function, so tests swap in a fake.
- **Archive is a soft delete** (hidden by default, reversible, with Undo); **delete is permanent**
  and confirmed.
- **Sort by stage uses pipeline order**, not alphabetical (which would put Interview first).
- **Edit is included** so a new resume doesn't mean delete-and-re-add (losing notes). The summary
  regenerates only when resume or cover-letter text changes.
- **`.txt` upload is read in the browser** into the text box: the user sees what's saved, and the
  backend only ever handles text.

## The AI feature

Everything is in `backend/app/ai/` behind one function, `summarise(resume, cover_letter)`:

1. **Clean:** normalise Unicode, strip control characters, cap at 20,000 characters (flagged as
   truncated), and remove `<resume>` tags so the text can't close its own wrapper.
2. **Pre-check:** almost no readable text means no model call.
3. **Prompt:** rules go in Gemini's system instruction; the applicant's text goes separately,
   wrapped and described as untrusted data that is never an instruction. Only resume and cover
   letter are sent; name, email and phone never leave the app.
4. **Structured output:** JSON matching a schema (summary, skills, highlights, flags), low
   temperature, token cap, 30-second timeout.
5. **Validate and ground:** malformed output becomes "failed"; skills not found in the resume are
   dropped.

The output is **display-only**: it can't change a stage or trigger anything, it's rendered as plain
text (a `<script>` in a resume is shown, never run), it's labelled AI-generated, and a warning
appears when the model flags injected instructions. Any failure (network, timeout, rate limit, bad
output) saves the candidate anyway with a Regenerate button.

**Why Gemini (gemini-3.5-flash):** fast and cheap for short summaries, schema-based JSON output, and
the same cloud as the deployment design. I measured before choosing: one model was closed to new
users, and the newest took about 60 seconds per call.

**Limitation.** Grounding catches *invented* skills, not false claims copied from the resume: the
injection seed literally contains "10 years at Google". That case relies on the system
instruction, the warning flag, and output that can't act. No prompt defence is perfect, so the
design limits what a successful injection can do.

## Tests

47 backend tests need no database or API key (in-memory MongoDB, fake Gemini). They cover what
could plausibly break: pipeline-order sorting, filters, archive views, append-only notes, 404s,
"editing a phone number doesn't call the AI", and empty, junk, oversized and injected input,
wrapper escape, invented skills, malformed JSON and timeouts. Two opt-in live tests run the
injection resumes against real Gemini.

## Tradeoffs

- Summaries are generated **synchronously** on save: simpler than a job queue, slower to save.
- Stage sorting runs **in Python**; at scale I'd store a stage rank and sort/paginate in MongoDB.
- Grounding is a **literal match**, so "NodeJS" vs "Node.js" gets dropped. I'd rather drop a real
  skill than show an invented one.
- The free Gemini tier allows ~5 requests a minute and ~20 a day; the app degrades to
  "failed + Regenerate" instead of erroring.

## What I'd build next

1. **Authentication and roles**, starting with Identity-Aware Proxy.
2. **PDF/DOCX upload with OCR fallback.** Scanned or image-only PDFs have no text layer and extract
   as nothing (I've hit this before), so detect that, fall back to OCR (Document AI or
   Tesseract), and tell the recruiter if it still can't be read.
3. **Background summaries** with retry on rate limits.
4. **Job-description matching**, with the same grounding rules.
5. **Talent pool and retention, with consent:** opted-in candidates are flagged for new matching
   roles, other archived candidates are auto-deleted after a retention period, and deletes get a
   short undo window.
6. **Pipeline board:** kanban with drag between stages, stage counts, bulk actions, days in stage.
7. **Candidate updates:** notify applicants when their application moves (received, under review,
   next round, outcome), with AI-drafted next-round or rejection messages from the stage, role and
   notes. Drafts are always reviewed and sent by a recruiter, never sent automatically, and never
   include the AI summary or private notes.
