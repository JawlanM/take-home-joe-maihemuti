import { Link, Route, Routes } from "react-router-dom";

import CandidateDetail from "./pages/CandidateDetail.jsx";
import CandidateForm from "./pages/CandidateForm.jsx";
import CandidateList from "./pages/CandidateList.jsx";

export default function App() {
  return (
    <>
      <header className="site-header">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true" />
          Candidate Tracker
        </Link>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<CandidateList />} />
          <Route path="/candidates/new" element={<CandidateForm />} />
          <Route path="/candidates/:id" element={<CandidateDetail />} />
          <Route path="/candidates/:id/edit" element={<CandidateForm />} />
          <Route
            path="*"
            element={
              <p>
                Page not found. <Link to="/">Back to candidates</Link>
              </p>
            }
          />
        </Routes>
      </main>
    </>
  );
}
