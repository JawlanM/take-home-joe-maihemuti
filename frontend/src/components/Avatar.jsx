import { getInitials } from "./initials.js";

// Initials avatar (no photos are stored). Decorative: the name is always shown next to it.

export default function Avatar({ name, size = "md" }) {
  return (
    <span className={`avatar avatar-${size}`} aria-hidden="true">
      {getInitials(name)}
    </span>
  );
}
