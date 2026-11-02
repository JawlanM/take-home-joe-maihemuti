import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api.js";
import Avatar from "../components/Avatar.jsx";
import StageBadge from "../components/StageBadge.jsx";
import { STAGES, formatDate } from "../constants.js";

const DEFAULTS = { stage: "", role: "", sort: "created", order: "desc", include_archived: "false" };

function LoadingTable() {
  return (
    <div className="table-wrap" aria-busy="true" aria-label="Loading candidates">
      <table>
        <tbody>
          {[0, 1, 2, 3, 4].map((row) => (
            <tr key={row}>
              {["40%", "60%", "30%", "40%", "50%"].map((width, col) => (
                <td key={col}>
                  <span className="skeleton" style={{ width }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function CandidateList() {
  // Filters live in the URL, so they survive refresh and the back button.
  const [searchParams, setSearchParams] = useSearchParams();
  const filters = { ...DEFAULTS, ...Object.fromEntries(searchParams) };

  const [roles, setRoles] = useState([]);
  // The URL only ever holds non-default filters, so it can be sent to the API as-is.
  const queryKey = searchParams.toString();
  // Each result remembers which query it answers; anything else means "still loading".
  const [result, setResult] = useState({ key: null, candidates: null, error: "" });
  const isCurrent = result.key === queryKey;
  const candidates = isCurrent ? result.candidates : null;
  const error = isCurrent ? result.error : "";

  useEffect(() => {
    api.listRoles().then(setRoles).catch(() => setRoles([]));
  }, []);

  useEffect(() => {
    let ignore = false; // drop responses that arrive after the filters changed again
    api
      .listCandidates(queryKey)
      .then((list) => !ignore && setResult({ key: queryKey, candidates: list, error: "" }))
      .catch((err) => !ignore && setResult({ key: queryKey, candidates: null, error: err.message }));
    return () => {
      ignore = true;
    };
  }, [queryKey]);

  function updateFilter(name, value) {
    const next = { ...filters, [name]: value };
    const nonDefault = Object.entries(next).filter(([key, val]) => val !== DEFAULTS[key]);
    setSearchParams(Object.fromEntries(nonDefault));
  }

  const isFiltered = filters.stage || filters.role;

  return (
    <>
      <div className="page-heading">
        <h1>Candidates</h1>
        <Link to="/candidates/new" className="button primary">
          Add candidate
        </Link>
      </div>

      <form className="toolbar" onSubmit={(e) => e.preventDefault()} aria-label="Filter and sort">
        <label>
          Stage
          <select value={filters.stage} onChange={(e) => updateFilter("stage", e.target.value)}>
            <option value="">All stages</option>
            {STAGES.map((stage) => (
              <option key={stage}>{stage}</option>
            ))}
          </select>
        </label>
        <label>
          Role
          <select value={filters.role} onChange={(e) => updateFilter("role", e.target.value)}>
            <option value="">All roles</option>
            {roles.map((role) => (
              <option key={role}>{role}</option>
            ))}
          </select>
        </label>
        <label>
          Sort by
          <select value={filters.sort} onChange={(e) => updateFilter("sort", e.target.value)}>
            <option value="created">Date added</option>
            <option value="stage">Stage</option>
          </select>
        </label>
        <label>
          Order
          <select value={filters.order} onChange={(e) => updateFilter("order", e.target.value)}>
            <option value="desc">{filters.sort === "stage" ? "Rejected first" : "Newest first"}</option>
            <option value="asc">{filters.sort === "stage" ? "Applied first" : "Oldest first"}</option>
          </select>
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={filters.include_archived === "true"}
            onChange={(e) => updateFilter("include_archived", String(e.target.checked))}
          />
          Show archived
        </label>
      </form>

      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}

      {!error && candidates === null && <LoadingTable />}

      {candidates?.length === 0 &&
        (isFiltered ? (
          <div className="empty">
            <p className="empty-title">No candidates found</p>
            <p className="muted">Try a different stage or role, or clear the filters to see the full pipeline.</p>
            <button type="button" className="button" onClick={() => setSearchParams({})}>
              Clear filters
            </button>
          </div>
        ) : (
          <div className="empty">
            <p className="empty-title">No candidates yet</p>
            <p className="muted">Add a candidate to start tracking your pipeline.</p>
            <Link to="/candidates/new" className="button primary">
              Add candidate
            </Link>
          </div>
        ))}

      {candidates?.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Role</th>
                <th scope="col">Stage</th>
                <th scope="col">Source</th>
                <th scope="col">Date added</th>
              </tr>
            </thead>
            <tbody className="stagger">
              {candidates.map((c, index) => (
                <tr key={c.id} className={c.archived ? "archived" : undefined} style={{ "--i": index }}>
                  <td>
                    <div className="name-cell">
                      <Avatar name={c.name} />
                      <span>
                        <Link to={`/candidates/${c.id}`}>{c.name}</Link>
                        {c.archived && <span className="tag">Archived</span>}
                      </span>
                    </div>
                  </td>
                  <td>{c.role}</td>
                  <td>
                    <StageBadge stage={c.stage} />
                  </td>
                  <td>{c.source || <span className="muted">None</span>}</td>
                  <td>{formatDate(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
