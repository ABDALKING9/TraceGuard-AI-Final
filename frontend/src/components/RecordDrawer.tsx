import { useCallback, useEffect, useState } from "react";
import { Activity, ShieldCheck, X } from "lucide-react";
import type {
  CaseItem,
  CompareResponse,
  MlFeatureContribution,
  MatchedIndicator,
  RecordItem,
} from "../api/types";
import { RiskBadge } from "./ui";

export function RecordDrawer({
  record,
  cases,
  onClose,
  onRunAnalysis,
  onCompareEngines,
  onUpdateReview,
  onAttachToCase,
  onAddNote,
}: {
  record: RecordItem | null;
  cases: CaseItem[];
  onClose: () => void;
  onRunAnalysis: (recordId: number, engine: string) => Promise<void>;
  onCompareEngines?: (recordId: number) => Promise<CompareResponse | void>;
  onUpdateReview: (recordId: number, reviewStatus: string) => Promise<void>;
  onAttachToCase: (caseId: number, recordId: number) => Promise<void>;
  onAddNote: (caseId: number, recordId: number, noteText: string) => Promise<void>;
}) {
  const [caseId, setCaseId] = useState("");
  const [noteText, setNoteText] = useState("");
  const [noteError, setNoteError] = useState("");
  const [attachError, setAttachError] = useState("");
  const [apiError, setApiError] = useState("");
  const [busy, setBusy] = useState(false);
  const [engine, setEngine] = useState<"rules" | "ml">("rules");
  const [comparison, setComparison] = useState<CompareResponse | null>(null);
  const [compareBusy, setCompareBusy] = useState(false);
  const [runBusy, setRunBusy] = useState<"rules" | "ml" | null>(null);

  useEffect(() => {
    setCaseId("");
    setNoteText("");
    setNoteError("");
    setAttachError("");
    setComparison(null);
  }, [record?.id]);

  if (!record) return null;
  const current = record;

  // Separate rule and ML analyses already stored on the record.
  const existingAnalysis = current.analysis;
  const ruleAnalysis = existingAnalysis?.engine_version?.startsWith("ml-")
    ? null
    : existingAnalysis;
  const mlAnalysis = existingAnalysis?.engine_version?.startsWith("ml-")
    ? existingAnalysis
    : null;

  const hasRule = !!ruleAnalysis;
  const hasMl = !!mlAnalysis;
  const bothAvailable = hasRule && hasMl;
  const agree = bothAvailable
    ? ruleAnalysis.risk_category === mlAnalysis.risk_category
    : null;

  async function runAnalysis(targetEngine: "rules" | "ml") {
    setRunBusy(targetEngine);
    try {
      await onRunAnalysis(current.id, targetEngine);
      // Freshly fetched record would have both; refresh parent data via load in App.
      // We just mark the run as complete so the UI can re-render from updated state.
    } catch (e) {
      setApiError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunBusy(null);
    }
  }

  async function compareEngines() {
    if (!onCompareEngines) return;
    setCompareBusy(true);
    try {
      const result = await onCompareEngines(current.id);
      if (result) setComparison(result);
    } catch (e) {
      setApiError(e instanceof Error ? e.message : String(e));
    } finally {
      setCompareBusy(false);
    }
  }

  async function attach() {
    if (!caseId) {
      setAttachError("Please select a case before attaching.");
      return;
    }
    setAttachError("");
    setBusy(true);
    try {
      await onAttachToCase(Number(caseId), current.id);
      setCaseId("");
    } catch (e) {
      setAttachError(e instanceof Error ? e.message : "Failed to attach record to case.");
    } finally {
      setBusy(false);
    }
  }

  async function saveNote() {
    if (!noteText.trim()) {
      setNoteError("Please enter a note before saving.");
      return;
    }
    if (!caseId) {
      setNoteError("Please select a case before saving a note.");
      return;
    }
    setNoteError("");
    setBusy(true);
    try {
      await onAddNote(Number(caseId), current.id, noteText.trim());
      setNoteText("");
      setCaseId("");
    } catch (e) {
      setNoteError(
        e instanceof Error ? e.message : "Failed to save note. Please try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  function indicatorRow(
    indicator: MatchedIndicator | MlFeatureContribution,
    isMl: boolean,
  ) {
    return (
      <div className="indicator" key={indicator.id}>
        <strong>{indicator.label}</strong>
        <span>
          {isMl ? `coef ${indicator.weight.toFixed(3)}` : `+${indicator.weight} points`}
        </span>
        {isMl && indicator.tfidf != null ? (
          <span className="muted">· tfidf {indicator.tfidf.toFixed(3)}</span>
        ) : null}
      </div>
    );
  }

  function engineResultBlock(
    title: string,
    version: string,
    score: number,
    category: string,
    indicators: MatchedIndicator[],
    explanations: string[],
    isMl: boolean,
    probability: number | null,
    positiveFeatures?: MlFeatureContribution[],
    negativeFeatures?: MlFeatureContribution[],
  ) {
    return (
      <section className="engine-block">
        <div className="engine-header">
          <h4>{title}</h4>
          <span className="engine-version">{version}</span>
        </div>
        <div className="score-box">
          <div>
            <span>Review priority score</span>
            <strong>{score}</strong>
          </div>
          {isMl && probability != null ? (
            <div className="ml-probability">
              <span>Model probability output (risky class):</span>
              <strong>{(probability * 100).toFixed(1)}%</strong>
              <span className="muted">
                · confidence-like score, not a calibrated probability of wrongdoing
              </span>
            </div>
          ) : null}
          <RiskBadge category={category} />
        </div>
        <h5>Matched indicators</h5>
        {indicators.length ? (
          indicators.map((ind) => indicatorRow(ind, isMl))
        ) : (
          <p className="muted">No indicators matched.</p>
        )}
        {isMl && positiveFeatures && positiveFeatures.length ? (
          <>
            <h5>Features supporting this prediction</h5>
            {positiveFeatures.map((ind) => indicatorRow(ind, true))}
          </>
        ) : null}
        {isMl && negativeFeatures && negativeFeatures.length ? (
          <>
            <h5>Features opposing this prediction</h5>
            {negativeFeatures.map((ind) => indicatorRow(ind, true))}
          </>
        ) : null}
        <h5>Explanation</h5>
        <ul className="explanation-list">
          {explanations.map((e, i) => <li key={i}>{e}</li>)}
        </ul>
      </section>
    );
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

        {/* -------- Analysis Overview: both engines side by side -------- */}
        <section className="analysis-overview">
          <h3>Analysis overview</h3>
          {bothAvailable ? (
            <>
              <p className={agree ? "muted agree" : "muted disagree"}>
                {agree
                  ? "Engines agree on risk category."
                  : "Engines disagree — inspect context before acting."}
              </p>
              <div className="engine-columns">
                {engineResultBlock(
                  "Rule engine",
                  ruleAnalysis!.engine_version,
                  ruleAnalysis!.score,
                  ruleAnalysis!.risk_category,
                  ruleAnalysis!.matched_indicators,
                  ruleAnalysis!.explanations,
                  false,
                  null,
                )}
                {engineResultBlock(
                  "ML classifier",
                  mlAnalysis!.engine_version,
                  mlAnalysis!.score,
                  mlAnalysis!.risk_category,
                  mlAnalysis!.matched_indicators,
                  mlAnalysis!.explanations,
                  true,
                  mlAnalysis!.ml_probability ?? null,
                  mlAnalysis!.ml_positive_features,
                  mlAnalysis!.ml_negative_features,
                )}
              </div>
              <p className="muted comparison-note">
                Scores are not averaged and no combined risk score is produced. Disagreement
                is a reason to inspect context, not proof of wrongdoing.
              </p>
            </>
          ) : (
            <>
              {hasRule || hasMl ? (
                <>
                  {hasRule && (
                    <>
                      {engineResultBlock(
                        "Rule engine",
                        ruleAnalysis!.engine_version,
                        ruleAnalysis!.score,
                        ruleAnalysis!.risk_category,
                        ruleAnalysis!.matched_indicators,
                        ruleAnalysis!.explanations,
                        false,
                        null,
                      )}
                      <button
                        className="secondary-button"
                        onClick={() => void runAnalysis("ml")}
                        disabled={runBusy === "ml" || compareBusy}
                      >
                        <Activity size={16} /> Run ML classifier
                      </button>
                    </>
                  )}
                  {hasMl && (
                    <>
                      {engineResultBlock(
                        "ML classifier",
                        mlAnalysis!.engine_version,
                        mlAnalysis!.score,
                        mlAnalysis!.risk_category,
                        mlAnalysis!.matched_indicators,
                        mlAnalysis!.explanations,
                        true,
                        mlAnalysis!.ml_probability ?? null,
                        mlAnalysis!.ml_positive_features,
                        mlAnalysis!.ml_negative_features,
                      )}
                      <button
                        className="secondary-button"
                        onClick={() => void runAnalysis("rules")}
                        disabled={runBusy === "rules" || compareBusy}
                      >
                        <Activity size={16} /> Run rule engine
                      </button>
                    </>
                  )}
                  <div style={{ marginTop: "0.5rem" }}>
                    {onCompareEngines && (
                      <button
                        className="primary-button"
                        onClick={() => void compareEngines()}
                        disabled={compareBusy}
                      >
                        <Activity size={16} />
                        {comparison ? "Show side-by-side comparison" : "Compare both engines"}
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <p className="muted">No analysis has been run for this record yet.</p>
                  <div style={{ marginTop: "0.5rem" }}>
                    <button
                      className="primary-button"
                      onClick={() => void runAnalysis("rules")}
                      disabled={runBusy === "rules" || compareBusy}
                    >
                      <Activity size={16} /> Run rule engine
                    </button>
                    <button
                      className="primary-button"
                      onClick={() => void runAnalysis("ml")}
                      disabled={runBusy === "ml" || compareBusy}
                      style={{ marginLeft: "0.5rem" }}
                    >
                      <Activity size={16} /> Run ML classifier
                    </button>
                  </div>
                </>
              )}
            </>
          )}
        </section>

        {comparison ? (
          <section className="comparison-box">
            <h3>Rule vs ML comparison</h3>
            <p className={comparison.agree ? "muted agree" : "muted disagree"}>
              {comparison.agree
                ? "Engines agree on risk category."
                : "Engines disagree — inspect context before acting."}
            </p>
            <div className="comparison-columns">
              <div className="comparison-column">
                {engineResultBlock(
                  "Rule engine",
                  comparison.rule_engine.engine_version,
                  comparison.rule_engine.score,
                  comparison.rule_engine.risk_category,
                  comparison.rule_engine.matched_indicators,
                  comparison.rule_engine.explanations,
                  false,
                  null,
                )}
              </div>
              <div className="comparison-column">
                {engineResultBlock(
                  "ML classifier",
                  comparison.ml_engine.engine_version,
                  comparison.ml_engine.score,
                  comparison.ml_engine.risk_category,
                  comparison.ml_engine.matched_indicators,
                  comparison.ml_engine.explanations,
                  true,
                  comparison.ml_engine.ml_probability ?? null,
                  comparison.ml_engine.positive_features,
                  comparison.ml_engine.negative_features,
                )}
              </div>
            </div>
            <p className="muted comparison-note">{comparison.comparison_note}</p>
            <button
              className="secondary-button full-button"
              onClick={() => setComparison(null)}
              disabled={compareBusy}
            >
              Close comparison
            </button>
          </section>
        ) : null}

        {apiError ? (
          <div className="alert error" role="alert">
            <p>{apiError}</p>
          </div>
        ) : null}

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

        <div className="case-selector-wrap">
          <label className="field-label" htmlFor="case-select">
            Select a case (optional)
          </label>
          <select
            id="case-select"
            className="full-select"
            value={caseId}
            onChange={(event) => {
              setCaseId(event.target.value);
              setAttachError("");
              setNoteError("");
            }}
            aria-label="Select a case"
          >
            <option value="">Select a case...</option>
            {cases.map((item) => (
              <option key={item.id} value={item.id}>
                CASE-{String(item.id).padStart(4, "0")} · {item.title}
              </option>
            ))}
          </select>
          {cases.length === 0 && (
            <p className="muted">No cases available. Create a case in Investigations first.</p>
          )}
        </div>

        {attachError ? (
          <div className="alert error" role="alert">
            <p>{attachError}</p>
          </div>
        ) : null}

        <div className="drawer-actions">
          <button
            className="secondary-button"
            onClick={() => void attach()}
            disabled={busy || !caseId}
          >
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
          onChange={(event) => {
            setNoteText(event.target.value);
            setNoteError("");
          }}
          placeholder="Note what you observed in this synthetic record."
        />
        {noteError ? (
          <div className="alert error" role="alert">
            <p>{noteError}</p>
          </div>
        ) : null}
        <div className="drawer-actions">
          <button
            className="secondary-button"
            onClick={() => void saveNote()}
            disabled={busy || !caseId || !noteText.trim()}
          >
            Save note
          </button>
        </div>

        <p className="drawer-disclaimer">
          This is synthetic demo content. Scores are heuristic review priorities and never establish
          criminal activity. The ML classifier has only been evaluated on synthetic data.
        </p>
      </aside>
    </div>
  );
}
