// Every call to the backend lives here, so pages never build URLs or parse errors themselves.

const BASE_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(status, message, fieldErrors = {}) {
    super(message);
    this.status = status;
    this.fieldErrors = fieldErrors; // { fieldName: "message" } from FastAPI 422 responses
  }
}

function parseError(status, body) {
  const detail = body?.detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{ loc: ["body", "email"], msg: "..." }, ...]
    const fieldErrors = {};
    for (const err of detail) {
      const field = err.loc?.[err.loc.length - 1];
      if (field) fieldErrors[field] = err.msg.replace(/^Value error, /, "");
    }
    return new ApiError(status, "Please fix the highlighted fields.", fieldErrors);
  }
  if (typeof detail === "string") return new ApiError(status, detail);
  return new ApiError(status, `Request failed (${status})`);
}

async function request(path, { method = "GET", body } = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}/api${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Is the backend running?");
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) throw parseError(response.status, data);
  return data;
}

export const api = {
  listCandidates: (params) => request(`/candidates?${new URLSearchParams(params)}`),
  listRoles: () => request("/roles"),
  getCandidate: (id) => request(`/candidates/${id}`),
  createCandidate: (data) => request("/candidates", { method: "POST", body: data }),
  updateCandidate: (id, data) => request(`/candidates/${id}`, { method: "PATCH", body: data }),
  changeStage: (id, stage) => request(`/candidates/${id}/stage`, { method: "PATCH", body: { stage } }),
  addNote: (id, text) => request(`/candidates/${id}/notes`, { method: "POST", body: { text } }),
  archive: (id) => request(`/candidates/${id}/archive`, { method: "POST" }),
  unarchive: (id) => request(`/candidates/${id}/unarchive`, { method: "POST" }),
  deleteCandidate: (id) => request(`/candidates/${id}`, { method: "DELETE" }),
  regenerateSummary: (id) => request(`/candidates/${id}/summary`, { method: "POST" }),
};
