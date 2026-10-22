import { useCallback } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Database,
  FileSearch,
  GitBranch,
  RefreshCw,
  ShieldCheck,
  Users,
} from "lucide-react";
import type { ActivityResponse, MetaResponse, RecordItem, Summary } from "../api/types";
import { ActivityChart, PlatformComparisonChart, RiskDistributionChart } from "../components/charts";
import { Empty, Metric, PanelHeading, RecordTable } from "../components/ui";

export function Overview({
  summary,
  activity,
  recent,
  meta,
  busy,
  activityInterval,
  onActivityIntervalChange,
  onSeed,
  onRefresh,
  onSelectRecord,
  onOpenExplorer,
}: {
  summary: Summary | null;
  activity: ActivityResponse | null;
  recent: RecordItem[];
  meta: MetaResponse | null;
  busy: boolean;
  activityInterval: string;
  onActivityIntervalChange: (interval: string) => void;
  onSeed: () => void;
  onRefresh: () => void;
  onSelectRecord: (record: RecordItem) => void;
  onOpenExplorer: () => void;
}) {
  const platformRows = summary?.platform_distribution ?? [];
  const formatMetric = useCallback((value: number | null | undefined): string => {
    if (value === null || value === undefined || Number.isNaN(value)) return "—";
    return (value * 100).toFixed(1) + "%";
  }, []);

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">INTELLIGENCE OVERVIEW</div>
          <h1>Investigation Overview</h1>
          <p>Review synthetic records, inspect explainable indicators, and manage cases.</p>
        </div>
        <div className="heading-actions">
          <button className="secondary-button" onClick={onRefresh} disabled={busy}>
            <RefreshCw size={15} /> Refresh
          </button>
          <button className="primary-button" onClick={onSeed} disabled={busy}>
            <Database size={16} />
            {busy ? "Working..." : "Load Demo Data"}
          </button>
        </div>
      </div>

      <div className="notice">
        <ShieldCheck size={19} />
        <div>
          <strong>Academic prototype · Synthetic data only</strong>
          <p>{meta?.synthetic_data_notice ?? "No connection to Telegram, WhatsApp, or Instagram."}</p>
        </div>
      </div>

      <div className="metric-grid">
        <Metric icon={<FileSearch />} label="Content records" value={summary?.records ?? "—"} hint="Posts and messages" />
        <Metric icon={<Users />} label="Synthetic accounts" value={summary?.accounts ?? "—"} hint="Across 3 simulated platforms" />
        <Metric icon={<ShieldCheck />} label="Investigation cases" value={summary?.cases ?? "—"} hint="Persisted in local database" />
        <Metric icon={<AlertTriangle />} label="Pending review" value={summary?.pending_review ?? "—"} hint="Awaiting analyst review" />
      </div>

      {meta?.ml_engine_version && meta?.ml_metrics ? (
        <section className="panel">
          <PanelHeading
            title="Offline ML classifier"
            subtitle={`TF-IDF + LogisticRegression · ${meta.ml_engine_version}`}
            icon={<Database size={19} />}
          />
          <div className="metric-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
            <Metric icon={<BarChart3 size={16} />} label="Held-out accuracy" value={formatMetric(meta.ml_metrics.held_out_split?.accuracy)} hint="held-out split" />
            <Metric icon={<ShieldCheck size={16} />} label="Held-out precision" value={formatMetric(meta.ml_metrics.held_out_split?.precision_macro)} hint="macro-averaged" />
            <Metric icon={<Activity size={16} />} label="Held-out recall" value={formatMetric(meta.ml_metrics.held_out_split?.recall_macro)} hint="macro-averaged" />
            <Metric icon={<Users size={16} />} label="Held-out F1" value={formatMetric(meta.ml_metrics.held_out_split?.f1_macro)} hint="macro-averaged" />
            <Metric icon={<Database size={16} />} label="Challenge accuracy" value={formatMetric(meta.ml_metrics.challenge_set?.accuracy)} hint="independent set" />
            <Metric icon={<BarChart3 size={16} />} label="Challenge F1" value={formatMetric(meta.ml_metrics.challenge_set?.f1_macro)} hint="macro-averaged" />
          </div>
          <div className="metric-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", marginTop: "0.75rem" }}>
            <Metric icon={<Database size={16} />} label="Training samples" value={meta.ml_metrics.training_samples ?? "—"} hint="synthetic labelled corpus" />
            <Metric icon={<Database size={16} />} label="Held-out samples" value={meta.ml_metrics.test_samples ?? "—"} hint="stratified split" />
            <Metric icon={<Database size={16} />} label="Challenge samples" value={meta.ml_metrics.challenge_samples ?? "—"} hint="never used in training" />
          </div>
          <p className="body-copy muted">
            {meta.ml_metrics.note ?? "Metrics are computed on synthetic demonstration data."}
          </p>
          <p className="body-copy muted">
            Perfect held-out scores reflect the keyword-separable synthetic corpus by design.
            Challenge-set results show realistic, imperfect generalization. Neither is a
            real-world detection claim.
          </p>
        </section>
      ) : meta?.ml_engine_version ? (
        <section className="panel">
          <PanelHeading
            title="Offline ML classifier"
            subtitle={`TF-IDF + LogisticRegression · ${meta.ml_engine_version}`}
            icon={<Database size={19} />}
          />
          <p className="body-copy muted">ML metrics are not yet available. Run an ML analysis to train the model and compute evaluation metrics.</p>
        </section>
      ) : null}

      <div className="two-col">
        <section className="panel">
          <PanelHeading
            title="Review priority distribution"
            subtitle={summary?.risk_basis ? `Latest saved analysis per record (${summary.risk_basis})` : "Latest saved analysis by risk category"}
            icon={<BarChart3 size={19} />}
          />
          <RiskDistributionChart data={summary?.risk_distribution ?? []} />
        </section>

        <section className="panel">
          <PanelHeading
            title="Platform distribution"
            subtitle={summary?.platform_basis ? `Synthetic records by simulated source (${summary.platform_basis})` : "Fictional records by simulated source"}
            icon={<Activity size={19} />}
          />
          <div className="platform-list">
            {platformRows.map((row) => (
              <div className="platform-row" key={row.platform}>
                <div className={`platform-icon ${row.platform.toLowerCase()}`}>{row.platform.slice(0, 1)}</div>
                <div className="platform-name">
                  {row.platform}
                  <span>Simulated source</span>
                </div>
                <strong>{row.count}</strong>
              </div>
            ))}
            {!platformRows.length && <Empty text="No records yet." />}
          </div>
          {platformRows.length ? (
            <div className="chart-wrap chart-wrap-compact">
              <PlatformComparisonChart
                records={summary?.platform_distribution ?? []}
                accounts={summary?.account_distribution ?? []}
              />
            </div>
          ) : null}
        </section>
      </div>

  <section className="panel">
        <PanelHeading
          title="Record volume over time"
          subtitle="Synthetic records created per bucket"
          icon={<BarChart3 size={19} />}
          action={
            <div className="segmented" role="group" aria-label="Activity interval">
              {["day", "week"].map((option) => (
                <button
                  key={option}
                  type="button"
                  className={activityInterval === option ? "active" : ""}
                  onClick={() => onActivityIntervalChange(option)}
                >
                  {option === "day" ? "Daily" : "Weekly"}
                </button>
              ))}
            </div>
          }
        />
        <ActivityChart buckets={activity?.buckets ?? []} interval={activityInterval} />
      </section>

      <section className="panel">
        <PanelHeading
          title="Recent content records"
          subtitle="Open a record to inspect its evidence and analysis."
          icon={<GitBranch size={19} />}
          action={
            <button className="text-button" onClick={onOpenExplorer}>
              View all records →
            </button>
          }
        />
        <RecordTable records={recent} onSelect={onSelectRecord} emptyText="No records yet. Load the demo data to populate the table." />
      </section>
    </>
  );
}
