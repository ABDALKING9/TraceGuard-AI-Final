import { Suspense, lazy, useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  FileSearch,
  GitBranch,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  RefreshCw,
  ShieldCheck,
  User,
} from "lucide-react";
import { apiFetch, compareEngines, fetchMeta } from "./api/client";
import type {
  ActivityResponse,
  CaseDetail,
  CaseItem,
  GraphData,
  MetaResponse,
  RecordItem,
  RecordsResponse,
  Summary,
} from "./api/types";
import { SessionProvider, useSession } from "./auth/SessionContext";
import { LoginScreen } from "./components/LoginScreen";
import { RecordDrawer } from "./components/RecordDrawer";

const Overview = lazy(() => import("./pages/Overview").then((module) => ({ default: module.Overview })));
const ContentExplorer = lazy(() =>
  import("./pages/ContentExplorer").then((module) => ({ default: module.ContentExplorer })),
);
const Investigations = lazy(() =>
  import("./pages/Investigations").then((module) => ({ default: module.Investigations })),
);
const RelationshipGraph = lazy(() =>
  import("./pages/RelationshipGraph").then((module) => ({ default: module.RelationshipGraph })),
);
const Methodology = lazy(() =>
  import("./pages/Methodology").then((module) => ({ default: module.Methodology })),
);

const DEMO_EMAIL = "demo@traceguard.local";
const DEMO_PASSWORD = "Demo@123";

type PageName = "Overview" | "Content Explorer" | "Investigations" | "Relationship Graph" | "Methodology";

