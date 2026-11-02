// Segmented control (from the ATS kit). A radio group underneath, so it works with the
// keyboard (arrow keys) and screen readers. The highlight slides to the selected option.
export default function SegmentedControl({ label, name, options, value, onChange }) {
  const index = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  );
  return (
    <fieldset className="segmented-field">
      <legend>{label}</legend>
      <div className="segmented" style={{ "--count": options.length, "--index": index }}>
        <span className="segmented-indicator" aria-hidden="true" />
        {options.map((option) => (
          <label key={option.value} className={option.value === value ? "is-selected" : undefined}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={option.value === value}
              onChange={() => onChange(option.value)}
              className="visually-hidden"
            />
            {option.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
