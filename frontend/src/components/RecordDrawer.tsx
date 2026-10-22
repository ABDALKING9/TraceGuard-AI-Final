import { useEffect, useState } from "react";
import { Activity, ShieldCheck, X } from "lucide-react";
import type { CaseItem, RecordItem } from "../api/types";
import { RiskBadge } from "./ui";

export function RecordDrawer({
  record,
  cases,
  onClose,
  onRunAnalysis,
  onUpdateReview,
  onAttachToCase,
  onAddNote,
}: {
  record: RecordItem | null;
  cases: CaseItem[];
  onClose: () => void;
  onRunAnalysis: (recordId: number) => Promise<void>;
  onUpdateReview: (recordId: number, reviewStatus: string) => Promise<void>;
  onAttachToCase: (caseId: number, recordId: number) => Promise<void>;
  onAddNote: (caseId: number, recordId: number, noteText: string) => Promise<void>;
}) {
  const [caseId, setCaseId] = useState("");
  const [noteText, setNoteText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setCaseId("");
    setNoteText("");
  }, [record?.id]);

  if (!record) return null;
  const current = record;

  async function runAnalysis() {
    setBusy(true);
    try {
      await onRunAnalysis(current.id);
    } finally {
      setBusy(false);
    }
  }

  async function attach() {
    if (!caseId) return;
    setBusy(true);
    try {
      await onAttachToCase(Number(caseId), current.id);
    } finally {
      setBusy(false);
    }
  }

  async function saveNote() {
    if (!caseId || !noteText.trim()) return;
    setBusy(true);
    try {
      await onAddNote(Number(caseId), current.id, noteText.trim());
      setNoteText("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="detail-drawer" onClick={(event) => event.stopPropagation()} data-testid="record-drawer">
        <div className="drawer-heading">
          <div>
            <span className="eyebrow">RECORD #{record.id}</span>
            <h2>Record details</h2>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close record details">
            <X size={17} />
          </button>
        </div>

        <div className="record-meta">
          <span className="platform-tag">{record.account.platform}</span>
          <span>@{record.account.username}</span>
          <span className="synthetic-tag">Synthetic</span>
          {record.created_at ? <span>{new Date(record.created_at).toLocaleString()}</span> : null}
        </div>

        <p className="record-full-text">{record.content_text}</p>

        <div className="score-box">
          <div>
            <span>Review priority score</span>
            <strong>{record.analysis?.score ?? "Not analyzed"}</strong>
          </div>
          {record.analysis ? <RiskBadge category={record.analysis.risk_category} /> : null}
        </div>

        {record.analysis ? (
          <>
            <h3>Matched indicators</h3>
            {record.analysis.matched_indicators.length ? (
              record.analysis.matched_indicators.map((indicator) => (
                <div className="indicator" key={indicator.id}>
                  <strong>{indicator.label}</strong>
                  <span>+{indicator.weight} points</span>
                </div>
              ))
            ) : (
              <p className="muted">No configured indicators matched.</p>
            )}
            <h3>Explanation</h3>
            <ul className="explanation-list">
              {record.analysis.explanations.map((explanation, index) => (
                <li key={index}>{explanation}</li>
              ))}
            </ul>
            <p className="muted">Engine version {record.analysis.engine_version}</p>
          </>
        ) : (
          <button className="primary-button full-button" onClick={() => void runAnalysis()} disabled={busy}>
            <Activity size={16} /> Run analysis
          </button>
        )}

        <h3>Analyst actions</h3>
        <label className="field-label" htmlFor="review-disposition">
          Review disposition
        </label>
        <select
          id="review-disposition"
          className="full-select"
          value={record.review_status}
          onChange={(event) => void onUpdateReview(record.id, event.target.value)}
        >
          <option>Pending Review</option>
          <option>Reviewed — No Action</option>
          <option>Further Review Required</option>
        </select>

        <div className="drawer-actions">
          <select
            className="full-select"
            value={caseId}
            onChange={(event) => setCaseId(event.target.value)}
            aria-label="Select a case"
          >
            <option value="">Select a case...</option>
            {cases.map((item) => (
              <option key={item.id} value={item.id}>
                CASE-{String(item.id).padStart(4, "0")} · {item.title}
              </option>
            ))}
          </select>
          <button className="secondary-button" onClick={() => void attach()} disabled={busy || !caseId}>
            <ShieldCheck size={15} /> Add to case
          </button>
        </div>

        <label className="field-label" htmlFor="drawer-note">
          Analyst note
        </label>
        <textarea
          id="drawer-note"
          className="login-input"
          rows={3}
          value={noteText}
          onChange={(event) => setNoteText(event.target.value)}
          placeholder="Note what you observed in this synthetic record."
        />
        <div className="drawer-actions">
          <button className="secondary-button" onClick={() => void saveNote()} disabled={busy || !caseId || !noteText.trim()}>
            Save note
          </button>
        </div>

        <p className="drawer-disclaimer">
          This is synthetic demo content. Scores are heuristic review priorities and never establish
          criminal activity.
        </p>
      </aside>
    </div>
  );
}
