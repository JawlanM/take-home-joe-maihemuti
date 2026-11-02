import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api.js";
import StageBadge from "../components/StageBadge.jsx";
import SummaryPanel from "../components/SummaryPanel.jsx";
import { STAGES, formatDateTime } from "../constants.js";

function Notes({ notes, onAdd }) {
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    if (!text.trim()) return;
    setSaving(true);
    setError("");
    try {
      await onAdd(text);
      setText("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const newestFirst = [...notes].reverse();
  return (
    <section className="card" aria-labelledby="notes-heading">
      <h2 id="notes-heading">Notes</h2>
      <form onSubmit={handleSubmit} className="note-form">
        <label htmlFor="new-note" className="visually-hidden">
          New note
        </label>
        <textarea
          id="new-note"
          rows={3}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Add a note…"
        />
        {error && <p className="field-error">{error}</p>}
        <button type="submit" className="button primary" disabled={saving || !text.trim()}>
          {saving ? "Adding…" : "Add note"}
        </button>
      </form>
      {newestFirst.length === 0 ? (
        <p className="muted">No notes yet.</p>
      ) : (
        <ol className="notes">
          {newestFirst.map((note) => (
            <li key={note.created_at + note.text}>
              <time dateTime={note.created_at}>{formatDateTime(note.created_at)}</time>
              <p>{note.text}</p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export default function CandidateDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [candidate, setCandidate] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(""); // which action is in progress, if any

  useEffect(() => {
    api
      .getCandidate(id)
      .then(setCandidate)
      .catch((err) => setError(err.message));
  }, [id]);

  // Run an action that returns the updated candidate, tracking busy/error state.
  async function run(action, fn) {
    setBusy(action);
    setError("");
    try {
      const updated = await fn();
      if (updated) setCandidate(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Permanently delete ${candidate.name}? This can't be undone.`)) return;
    setBusy("delete");
    try {
      await api.deleteCandidate(id);
      navigate("/");
    } catch (err) {
      setError(err.message);
      setBusy("");
    }
  }

  if (error && !candidate) {
    return (
      <>
        <p className="alert error" role="alert">
          {error}
        </p>
        <Link to="/">← All candidates</Link>
      </>
    );
  }
  if (!candidate) return <p className="muted">Loading…</p>;

  const c = candidate;
  return (
    <>
      <p className="breadcrumb">
        <Link to="/">← All candidates</Link>
      </p>

      <div className="page-heading">
        <div>
          <h1>
            {c.name} {c.archived && <span className="tag">Archived</span>}
          </h1>
          <p className="muted">{c.role}</p>
        </div>
        <div className="actions">
          <Link to={`/candidates/${id}/edit`} className="button">
            Edit
          </Link>
          {c.archived ? (
            <button type="button" className="button" disabled={Boolean(busy)} onClick={() => run("archive", () => api.unarchive(id))}>
              Unarchive
            </button>
          ) : (
            <button type="button" className="button" disabled={Boolean(busy)} onClick={() => run("archive", () => api.archive(id))}>
              Archive
            </button>
          )}
          <button type="button" className="button danger" disabled={Boolean(busy)} onClick={handleDelete}>
            Delete
          </button>
        </div>
      </div>

      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}

      <div className="detail-grid">
        <div className="stack">
          <section className="card" aria-labelledby="profile-heading">
            <h2 id="profile-heading">Profile</h2>
            <div className="field stage-field">
              <label htmlFor="stage">Stage</label>
              <div className="inline">
                <select
                  id="stage"
                  value={c.stage}
                  disabled={Boolean(busy)}
                  onChange={(e) => run("stage", () => api.changeStage(id, e.target.value))}
                >
                  {STAGES.map((stage) => (
                    <option key={stage}>{stage}</option>
                  ))}
                </select>
                <StageBadge stage={c.stage} />
                {busy === "stage" && <span className="muted small">Saving…</span>}
              </div>
            </div>
            <dl className="details">
              <dt>Email</dt>
              <dd>
                <a href={`mailto:${c.email}`}>{c.email}</a>
              </dd>
              <dt>Phone</dt>
              <dd>{c.phone || <span className="muted">Not provided</span>}</dd>
              <dt>Source</dt>
              <dd>{c.source || <span className="muted">Not provided</span>}</dd>
              <dt>Added</dt>
              <dd>{formatDateTime(c.created_at)}</dd>
              <dt>Last updated</dt>
              <dd>{formatDateTime(c.updated_at)}</dd>
            </dl>
          </section>

          <SummaryPanel
            summary={c.ai_summary}
            regenerating={busy === "summary"}
            onRegenerate={() => run("summary", () => api.regenerateSummary(id))}
          />

          <section className="card" aria-labelledby="documents-heading">
            <h2 id="documents-heading">Resume and cover letter</h2>
            <details>
              <summary>Resume</summary>
              <pre className="document">{c.resume_text || "No resume text."}</pre>
            </details>
            <details>
              <summary>Cover letter</summary>
              <pre className="document">{c.cover_letter_text || "No cover letter."}</pre>
            </details>
          </section>
        </div>

        <Notes notes={c.notes} onAdd={(text) => api.addNote(id, text).then(setCandidate)} />
      </div>
    </>
  );
}
