import type { MetaResponse } from "../api/types";
import { PanelHeading } from "../components/ui";

export function Methodology({ meta }: { meta: MetaResponse | null }) {
  const thresholds = meta?.risk_thresholds ?? {};
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">TRANSPARENCY</div>
          <h1>Methodology & Limitations</h1>
          <p>Understand what the prototype can and cannot conclude.</p>
        </div>
      </div>

      <div className="notice">
        <ShieldIcon />
        <div>
          <strong>Core principle</strong>
          <p data-testid="methodology-principle">
            {meta?.methodology_principle ??
              "TraceGuard AI is a synthetic-data research demonstration. Rule-based scores rank records for human review; a score is not a probability and never evidence that an account is involved in criminal activity."}
          </p>
        </div>
      </div>

      <div className="method-grid">
        <section className="panel">
          <PanelHeading title="How scoring works" subtitle={`Rule engine ${meta?.engine_version ?? "rules-1.1"}`} />
          <p className="body-copy">
            The backend normalizes text, matches a small set of configurable phrases, checks for
            benign-context language, deduplicates rule matches, and calculates a deterministic score
            from 0 to 100.
          </p>
          <ul>
            <li>Low: 0–{Math.max(0, (thresholds.Low ?? 25) - 1)}</li>
            <li>Moderate: {thresholds.Low ?? 25}–{Math.max(0, (thresholds.Moderate ?? 50) - 1)}</li>
            <li>Elevated: {thresholds.Moderate ?? 50}–{Math.max(0, (thresholds.Elevated ?? 75) - 1)}</li>
            <li>High: {thresholds.Elevated ?? 75}–100</li>
          </ul>
        </section>

        <section className="panel">
          <PanelHeading title="Offline ML classifier" subtitle={`${meta?.ml_engine_version ?? "ml-tfidf-logreg-v1.0"}`} />
          <p className="body-copy">
            An optional scikit-learn pipeline (TF-IDF vectorization + LogisticRegression) is trained on
            a synthetic labelled corpus and runs entirely on localhost. It produces a calibrated
            probability for the synthetic "risky" label, mapped to a 0–100 review-priority score.
            Top contributing TF-IDF features are shown as matched indicators.
          </p>
          <ul>
            <li>Vectorizer: TF-IDF, unigrams + bigrams, English stop words removed</li>
            <li>Classifier: LogisticRegression with balanced class weights</li>
            <li>Training data: 192 synthetic records (121 risky, 71 benign), disjoint from the seed corpus</li>
            <li>Evaluation: 25% held-out stratified split, metrics exposed via /api/v1/model/info</li>
            <li>No cloud/hosted AI; no real platform data ingested</li>
          </ul>
        </section>

        <section className="panel">
          <PanelHeading title="Important limitations" subtitle="What this prototype cannot do" />
          <ul>
            <li>All default content and accounts are synthetic.</li>
            <li>No platform APIs, scraping, or third-party ingestion are used.</li>
            <li>Rules can miss context and produce false positives.</li>
            <li>The ML classifier can overfit to the synthetic training vocabulary.</li>
            <li>A score is not a probability, accusation, or proof.</li>
            <li>Human review is always required before any action.</li>
            <li>Relationships are seeded fixtures, not inferred coordination.</li>
          </ul>
        </section>
      </div>

      <section className="panel">
        <PanelHeading title="Data provenance" subtitle="What is stored in the local SQLite database" />
        <p className="body-copy muted">
          {meta?.synthetic_data_notice ??
            "Every account, content record, case and relationship in this instance is synthetic and offline."}
        </p>
        <ul className="method-grid">
          <li>Accounts, messages and posts are generated from a deterministic template corpus.</li>
          <li>Cases, notes and relationships are seeded fixtures with explicit evidence text.</li>
          <li>ML model and metrics are persisted as local joblib/JSON files (no network).</li>
          <li>No network request leaves the machine; the backend runs on 127.0.0.1 only.</li>
        </ul>
      </section>
    </>
  );
}

function ShieldIcon() {
  return (
    <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}
