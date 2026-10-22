import { useEffect, useMemo, useRef, useState } from "react";
import cytoscape, { type Core } from "cytoscape";
import { GitBranch, LoaderCircle, Network, TriangleAlert } from "lucide-react";
import { apiFetch } from "../api/client";
import type { GraphData, GraphEdgeDetail, GraphNodeDetail } from "../api/types";
import { RISK_COLORS, RISK_ORDER } from "../components/charts";
import { Empty, PanelHeading, RiskBadge } from "../components/ui";

export function RelationshipGraph({
  graph,
  onSelectRecord,
}: {
  graph: GraphData | null;
  onSelectRecord: (recordId: number) => void;
}) {
  const container = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const [nodeDetail, setNodeDetail] = useState<GraphNodeDetail | null>(null);
  const [edgeDetail, setEdgeDetail] = useState<GraphEdgeDetail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const elements = useMemo(() => {
    if (!graph) return [] as cytoscape.ElementDefinition[];
    const nodes = graph.nodes.map((node) => ({
      group: "nodes" as const,
      data: {
        id: node.id,
        label: node.label,
        platform: node.platform,
        risk: node.risk_category,
        records: node.record_count,
        accountId: node.account_id,
        color: RISK_COLORS[node.risk_category] ?? "#5577e8",
        size: Math.max(18, Math.min(52, 16 + node.record_count * 3)),
      },
    }));
    const edges = graph.edges.map((edge) => ({
      group: "edges" as const,
      data: {
        id: `edge-${edge.id}`,
        edgeId: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.relationship_type.replace(/_/g, " "),
      },
    }));
    return [...nodes, ...edges];
  }, [graph]);

  useEffect(() => {
    if (!container.current || !elements.length) return;
    const cy = cytoscape({
      container: container.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            width: "data(size)",
            height: "data(size)",
            label: "data(label)",
            color: "#3a4759",
            "font-size": 8,
            "text-valign": "bottom",
            "text-margin-y": 4,
            "text-outline-color": "#ffffff",
            "text-outline-width": 2,
            "border-width": 1,
            "border-color": "#ffffff",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.4,
            "line-color": "#b6c2e4",
            "target-arrow-color": "#b6c2e4",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 6.5,
            color: "#8a95a6",
            "text-rotation": "autorotate",
            "text-outline-color": "#ffffff",
            "text-outline-width": 2,
          },
        },
        {
          selector: "node:active",
          style: { "border-color": "#526ee8", "border-width": 3 },
        },
        {
          selector: "node.synthetic-highlight",
          style: { "border-color": "#526ee8", "border-width": 3 },
        },
      ],
      layout: { name: "cose", animate: false, padding: 24, nodeRepulsion: 6500 },
    });
    cyRef.current = cy;

    cy.on("tap", "node", (event) => {
      const accountId = event.target.data("accountId") as number;
      void selectNode(accountId);
    });
    cy.on("tap", "edge", (event) => {
      const edgeId = event.target.data("edgeId") as number;
      void selectEdge(edgeId);
    });

    container.current.dataset.nodes = String(cy.nodes().length);
    container.current.dataset.edges = String(cy.edges().length);

    // Test hook: the end-to-end suite drives the graph through this handle.
    (window as unknown as { __traceguardCytoscape?: Core }).__traceguardCytoscape = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
      delete (window as unknown as { __traceguardCytoscape?: Core }).__traceguardCytoscape;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [elements]);

  async function selectNode(accountId: number) {
    setBusy(true);
    setError("");
    setEdgeDetail(null);
    try {
      setNodeDetail(await apiFetch<GraphNodeDetail>(`/api/v1/graph/nodes/${accountId}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setNodeDetail(null);
    } finally {
      setBusy(false);
    }
  }

  async function selectEdge(edgeId: number) {
    setBusy(true);
    setError("");
    setNodeDetail(null);
    try {
      setEdgeDetail(await apiFetch<GraphEdgeDetail>(`/api/v1/graph/edges/${edgeId}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setEdgeDetail(null);
    } finally {
      setBusy(false);
    }
  }

  function focusNode(node: GraphNodeDetail) {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("synthetic-highlight");
    const target = cy.getElementById(node.id);
    if (target.length) {
      target.addClass("synthetic-highlight");
      cy.animate({ center: { eles: target }, zoom: 1.6 }, { duration: 260 });
    }
  }

  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">RELATIONSHIP ANALYSIS</div>
          <h1>Relationship Graph</h1>
          <p>Inspect explicitly seeded synthetic relationships and their evidence.</p>
        </div>
      </div>

      {error ? (
        <div className="alert error" role="alert">
          <p>{error}</p>
        </div>
      ) : null}

      <section className="panel">
        <PanelHeading
          title="Evidence-backed synthetic links"
          subtitle="These links are demo fixtures, not inferred criminal coordination."
          icon={<GitBranch size={19} />}
          action={
            <div className="graph-legend">
              {RISK_ORDER.map((category) => (
                <span key={category} className="legend-item">
                  <i style={{ background: RISK_COLORS[category] }} />
                  {category}
                </span>
              ))}
            </div>
          }
        />

        {!graph || !graph.nodes.length ? (
          <Empty text="No relationship edges are available. Load demo data first." />
        ) : (
          <div className="graph-layout">
            <div className="graph-canvas-wrap">
              <div className="graph-canvas" ref={container} data-testid="graph-canvas" />
              <p className="muted graph-hint">
                {graph.nodes.length} accounts · {graph.edges.length} relationships · select a node or an
                edge to inspect its metadata and evidence.
              </p>
            </div>

            <aside className="graph-panel" data-testid="graph-panel">
              {busy ? (
                <div className="empty-state">
                  <LoaderCircle size={22} className="spin" />
                  <p>Loading evidence...</p>
                </div>
              ) : nodeDetail ? (
                <div className="graph-detail">
                  <div className="eyebrow">ACCOUNT #{nodeDetail.account_id}</div>
                  <h3>{nodeDetail.label}</h3>
                  <div className="record-meta">
                    <span className="platform-tag">{nodeDetail.platform}</span>
                    <span>{nodeDetail.display_name}</span>
                    <span className="synthetic-tag">Synthetic</span>
                  </div>
                  <div className="score-box">
                    <div>
                      <span>Highest review priority</span>
                      <strong>{nodeDetail.risk_score}</strong>
                    </div>
                    <RiskBadge category={nodeDetail.risk_category} />
                  </div>

                  <h4>Related records ({nodeDetail.record_count})</h4>
                  <div className="mini-list">
                    {nodeDetail.records.map((record) => (
                      <button
                        key={record.id}
                        type="button"
                        className="mini-row"
                        onClick={() => onSelectRecord(record.id)}
                      >
                        <strong>#{record.id}</strong>
                        <span className="mini-preview">{record.content_preview}</span>
                        {record.analysis ? (
                          <RiskBadge category={record.analysis.risk_category} />
                        ) : null}
                      </button>
                    ))}
                    {!nodeDetail.records.length && <p className="muted">No records for this account.</p>}
                  </div>

                  <h4>Evidence and indicators</h4>
                  <div className="mini-list">
                    {nodeDetail.records
                      .filter((record) => record.analysis && record.analysis.matched_indicators.length)
                      .slice(0, 6)
                      .map((record) => (
                        <div className="mini-row note-row" key={`evidence-${record.id}`}>
                          <div>
                            <p>
                              #{record.id}:{" "}
                              {record.analysis!.matched_indicators
                                .map((indicator) => indicator.label)
                                .join(", ")}
                            </p>
                            <small className="muted">Score {record.analysis!.score}</small>
                          </div>
                        </div>
                      ))}
                    {!nodeDetail.records.some((record) => record.analysis?.matched_indicators.length) && (
                      <p className="muted">No indicators matched for this account.</p>
                    )}
                  </div>

                  <h4>Relationships ({nodeDetail.relationships.length})</h4>
                  <div className="mini-list">
                    {nodeDetail.relationships.map((relationship) => (
                      <button
                        key={relationship.id}
                        type="button"
                        className="mini-row"
                        onClick={() => void selectEdge(relationship.id)}
                      >
                        <strong>{relationship.counterpart_label ?? "Unknown"}</strong>
                        <span className="muted">{relationship.relationship_type.replace(/_/g, " ")}</span>
                      </button>
                    ))}
                    {!nodeDetail.relationships.length && (
                      <p className="muted">No seeded relationships for this account.</p>
                    )}
                  </div>

                  <button className="secondary-button full-button" onClick={() => focusNode(nodeDetail)}>
                    <Network size={15} /> Centre on this account
                  </button>
                </div>
              ) : edgeDetail ? (
                <div className="graph-detail">
                  <div className="eyebrow">RELATIONSHIP #{edgeDetail.id}</div>
                  <h3>{edgeDetail.relationship_type.replace(/_/g, " ")}</h3>
                  <div className="edge-pair">
                    <div className="edge-node">
                      {edgeDetail.source_label}
                      <small>{edgeDetail.source_platform}</small>
                    </div>
                    <div className="edge-line">
                      <span>link</span>
                      <div />
                    </div>
                    <div className="edge-node">
                      {edgeDetail.target_label}
                      <small>{edgeDetail.target_platform}</small>
                    </div>
                  </div>
                  <h4>Shared feature</h4>
                  <p className="muted">{edgeDetail.shared_feature || "Not recorded"}</p>
                  <h4>Evidence description</h4>
                  <p className="muted">{edgeDetail.evidence_description}</p>
                  <p className="drawer-disclaimer">
                    <TriangleAlert size={13} /> This relationship is a seeded synthetic fixture. It does
                    not describe a real person or a real criminal network.
                  </p>
                </div>
              ) : (
                <Empty text="Select a node or an edge in the graph to inspect its metadata." />
              )}
            </aside>
          </div>
        )}
      </section>
    </>
  );
}
