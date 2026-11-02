import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { api } from "../api.js";
import BackLink from "../components/BackLink.jsx";
import Select from "../components/Select.jsx";
import TextFileField from "../components/TextFileField.jsx";
import { useToast } from "../components/toastContext.js";
import { STAGES } from "../constants.js";

const EMPTY = {
  name: "",
  email: "",
  phone: "",
  role: "",
  source: "",
  stage: "Applied",
  resume_text: "",
  cover_letter_text: "",
};

// Optional fields: an empty box means "not provided" (null), not an empty string.
const OPTIONAL = ["phone", "source"];

function toPayload(values, isEdit) {
  const payload = { ...values };
  for (const field of OPTIONAL) payload[field] = payload[field].trim() || null;
  if (isEdit) delete payload.stage; // stage is changed from the detail page
  return payload;
}

function TextField({ label, name, value, onChange, error, type = "text", required, ...rest }) {
  return (
    <div className="field">
      <label htmlFor={name}>
        {label}
        {!required && <span className="muted"> (optional)</span>}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        value={value}
        required={required}
        onChange={(e) => onChange(name, e.target.value)}
        aria-invalid={Boolean(error)}
        {...rest}
      />
      {error && <p className="field-error">{error}</p>}
    </div>
  );
}

export default function CandidateForm() {
  const { id } = useParams();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const showToast = useToast();

  const [values, setValues] = useState(EMPTY);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});

  useEffect(() => {
    api.listRoles().then(setRoles).catch(() => setRoles([]));
    if (!isEdit) return;
    api
      .getCandidate(id)
      .then((c) => {
        const loaded = Object.fromEntries(Object.keys(EMPTY).map((key) => [key, c[key] ?? ""]));
        setValues(loaded);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id, isEdit]);

  function handleChange(name, value) {
    setValues((prev) => ({ ...prev, [name]: value }));
    setFieldErrors((prev) => ({ ...prev, [name]: undefined }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setFieldErrors({});
    try {
      const payload = toPayload(values, isEdit);
      const saved = isEdit ? await api.updateCandidate(id, payload) : await api.createCandidate(payload);
      showToast(isEdit ? "Changes saved" : `${saved.name} added`);
      navigate(`/candidates/${saved.id}`);
    } catch (err) {
      setError(err.message);
      setFieldErrors(err.fieldErrors ?? {});
      setSaving(false);
    }
  }

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <>
      <BackLink to={isEdit ? `/candidates/${id}` : "/"}>
        {isEdit ? "Back to candidate" : "Back to candidates"}
      </BackLink>
      <h1>{isEdit ? "Edit candidate" : "Add candidate"}</h1>

      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}

      <form className="form" onSubmit={handleSubmit} noValidate>
        <fieldset className="grid-2" disabled={saving}>
          <TextField label="Name" name="name" value={values.name} onChange={handleChange} error={fieldErrors.name} required autoComplete="off" />
          <TextField label="Email" name="email" type="email" value={values.email} onChange={handleChange} error={fieldErrors.email} required autoComplete="off" />
          <TextField label="Phone" name="phone" type="tel" value={values.phone} onChange={handleChange} error={fieldErrors.phone} autoComplete="off" />
          <div>
            <TextField label="Role applied for" name="role" value={values.role} onChange={handleChange} error={fieldErrors.role} required autoComplete="off" />
            {roles.length > 0 && (
              <div className="role-suggestions" aria-label="Existing roles">
                {roles
                  .filter((role) => role !== values.role)
                  .map((role) => (
                    <button key={role} type="button" className="chip-button" onClick={() => handleChange("role", role)}>
                      {role}
                    </button>
                  ))}
              </div>
            )}
          </div>
          <TextField label="Source" name="source" value={values.source} onChange={handleChange} error={fieldErrors.source} placeholder="e.g. LinkedIn, referral" autoComplete="off" />
          {!isEdit && (
            <div className="field">
              <Select
                label="Stage"
                value={values.stage}
                options={STAGES.map((stage) => ({ value: stage, label: stage }))}
                onChange={(stage) => handleChange("stage", stage)}
              />
            </div>
          )}
        </fieldset>

        <fieldset disabled={saving}>
          <TextFileField
            label="Resume"
            name="resume_text"
            value={values.resume_text}
            onChange={handleChange}
            error={fieldErrors.resume_text}
            hint="Used for the AI summary."
          />
          <TextFileField
            label="Cover letter (optional)"
            name="cover_letter_text"
            value={values.cover_letter_text}
            onChange={handleChange}
            error={fieldErrors.cover_letter_text}
          />
        </fieldset>

        <div className="form-actions">
          <button type="submit" className="button primary" disabled={saving}>
            {saving ? "Saving and generating summary…" : isEdit ? "Save changes" : "Add candidate"}
          </button>
          <Link to={isEdit ? `/candidates/${id}` : "/"} className="button">
            Cancel
          </Link>
        </div>
      </form>
    </>
  );
}
