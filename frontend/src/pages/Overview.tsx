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
