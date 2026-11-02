// Initials avatar (no photos are stored). Decorative: the name is always shown next to it.
export default function Avatar({ name, size = "md" }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
  return (
    <span className={`avatar avatar-${size}`} aria-hidden="true">
      {initials}
    </span>
  );
}
