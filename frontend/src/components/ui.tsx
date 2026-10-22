import type { ReactNode } from "react";
import { Database } from "lucide-react";
import type { RecordItem } from "../api/types";

export function Metric({
  icon,
  label,
  value,
  hint,
}: {
  icon: ReactNode;
  label: string;
  value: string | number;
  hint: string;
}) {
  return (
    <div className="metric-card">
      <div className="metric-top">
        <span>{label}</span>
        <div className="metric-icon">{icon}</div>
      </div>
      <strong>{value}</strong>
      <small>{hint}</small>
    </div>
  );
}

export function RiskBadge({ category }: { category: string }) {
  const slug = category.toLowerCase().replace(/\s+/g, "-");
  return <span className={`risk-badge ${slug}`}>{category}</span>;
}

export function Empty({ text, action }: { text: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <Database size={22} />
      <p>{text}</p>
      {action}
    </div>
  );
}

export function RecordTable({
  records,
  onSelect,
  emptyText = "No records match this view. Load demo data or adjust filters.",
}: {
  records: RecordItem[];
  onSelect: (record: RecordItem) => void;
  emptyText?: string;
}) {
  if (!records.length) return <Empty text={emptyText} />;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Record</th>
            <th>Simulated platform</th>
            <th>Content preview</th>
            <th>Score</th>
            <th>Priority</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.id} onClick={() => onSelect(record)} data-testid="record-row">
              <td>
                <strong>#{record.id}</strong>
                <small>{record.record_type}</small>
              </td>
              <td>
                <span className="platform-tag">{record.account.platform}</span>
              </td>
              <td className="preview-cell">{record.content_text}</td>
              <td className="score-cell">{record.analysis?.score ?? "—"}</td>
              <td>
                {record.analysis ? (
                  <RiskBadge category={record.analysis.risk_category} />
                ) : (
                  <span className="risk-badge low">Not analyzed</span>
                )}
              </td>
              <td>
                <span className="status-pill">{record.review_status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PanelHeading({
  title,
  subtitle,
  icon,
  action,
}: {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="panel-heading">
      <div>
        <h2>{title}</h2>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {action ?? icon}
    </div>
  );
}