function Workspace() {
  const session = useSession();
  const [page, setPage] = useState<PageName>("Overview");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [activity, setActivity] = useState<ActivityResponse | null>(null);
  const [activityInterval, setActivityInterval] = useState("day");
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [recent, setRecent] = useState<RecordItem[]>([]);
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [selected, setSelected] = useState<RecordItem | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const load = useCallback(
    async (interval: string) => {
      setBusy(true);
      setError("");
      try {
        const [summaryData, activityData, caseData, graphData, recentData, metaData] = await Promise.all([
          apiFetch<Summary>("/api/v1/dashboard/summary"),
          apiFetch<ActivityResponse>(`/api/v1/dashboard/activity?interval=${interval}`),
          apiFetch<CaseItem[]>("/api/v1/cases"),
          apiFetch<GraphData>("/api/v1/graph"),
          apiFetch<RecordsResponse>("/api/v1/records?page_size=8&sort=created_desc"),
          fetchMeta(),
        ]);
        setSummary(summaryData);
        setActivity(activityData);
        setCases(caseData);
        setGraph(graphData);
        setRecent(recentData.items);
        setMeta(metaData);
        setSelected((current) => {
          if (!current) return null;
          const match = recentData.items.find((item) => item.id === current.id);
          return match ?? current;
        });
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  useEffect(() => {
    void load(activityInterval);
  }, [load, activityInterval]);

  async function seedDemo() {
    setBusy(true);
    setError("");
    try {
      const result = await apiFetch<{ records: number }>("/api/v1/demo/seed", { method: "POST" });
      await load(activityInterval);
      setToast(`Synthetic demo data ready. ${result.records} records in the seed dataset.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runAnalysis(recordId: number, engine: string = "rules") {
    try {
      await apiFetch(`/api/v1/analysis/run/${recordId}?engine=${engine}`, { method: "POST" });
      await load(activityInterval);
      setToast(`Analysis saved for record #${recordId} (${engine} engine).`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function compareRecordEngines(recordId: number) {
    try {
      const result = await compareEngines(recordId);
      await load(activityInterval);
      setToast(`Compared rule vs ML for record #${recordId}. ${result.agree ? "Engines agree." : "Engines disagree — review context."}`);
      return result;
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function updateReview(recordId: number, reviewStatus: string) {
    try {
      await apiFetch(`/api/v1/records/${recordId}/review`, {
        method: "PATCH",
        body: JSON.stringify({ review_status: reviewStatus }),
      });
      setSelected((current) =>
        current && current.id === recordId ? { ...current, review_status: reviewStatus } : current,
      );
      await load(activityInterval);
      setToast("Review disposition saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function createCase(title: string, description: string) {
    try {
      const created = await apiFetch<CaseItem>("/api/v1/cases", {
        method: "POST",
        body: JSON.stringify({ title, description, status: "Open" }),
      });
      await load(activityInterval);
      setToast(`Created case #${created.id}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function openCase(caseId: number): Promise<CaseDetail | null> {
    return apiFetch<CaseDetail>(`/api/v1/cases/${caseId}`);
  }

  async function attachToCase(caseId: number, recordId: number) {
    try {
      await apiFetch(`/api/v1/cases/${caseId}/records/${recordId}`, { method: "POST" });
      await load(activityInterval);
      setToast(`Record #${recordId} attached to case #${caseId}.`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      throw new Error(msg);
    }
  }

  async function addNote(caseId: number, noteText: string, disposition: string, recordId?: number) {
    try {
      await apiFetch(`/api/v1/cases/${caseId}/notes`, {
        method: "POST",
        body: JSON.stringify({ note_text: noteText, disposition, record_id: recordId ?? null }),
      });
      await load(activityInterval);
      setToast("Analyst note saved.");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      throw new Error(msg);
    }
  }

  async function updateDisposition(caseId: number, noteId: number, disposition: string) {
    try {
      const detail = await apiFetch<CaseDetail>(`/api/v1/cases/${caseId}`);
      const note = detail.notes.find((item) => item.id === noteId);
      if (!note) return;
      await apiFetch(`/api/v1/cases/${caseId}/notes/${noteId}`, {
        method: "PATCH",
        body: JSON.stringify({
          note_text: note.note_text,
          disposition,
          record_id: note.record_id,
        }),
      });
      await load(activityInterval);
      setToast("Note disposition updated.");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }
  async function openRecord(recordId: number) {
    try {
      const record = await apiFetch<RecordItem>(`/api/v1/records/${recordId}`);
      setSelected(record);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  const menu = useMemo(
    () => [
      { label: "Overview" as PageName, icon: LayoutDashboard },
      { label: "Content Explorer" as PageName, icon: FileSearch },
      { label: "Investigations" as PageName, icon: ShieldCheck },
      { label: "Relationship Graph" as PageName, icon: GitBranch },
      { label: "Methodology" as PageName, icon: Activity },
    ],
    [],
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <ShieldCheck size={23} />
          </div>
          <div>
            <strong>TraceGuard</strong>
            <span>AI ANALYST WORKSPACE</span>
          </div>
        </div>
        <div className="nav-caption">WORKSPACE</div>
        {menu.map((item) => (
          <button
            key={item.label}
            data-testid={`nav-${item.label.replace(/\s+/g, "-").toLowerCase()}`}
            className={`nav-item ${page === item.label ? "active" : ""}`}
            onClick={() => setPage(item.label)}
          >
            <item.icon size={18} />
            {item.label}
          </button>
        ))}
        <div className="sidebar-bottom">
          <div className="offline-dot" />
          <div>
            <strong>Offline demo mode</strong>
            <span>Local synthetic dataset</span>
          </div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span> {page}
          </div>
          <div className="top-actions">
            <span className="demo-badge">
              <span /> Synthetic Data — Offline Demo
            </span>
            <span className="session-badge" data-testid="session-user">
              <User size={13} /> {session.email ?? "operator"}
            </span>
            <button
              className="icon-button"
              onClick={() => void load(activityInterval)}
              title="Refresh"
              aria-label="Refresh data"
            >
              <RefreshCw size={17} />
            </button>
            <button
              className="icon-button"
              onClick={() => void session.signOut()}
              title="Sign out"
              aria-label="Sign out"
              data-testid="sign-out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>

        <div className="content">
          {error ? (
            <div className="alert error" role="alert">
              <AlertTriangle size={18} />
              <div>
                <strong>Action needs attention</strong>
                <p>{error}</p>
              </div>
              <button onClick={() => setError("")}>Dismiss</button>
            </div>
          ) : null}
          {toast ? (
            <div className="alert success" role="status">
              <CheckCircle2 size={18} />
              <p>{toast}</p>
              <button onClick={() => setToast("")}>Dismiss</button>
            </div>
          ) : null}

          <Suspense
            fallback={
              <div className="empty-state">
                <LoaderCircle size={22} className="spin" />
                <p>Loading view...</p>
              </div>
            }
          >
            {page === "Overview" ? (
              <Overview
                summary={summary}
                activity={activity}
                recent={recent}
                meta={meta}
                busy={busy}
                activityInterval={activityInterval}
                onActivityIntervalChange={setActivityInterval}
                onSeed={() => void seedDemo()}
                onRefresh={() => void load(activityInterval)}
                onSelectRecord={setSelected}
                onOpenExplorer={() => setPage("Content Explorer")}
              />
            ) : null}

            {page === "Content Explorer" ? (
              <ContentExplorer onSelectRecord={setSelected} />
            ) : null}

            {page === "Investigations" ? (
              <Investigations
                cases={cases}
                onCreateCase={createCase}
                onOpenCase={openCase}
                onAddNote={(caseId, noteText, disposition) =>
                  addNote(caseId, noteText, disposition)
                }
                onUpdateDisposition={updateDisposition}
                onSelectRecord={(recordId) => void openRecord(recordId)}
              />
            ) : null}

            {page === "Relationship Graph" ? (
              <RelationshipGraph graph={graph} onSelectRecord={(recordId) => void openRecord(recordId)} />
            ) : null}

            {page === "Methodology" ? <Methodology meta={meta} /> : null}
          </Suspense>
        </div>

        <footer>
          TRACEGUARD AI <span>Academic MVP · Local-first · Synthetic data only</span>
        </footer>
      </main>

      <RecordDrawer
        record={selected}
        cases={cases}
        onClose={() => setSelected(null)}
        onRunAnalysis={runAnalysis}
        onCompareEngines={compareRecordEngines}
        onUpdateReview={updateReview}
        onAttachToCase={attachToCase}
        onAddNote={(caseId, recordId, noteText) => addNote(caseId, noteText, "Pending Review", recordId)}
      />
    </div>
  );
}

function AppRouter() {
  const session = useSession();

  if (session.status === "checking") {
    return (
      <div className="boot-screen">
        <LoaderCircle size={26} className="spin" />
        <p>Restoring session...</p>
      </div>
    );
  }

  if (session.status === "signed-out") {
    return (
      <LoginScreen
        demoEmail={DEMO_EMAIL}
        demoPassword={DEMO_PASSWORD}
        backendHint="Start the backend with: python -m uvicorn backend.app.main:app --port 8000"
        onSubmit={session.signIn}
      />
    );
  }

  return <Workspace />;
}

export default function App() {
  return (
    <SessionProvider>
      <AppRouter />
    </SessionProvider>
  );
}
