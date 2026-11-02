import { useEffect, useId, useRef, useState } from "react";

// Custom dropdown so the open list matches the app's design (native <select> lists are
// drawn by the OS). Follows the ARIA "select-only combobox" pattern:
//   - button with role="combobox" + aria-expanded, list with role="listbox"
//   - Up/Down/Home/End move, Enter/Space choose, Escape/Tab close, typing a letter jumps
//   - clicking outside closes it
// options: [{ value, label }]
export default function Select({ label, value, options, onChange, disabled = false, hideLabel = false }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef(null);
  const buttonRef = useRef(null);

  const selectedIndex = Math.max(
    0,
    options.findIndex((option) => option.value === value),
  );
  const selected = options[selectedIndex];

  useEffect(() => {
    if (!open) return undefined;
    function handlePointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [open]);

  function openList() {
    setActiveIndex(selectedIndex);
    setOpen(true);
  }

  function choose(index) {
    setOpen(false);
    buttonRef.current?.focus();
    if (options[index].value !== value) onChange(options[index].value);
  }

  function handleKeyDown(event) {
    const last = options.length - 1;
    const keys = {
      ArrowDown: () => (open ? setActiveIndex((i) => Math.min(i + 1, last)) : openList()),
      ArrowUp: () => (open ? setActiveIndex((i) => Math.max(i - 1, 0)) : openList()),
      Home: () => open && setActiveIndex(0),
      End: () => open && setActiveIndex(last),
      Enter: () => (open ? choose(activeIndex) : openList()),
      " ": () => (open ? choose(activeIndex) : openList()),
      Escape: () => setOpen(false),
    };
    if (keys[event.key]) {
      event.preventDefault();
      keys[event.key]();
      return;
    }
    if (event.key === "Tab") {
      setOpen(false);
      return;
    }
    // Type-ahead: jump to the first option starting with the typed letter.
    if (event.key.length === 1) {
      const match = options.findIndex((o) => o.label.toLowerCase().startsWith(event.key.toLowerCase()));
      if (match < 0) return;
      if (open) setActiveIndex(match);
      else choose(match);
    }
  }

  const listId = `${id}-list`;
  const labelId = `${id}-label`;
  return (
    <div className={`dropdown ${open ? "is-open" : ""}`} ref={rootRef}>
      <span id={labelId} className={hideLabel ? "visually-hidden" : "dropdown-label"}>
        {label}
      </span>
      <button
        ref={buttonRef}
        type="button"
        role="combobox"
        className="dropdown-button"
        aria-labelledby={labelId}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={open ? `${id}-opt-${activeIndex}` : undefined}
        disabled={disabled}
        onClick={() => (open ? setOpen(false) : openList())}
        onKeyDown={handleKeyDown}
      >
        <span className="dropdown-value">{selected?.label}</span>
        <span className="dropdown-chevron" aria-hidden="true" />
      </button>
      {open && (
        <ul className="dropdown-list" role="listbox" id={listId} aria-labelledby={labelId}>
          {options.map((option, index) => (
            <li
              key={option.value}
              id={`${id}-opt-${index}`}
              role="option"
              aria-selected={index === selectedIndex}
              className={index === activeIndex ? "is-active" : undefined}
              onPointerEnter={() => setActiveIndex(index)}
              onClick={() => choose(index)}
            >
              {option.label}
              {index === selectedIndex && <span className="dropdown-check" aria-hidden="true" />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
