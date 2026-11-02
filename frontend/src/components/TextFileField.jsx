import { useId, useState } from "react";

const MAX_FILE_BYTES = 200 * 1024;

// A textarea that can also be filled from a .txt file. The file is read in the
// browser and put into the box, so the user sees exactly what will be saved
// and the backend only ever receives text.
export default function TextFileField({ label, name, value, onChange, error, hint }) {
  const id = useId();
  const [fileError, setFileError] = useState("");

  function handleFile(event) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow re-selecting the same file
    setFileError("");
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".txt")) {
      setFileError("Only .txt files are supported.");
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      setFileError("File is larger than 200 KB.");
      return;
    }
    file
      .text()
      .then((text) => onChange(name, text))
      .catch(() => setFileError("Couldn't read that file."));
  }

  const message = fileError || error;
  return (
    <div className="field">
      <div className="field-label-row">
        <label htmlFor={id}>{label}</label>
        <label className="button small">
          Load .txt file
          <input type="file" accept=".txt,text/plain" onChange={handleFile} className="visually-hidden" />
        </label>
      </div>
      {hint && <p className="hint">{hint}</p>}
      <textarea
        id={id}
        name={name}
        rows={8}
        value={value}
        onChange={(e) => onChange(name, e.target.value)}
        aria-invalid={Boolean(message)}
      />
      {message && <p className="field-error">{message}</p>}
    </div>
  );
}
