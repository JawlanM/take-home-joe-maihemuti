import { createContext, useContext } from "react";

export const ToastContext = createContext(() => {});

// showToast("Saved") or showToast("Archived", { actionLabel: "Undo", onAction: fn, tone: "error" })
export function useToast() {
  return useContext(ToastContext);
}
