import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Search } from "lucide-react";
import { apiFetch } from "../api/client";
import type { RecordsResponse } from "../api/types";
import { RecordTable } from "../components/ui";

export type ExplorerFilters = {
  search: string;
  platform: string;
  risk: string;
  recordType: string;
  dateFrom: string;
  dateTo: string;
};

const EMPTY_FILTERS: ExplorerFilters = {
  search: "",
  platform: "",
  risk: "",
  recordType: "",
  dateFrom: "",
  dateTo: "",
};

export function ContentExplorer({
  onSelectRecord,
}: {
  onSelectRecord: (record: RecordsResponse["items"][number]) => void;
}) {
  const [filters, setFilters] = useState<ExplorerFilters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<ExplorerFilters>(EMPTY_FILTERS);
  const [data, setData] = useState<RecordsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const requestId = useRef(0);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (applied.search) params.set("search", applied.search);
    if (applied.platform) params.set("platform", applied.platform);
    if (applied.risk) params.set("risk_category", applied.risk);
    if (applied.recordType) params.set("record_type", applied.recordType);
    if (applied.dateFrom) params.set("date_from", applied.dateFrom);
    if (applied.dateTo) params.set("date_to", applied.dateTo);
    params.set("page_size", "200");
    params.set("sort", "id_asc");
    return params.toString();
  }, [applied]);

  const load = useCallback(async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError("");
    try {
      const result = await apiFetch<RecordsResponse>(`/api/v1/records?${query}`);
      if (id !== requestId.current) return;
      setData(result);
    } catch (e) {
      if (id !== requestId.current) return;
      setError(e instanceof Error ? e.message : String(e));
      setData(null);
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [query]);

  useEffect(() => {
    void load();
  }, [load]);

  function update<K extends keyof ExplorerFilters>(key: K, value: ExplorerFilters[K]) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function applyFilters(event?: { preventDefault: () => void }) {
    event?.preventDefault();
    setApplied(filters);
  }

  function resetFilters() {
    setFilters(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
  }

  const activeFilterCount = Object.values(applied).filter(Boolean).length;

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">RECORD REVIEW</div>
          <h1>Content Explorer</h1>
          <p>Search fictional posts and messages, then inspect their analysis.</p>
        </div>
        <span className="count-pill" data-testid="record-count">
          {data?.total ?? 0} records
        </span>
      </div>

      <section className="panel">
        <form className="filters" onSubmit={applyFilters}>
          <div className="search-box">
            <Search size={17} />
            <input
              value={filters.search}
              onChange={(event) => update("search", event.target.value)}
              placeholder="Search content or username..."
              aria-label="Search records"
            />
          </div>
          <select
            value={filters.platform}
            onChange={(event) => update("platform", event.target.value)}
            aria-label="Filter by platform"
          >
            <option value="">All platforms</option>
            <option>Telegram</option>
            <option>WhatsApp</option>
            <option>Instagram</option>
          </select>
          <select
            value={filters.risk}
            onChange={(event) => update("risk", event.target.value)}
            aria-label="Filter by risk category"
          >
            <option value="">All risk categories</option>
            <option>Low</option>
            <option>Moderate</option>
            <option>Elevated</option>
            <option>High</option>
          </select>
          <select
            value={filters.recordType}
            onChange={(event) => update("recordType", event.target.value)}
            aria-label="Filter by record type"
          >
            <option value="">All record types</option>
            <option value="post">Posts</option>
            <option value="message">Messages</option>
          </select>
          <label className="date-field">
            <span>From</span>
            <input
              type="date"
              value={filters.dateFrom}
              max={filters.dateTo || undefined}
              onChange={(event) => update("dateFrom", event.target.value)}
              aria-label="Records from date"
            />
          </label>
          <label className="date-field">
            <span>To</span>
            <input
              type="date"
              value={filters.dateTo}
              min={filters.dateFrom || undefined}
              onChange={(event) => update("dateTo", event.target.value)}
              aria-label="Records to date"
            />
          </label>
          <button className="primary-button" type="submit" disabled={loading}>
            Apply filters
          </button>
          <button className="secondary-button" type="button" onClick={resetFilters} disabled={loading}>
            Reset
          </button>
        </form>

        {error ? (
          <div className="alert error" role="alert">
            <p>{error}</p>
          </div>
        ) : null}

        {activeFilterCount > 0 ? (
          <p className="muted filter-summary">
            {activeFilterCount} filter{activeFilterCount === 1 ? "" : "s"} applied
            {applied.dateFrom || applied.dateTo
              ? ` · ${applied.dateFrom || "start"} → ${applied.dateTo || "today"}`
              : ""}
          </p>
        ) : null}

        <RecordTable
          records={data?.items ?? []}
          onSelect={onSelectRecord}
          emptyText={
            loading
              ? "Loading records..."
              : "No records match these filters. Reset the filters or load demo data."
          }
        />
      </section>
    </>
  );
}
