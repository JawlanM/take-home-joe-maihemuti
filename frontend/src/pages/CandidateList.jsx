import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { api } from "../api.js";
import Avatar from "../components/Avatar.jsx";
import SegmentedControl from "../components/SegmentedControl.jsx";
import Select from "../components/Select.jsx";
import StageBadge from "../components/StageBadge.jsx";
import { STAGES, formatDate } from "../constants.js";

const DEFAULTS = { stage: "", role: "", sort: "created", order: "desc", archived: "active" };

const VIEW_OPTIONS = [
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" },
  { value: "all", label: "All" },
];

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

function EmptyState({ title, message, children }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      <p className="muted">{message}</p>
      {children}
    </div>
  );
}

export default function CandidateList() {
  // Filters live in the URL, so they survive refresh and the back button.
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const filters = { ...DEFAULTS, ...Object.fromEntries(searchParams) };

  const [roles, setRoles] = useState([]);
  // The URL only ever holds non-default filters, so it can be sent to the API as-is.
  const queryKey = searchParams.toString();
  // The last result stays on screen (dimmed) while the next one loads, so changing a
  // filter updates the table in place instead of flashing a loading state.
  const [result, setResult] = useState({ key: null, candidates: null, error: "" });
  const isCurrent = result.key === queryKey;
  const isFirstLoad = result.key === null;
  const isRefreshing = !isCurrent && !isFirstLoad;
  const candidates = result.candidates;
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

  function updateFilters(changes) {
    const next = { ...filters, ...changes };
    const nonDefault = Object.entries(next).filter(([key, val]) => val !== DEFAULTS[key]);
    setSearchParams(Object.fromEntries(nonDefault));
  }

  const hasStageOrRole = filters.stage || filters.role;

  function renderEmpty() {
    if (hasStageOrRole) {
      return (
        <EmptyState
          title="No candidates found"
          message="Try a different stage or role, or clear the filters to see the full pipeline."
        >
          <button type="button" className="button" onClick={() => updateFilters({ stage: "", role: "" })}>
            Clear filters
          </button>
        </EmptyState>
      );
    }
    if (filters.archived === "archived") {
      return (
        <EmptyState
          title="No archived candidates"
          message="Candidates you archive from their profile appear here. They keep all their data and can be restored."
        >
          <button type="button" className="button" onClick={() => updateFilters({ archived: "active" })}>
            Back to active candidates
          </button>
        </EmptyState>
      );
    }
    return (
      <EmptyState title="No candidates yet" message="Add a candidate to start tracking your pipeline.">
        <Link to="/candidates/new" className="button primary">
          Add candidate
        </Link>
      </EmptyState>
    );
  }

  return (
    <>
      <div className="page-heading">
        <h1>Candidates</h1>
        <Link to="/candidates/new" className="button primary">
          Add candidate
        </Link>
      </div>

      <form className="toolbar" onSubmit={(e) => e.preventDefault()} aria-label="Filter and sort">
        <SegmentedControl
          label="Show"
          name="archived"
          options={VIEW_OPTIONS}
          value={filters.archived}
          onChange={(archived) => updateFilters({ archived })}
        />
        <Select
          label="Stage"
          value={filters.stage}
          options={[{ value: "", label: "All stages" }, ...STAGES.map((stage) => ({ value: stage, label: stage }))]}
          onChange={(stage) => updateFilters({ stage })}
        />
        <Select
          label="Role"
          value={filters.role}
          options={[{ value: "", label: "All roles" }, ...roles.map((role) => ({ value: role, label: role }))]}
          onChange={(role) => updateFilters({ role })}
        />
        <Select
          label="Sort by"
          value={filters.sort}
          options={[
            { value: "created", label: "Date added" },
            { value: "stage", label: "Stage" },
          ]}
          onChange={(sort) => updateFilters({ sort })}
        />
        <Select
          label="Order"
          value={filters.order}
          options={
            filters.sort === "stage"
              ? [
                  { value: "asc", label: "Applied first" },
                  { value: "desc", label: "Rejected first" },
                ]
              : [
                  { value: "desc", label: "Newest first" },
                  { value: "asc", label: "Oldest first" },
                ]
          }
          onChange={(order) => updateFilters({ order })}
        />
      </form>

      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}

      {isFirstLoad && !error && <LoadingTable />}

      {candidates && (
        <div className={`results ${isRefreshing ? "is-refreshing" : ""}`} aria-busy={isRefreshing}>
          <p className="result-count muted" aria-live="polite">
            {candidates.length} {candidates.length === 1 ? "candidate" : "candidates"}
          </p>
          {candidates.length === 0 ? (
            renderEmpty()
          ) : (
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
                <tbody className="stagger" key={result.key}>
                  {candidates.map((c, index) => (
                    <tr
                      key={c.id}
                      className={`row-link ${c.archived ? "archived" : ""}`}
                      style={{ "--i": index }}
                      // Whole row opens the candidate. The name stays a real link for
                      // keyboard users and Ctrl/Cmd-click; text selection doesn't navigate.
                      onClick={(e) => {
                        if (e.target.closest("a") || window.getSelection()?.toString()) return;
                        navigate(`/candidates/${c.id}`);
                      }}
                    >
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
        </div>
      )}
    </>
  );
}
