// Shows the AI summary. Everything is rendered as plain text (React escapes it),
// so resume content like <script> can never run. The summary is display-only:
// nothing here changes the candidate.

function Body({ summary }) {
  return (
    <>
      {summary.flags?.suspicious_content && (
        <p className="alert warning" role="alert">
          This resume contains text that appears to give instructions to the AI. It was ignored, but
          review the resume yourself.
        </p>
      )}
      {summary.flags?.insufficient_info && (
        <p className="alert info">There wasn&apos;t enough readable content for a reliable summary.</p>
      )}
      {summary.summary && <p>{summary.summary}</p>}

      {summary.skills?.length > 0 && (
        <>
          <h3>Key skills</h3>
          <ul className="chips">
            {summary.skills.map((skill) => (
              <li key={skill}>{skill}</li>
            ))}
          </ul>
        </>
      )}
      {summary.highlights?.length > 0 && (
        <>
          <h3>Experience highlights</h3>
          <ul>
            {summary.highlights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      )}

      <p className="small muted">
        {summary.dropped_skills > 0 &&
          `${summary.dropped_skills} suggested skill(s) removed because they don't appear in the resume. `}
        {summary.flags?.truncated && "Only the first part of a very long resume was summarised. "}
      </p>
    </>
  );
}

export default function SummaryPanel({ summary, onRegenerate, regenerating }) {
  let content;
  if (!summary) {
    content = <p className="muted">No summary yet.</p>;
  } else if (summary.status === "ok") {
    content = <Body summary={summary} />;
  } else if (summary.status === "insufficient_input") {
    content = <p className="muted">No readable resume or cover letter text to summarise.</p>;
  } else if (summary.status === "disabled") {
    content = <p className="muted">AI summaries are turned off (no Gemini API key configured).</p>;
  } else {
    content = (
      <>
        <p className="alert error" role="alert">
          The summary couldn&apos;t be generated: {summary.error || "unknown error"}.
        </p>
        <button type="button" className="button" onClick={onRegenerate} disabled={regenerating}>
          {regenerating ? "Regenerating…" : "Regenerate summary"}
        </button>
      </>
    );
  }

  return (
    <section className="card" aria-labelledby="summary-heading">
      <h2 id="summary-heading">AI summary</h2>
      <p className="small muted">AI-generated from the resume and cover letter. May be inaccurate.</p>
      {content}
    </section>
  );
}
