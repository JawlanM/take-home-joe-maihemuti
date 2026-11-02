// Must match the backend Stage enum, in pipeline order.
export const STAGES = ["Applied", "Screening", "Interview", "Offer", "Rejected"];

const dateTimeFormat = new Intl.DateTimeFormat("en-AU", { dateStyle: "medium", timeStyle: "short" });
const dateFormat = new Intl.DateTimeFormat("en-AU", { dateStyle: "medium" });

export const formatDateTime = (iso) => (iso ? dateTimeFormat.format(new Date(iso)) : "");
export const formatDate = (iso) => (iso ? dateFormat.format(new Date(iso)) : "");
