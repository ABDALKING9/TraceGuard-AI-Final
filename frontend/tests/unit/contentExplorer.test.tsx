import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ContentExplorer } from "../../src/pages/ContentExplorer";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "OK",
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

const emptyPage = { items: [], total: 0, page: 1, page_size: 200, filters: {} };

describe("ContentExplorer", () => {
  it("requests records without filters on first load", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => jsonResponse(emptyPage));
    vi.stubGlobal("fetch", fetchMock);

    render(<ContentExplorer onSelectRecord={() => {}} />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    const [url] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/records?");
    expect(url).not.toContain("date_from=");
  });

  it("sends the date range and platform filters to the API", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => jsonResponse(emptyPage));
    vi.stubGlobal("fetch", fetchMock);

    render(<ContentExplorer onSelectRecord={() => {}} />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    await userEvent.selectOptions(screen.getByLabelText("Filter by platform"), "WhatsApp");
    await userEvent.type(screen.getByLabelText("Records from date"), "2026-09-22");
    await userEvent.type(screen.getByLabelText("Records to date"), "2026-09-30");
    await userEvent.click(screen.getByRole("button", { name: /apply filters/i }));

    await waitFor(() => {
      const urls = fetchMock.mock.calls.map((call) => call[0]);
      const applied = urls.find((url) => url.includes("date_from="));
      expect(applied).toBeDefined();
      expect(applied).toContain("platform=WhatsApp");
      expect(applied).toContain("date_from=2026-09-22");
      expect(applied).toContain("date_to=2026-09-30");
    });
  });

  it("renders the returned records and the total count", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      jsonResponse({
        items: [
          {
            id: 42,
            record_type: "message",
            content_text: "Synthetic dispatch example.",
            created_at: "2026-09-23T06:00:00",
            review_status: "Pending Review",
            is_synthetic: true,
            account: { id: 3, username: "wa_grove", display_name: "Fictional Wa Grove", platform: "WhatsApp" },
            analysis: {
              score: 40,
              risk_category: "Moderate",
              matched_indicators: [],
              explanations: [],
              engine_version: "rules-1.1",
              analyzed_at: null,
            },
          },
        ],
        total: 1,
        page: 1,
        page_size: 200,
        filters: {},
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ContentExplorer onSelectRecord={() => {}} />);

    expect(await screen.findByText("#42")).toBeInTheDocument();
    expect(screen.getByTestId("record-count")).toHaveTextContent("1 records");
  });
});
