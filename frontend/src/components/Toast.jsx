import { useCallback, useRef, useState } from "react";

import { ToastContext } from "./toastContext.js";

// Small confirmation messages after an action ("Note added", "Archived · Undo").
// Lives above the router so a message survives navigation (e.g. after delete).

const DURATION_MS = 4500;
const ACTION_DURATION_MS = 8000; // longer when there's an Undo to reach

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message, options = {}) => {
      const id = nextId.current++;
      setToasts((current) => [...current.slice(-2), { id, message, ...options }]);
      setTimeout(() => dismiss(id), options.onAction ? ACTION_DURATION_MS : DURATION_MS);
    },
    [dismiss],
  );

  return (
    <ToastContext.Provider value={showToast}>
      {children}
      <div className="toast-region" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast ${toast.tone === "error" ? "toast-error" : ""}`}>
            <span>{toast.message}</span>
            {toast.onAction && (
              <button
                type="button"
                className="toast-action"
                onClick={() => {
                  dismiss(toast.id);
                  toast.onAction();
                }}
              >
                {toast.actionLabel}
              </button>
            )}
            <button type="button" className="toast-close" aria-label="Dismiss" onClick={() => dismiss(toast.id)}>
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
