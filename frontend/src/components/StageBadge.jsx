// Stage is shown as text plus colour, never colour alone.
export default function StageBadge({ stage }) {
  return <span className={`badge stage-${stage.toLowerCase()}`}>{stage}</span>;
}
