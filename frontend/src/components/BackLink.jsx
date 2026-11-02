import { Link } from "react-router-dom";

// Visible "back" control at the top of detail and form pages.
export default function BackLink({ to, children }) {
  return (
    <Link to={to} className="back-link">
      <span className="back-arrow" aria-hidden="true" />
      {children}
    </Link>
  );
}
