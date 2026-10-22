import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ActivityChart, PlatformComparisonChart, RiskDistributionChart } from "../../src/components/charts";
import { Empty, Metric, RecordTable, RiskBadge } from "../../src/components/ui";

describe("RiskBadge", () => {
  it("renders the category with a matching class", () => {
    render(<RiskBadge category="High" />);
    const badge = screen.getByText("High");
    expect(badge).toHaveClass("risk-badge", "high");
  });
});

describe("Empty", () => {
  it("renders the empty message", () => {
    render(<Empty text="Nothing here yet." />);
    expect(screen.getByText("Nothing here yet.")).toBeInTheDocument();
  });
});

describe("Metric", () => {
  it("renders the label, value and hint", () => {
    render(<Metric icon={<span />} label="Content records" value={150} hint="Posts and messages" />);
    expect(screen.getByText("Content records")).toBeInTheDocument();
    expect(screen.getByText("150")).toBeInTheDocument();
    expect(screen.getByText("Posts and messages")).toBeInTheDocument();
  });
});

describe("RecordTable", () => {
  it("shows an empty state when there is nothing to review", () => {
    render(<RecordTable records={[]} onSelect={() => {}} />);
    expect(screen.getByText(/No records match this view/)).toBeInTheDocument();
  });

  it("lists records with their score and risk badge", () => {
    render(
      <RecordTable
        records={[
          {
            id: 7,
            record_type: "post",
            content_text: "Synthetic catalogue update.",
            created_at: "2026-09-22T06:00:00",
            review_status: "Pending Review",
            is_synthetic: true,
            account: { id: 1, username: "tg_dune", display_name: "Fictional Tg Dune", platform: "Telegram" },
            analysis: {
              score: 62,
              risk_category: "Elevated",
              matched_indicators: [],
              explanations: [],
              engine_version: "rules-1.1",
              analyzed_at: null,
            },
          },
        ]}
        onSelect={() => {}}
      />,
    );

    expect(screen.getByText("#7")).toBeInTheDocument();
    expect(screen.getByText("62")).toBeInTheDocument();
    expect(screen.getByText("Elevated")).toBeInTheDocument();
  });
});

describe("charts", () => {
  it("renders an empty state for the risk chart when nothing is analysed", () => {
    render(<RiskDistributionChart data={[{ category: "Low", count: 0 }]} />);
    expect(screen.getByText(/No analysed records yet/)).toBeInTheDocument();
  });

  it("renders the risk chart container when data is present", () => {
    render(
      <RiskDistributionChart
        data={[
          { category: "Low", count: 60 },
          { category: "High", count: 15 },
        ]}
      />,
    );
    expect(screen.getByTestId("risk-chart")).toBeInTheDocument();
  });

  it("renders an empty state for the platform chart", () => {
    render(<PlatformComparisonChart records={[]} accounts={[]} />);
    expect(screen.getByText(/No records yet/)).toBeInTheDocument();
  });

  it("renders an empty state for the activity chart", () => {
    render(<ActivityChart buckets={[]} interval="day" />);
    expect(screen.getByText(/No record activity/)).toBeInTheDocument();
  });

  it("renders the activity chart container when buckets exist", () => {
    render(<ActivityChart buckets={[{ bucket: "2026-09-22", count: 4 }]} interval="day" />);
    expect(screen.getByTestId("activity-chart")).toBeInTheDocument();
  });
});
