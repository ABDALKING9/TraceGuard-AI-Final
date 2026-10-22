import { useState } from "react";
import { FileText, Plus, ShieldCheck } from "lucide-react";
import type { CaseDetail, CaseItem } from "../api/types";
import { Empty, PanelHeading, RiskBadge } from "../components/ui";

export function Investigations({
  cases,
  onCreateCase,
  onOpenCase,
  onAddNote,
  onUpdateDisposition,
  onSelectRecord,
}: {
  cases: CaseItem[];
  onCreateCase: (title: string, description: string) => Promise<void>;
  onOpenCase: (caseId: number) => Promise<CaseDetail | null>;
  onAddNote: (caseId: number, noteText: string, disposition: string) => Promise<void>;
  onUpdateDisposition: (
    caseId: number,
    noteId: number,
    disposition: string,
  ) => Promise<void>;
  onSelectRecord: (recordId: number) => void;
}) {
  const [openCaseId, setOpenCaseId] = useState<number | null>(null);
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [noteText, setNoteText] = useState("");
  const [disposition, setDisposition] = useState("Pending Review");
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function createCase(event: { preventDefault: () => void }) {
    event.preventDefault();
    if (!newTitle.trim()) return;
    setBusy(true);
    setError("");
    try {
      await onCreateCase(newTitle.trim(), newDescription.trim());
      setNewTitle("");
      setNewDescription("");
      setCreating(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function openCase(caseId: number) {
    setBusy(true);
    setError("");
    try {
      const result = await onOpenCase(caseId);
      setDetail(result);
      setOpenCaseId(caseId);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function changeDisposition(noteId: number, nextDisposition: string) {
    if (!detail) return;
    setBusy(true);
    setError("");
    try {
      await onUpdateDisposition(detail.id, noteId, nextDisposition);
      setDetail(await onOpenCase(detail.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function submitNote(event: { preventDefault: () => void }) {
    event.preventDefault();
    if (!detail || !noteText.trim()) return;
    setBusy(true);
    setError("");
    try {
      await onAddNote(detail.id, noteText.trim(), disposition);
      setNoteText("");
      setDetail(await onOpenCase(detail.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">CASE MANAGEMENT</div>
          <h1>Investigations</h1>
          <p>Organize reviewed records into documented synthetic cases.</p>
        </div>
        <button className="primary-button" onClick={() => setCreating((value) => !value)} disabled={busy}>
          <Plus size={16} /> New case
        </button>
      </div>

      {creating ? (
        <section className="panel">
          <form className="case-form" onSubmit={createCase}>
            <div>
              <label className="field-label" htmlFor="case-title">
                Case title
              </label>
              <input
                id="case-title"
                className="login-input"
                value={newTitle}
                onChange={(event) => setNewTitle(event.target.value)}
                placeholder="Synthetic review — short description"
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="case-description">
                Description
              </label>
              <input
                id="case-description"
                className="login-input"
                value={newDescription}
                onChange={(event) => setNewDescription(event.target.value)}
                placeholder="Created during the synthetic offline demonstration."
              />
            </div>
            <div className="note-form-actions">
              <button className="secondary-button" type="button" onClick={() => setCreating(false)}>
                Cancel
              </button>
              <button className="primary-button" type="submit" disabled={busy || !newTitle.trim()}>
                Create case
              </button>
            </div>
          </form>
        </section>
      ) : null}

      {error ? (
        <div className="alert error" role="alert">
          <p>{error}</p>
        </div>
      ) : null}

      <div className="two-col two-col-wide">
        <section className="panel">
          <PanelHeading title="Investigation cases" subtitle="Stored locally in SQLite" icon={<ShieldCheck size={19} />} />
          <div className="case-list">
            {cases.map((item) => (
              <div
                className={`case-row ${openCaseId === item.id ? "selected" : ""}`}
                key={item.id}
              >
                <div className="case-symbol">
                  <ShieldCheck size={20} />
                </div>
                <div className="case-info">
                  <strong>{item.title}</strong>
                  <span>
                    CASE-{String(item.id).padStart(4, "0")} · {item.record_count} linked records
                  </span>
                  <p>{item.description}</p>
                </div>
                <span className={`status-pill ${item.status.toLowerCase().replace(" ", "-")}`}>{item.status}</span>
                <button className="secondary-button" onClick={() => void openCase(item.id)} disabled={busy}>
                  View
                </button>
              </div>
            ))}
            {!cases.length && <Empty text="No cases yet. Load demo data or create a case." />}
          </div>
        </section>

        <section className="panel">
          <PanelHeading
            title={detail ? `CASE-${String(detail.id).padStart(4, "0")}` : "Case detail"}
            subtitle={detail ? detail.title : "Select a case to inspect its records and notes"}
            icon={<FileText size={19} />}
          />

          {!detail ? (
            <Empty text="No case selected." />
          ) : (
            <div className="case-detail">
              <div className="case-detail-meta">
                <span className={`status-pill ${detail.status.toLowerCase().replace(" ", "-")}`}>{detail.status}</span>
                <span className="muted">{detail.records.length} linked records</span>
                <span className="muted">{detail.notes.length} notes</span>
              </div>
              <p className="body-copy muted">{detail.description}</p>

              <h3>Linked records</h3>
              <div className="mini-list">
                {detail.records.map((record) => (
                  <button
                    key={record.id}
                    className="mini-row"
                    onClick={() => onSelectRecord(record.id)}
                    type="button"
                  >
                    <strong>#{record.id}</strong>
                    <span className="platform-tag">{record.account.platform}</span>
                    <span className="mini-preview">{record.content_text}</span>
                    {record.analysis ? <RiskBadge category={record.analysis.risk_category} /> : null}
                  </button>
                ))}
                {!detail.records.length && <p className="muted">No records are attached to this case yet.</p>}
              </div>

              <h3>Analyst notes</h3>
              <div className="mini-list">
                {detail.notes.map((note) => (
                  <div className="mini-row note-row" key={note.id}>
                    <div>
                      <p>{note.note_text}</p>
                      <small className="muted">
                        {note.record_id ? `Record #${note.record_id} · ` : ""}
                        {new Date(note.created_at).toLocaleString()}
                      </small>
                    </div>
                    <select
                      className="full-select compact-select"
                      value={note.disposition}
                      onChange={(event) => void changeDisposition(note.id, event.target.value)}
                      aria-label={`Disposition for note ${note.id}`}
                    >
                      <option>Pending Review</option>
                      <option>Reviewed — No Action</option>
                      <option>Further Review Required</option>
                    </select>
                  </div>
                ))}
                {!detail.notes.length && <p className="muted">No analyst notes yet.</p>}
              </div>

              <form className="note-form" onSubmit={submitNote}>
                <label className="field-label" htmlFor="note-text">
                  New analyst note
                </label>
                <textarea
                  id="note-text"
                  className="login-input"
                  rows={3}
                  value={noteText}
                  onChange={(event) => setNoteText(event.target.value)}
                  placeholder="Describe what the analyst observed in the synthetic record."
                />
                <div className="note-form-actions">
                  <select
                    className="full-select"
                    value={disposition}
                    onChange={(event) => setDisposition(event.target.value)}
                    aria-label="New note disposition"
                  >
                    <option>Pending Review</option>
                    <option>Reviewed — No Action</option>
                    <option>Further Review Required</option>
                  </select>
                  <button className="primary-button" type="submit" disabled={busy || !noteText.trim()}>
                    Save note
                  </button>
                </div>
              </form>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
