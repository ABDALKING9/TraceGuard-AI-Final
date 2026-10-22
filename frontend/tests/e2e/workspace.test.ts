import { afterAll, beforeAll, describe, expect, it } from "vitest";
import puppeteer, { type Browser, type ConsoleMessage, type Page } from "puppeteer-core";

const FRONTEND_URL = "http://127.0.0.1:4173";
const CHROME_PATH =
  process.env.CHROME_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

type TrackedPage = {
  page: Page;
  consoleErrors: string[];
  failedRequests: string[];
};

async function openTrackedPage(browser: Browser): Promise<TrackedPage> {
  const page = await browser.newPage();
  await page.setViewport({ width: 1500, height: 950 });
  const consoleErrors: string[] = [];
  const failedRequests: string[] = [];
  page.on("console", (message: ConsoleMessage) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => consoleErrors.push(String(error)));
  page.on("requestfailed", (request) => {
    failedRequests.push(`${request.url()} ${request.failure()?.errorText ?? "failed"}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) failedRequests.push(`${response.status()} ${response.url()}`);
  });
  return { page, consoleErrors, failedRequests };
}

async function fill(page: Page, selector: string, value: string): Promise<void> {
  await page.click(selector);
  await page.keyboard.down("Control");
  await page.keyboard.press("KeyA");
  await page.keyboard.up("Control");
  await page.keyboard.press("Backspace");
  await page.type(selector, value);
}

/** React controlled inputs need the native value setter plus an input event. */
async function setDateInput(page: Page, selector: string, value: string): Promise<void> {
  await page.evaluate(
    (target, next) => {
      const input = document.querySelector(target) as HTMLInputElement | null;
      if (!input) throw new Error(`missing ${target}`);
      const setter = Object.getOwnPropertyDescriptor(
        window.HTMLInputElement.prototype,
        "value",
      )?.set;
      setter?.call(input, next);
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    },
    selector,
    value,
  );
}

function textOf(page: Page, selector: string): Promise<string> {
  return page.evaluate((target) => {
    const node = document.querySelector(target);
    return node?.textContent ?? "";
  }, selector);
}

async function signIn(page: Page): Promise<void> {
  await page.goto(FRONTEND_URL, { waitUntil: "networkidle2" });
  await page.waitForSelector("#login-email", { timeout: 30_000 });
  await fill(page, "#login-email", "demo@traceguard.local");
  await fill(page, "#login-password", "Demo@123");
  await page.click("button[type=submit]");
  await page.waitForSelector(".metric-grid", { timeout: 30_000 });
  await waitForDashboardData(page);
}

/** The metric cards render placeholders until the dashboard request resolves. */
async function waitForDashboardData(page: Page): Promise<void> {
  await page.waitForFunction(
    () => {
      const value = document.querySelector(".metric-card strong")?.textContent ?? "";
      return /^\d+$/.test(value);
    },
    { timeout: 30_000 },
  );
}

async function navigateTo(page: Page, label: string): Promise<void> {
  await page.click(`[data-testid="nav-${label.toLowerCase().replace(/\s+/g, "-")}"]`);
}

describe("TraceGuard AI workspace (end to end)", () => {
  let browser: Browser;

  beforeAll(async () => {
    browser = await puppeteer.launch({
      executablePath: CHROME_PATH,
      headless: true,
      args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    });
  }, 120_000);

  afterAll(async () => {
    await browser?.close();
  });

  it("requires a session and signs in with the demonstration credentials", async () => {
    const { page } = await openTrackedPage(browser);
    try {
      await page.goto(FRONTEND_URL, { waitUntil: "networkidle2" });
      await page.waitForSelector("#login-email", { timeout: 30_000 });
      expect(await page.$(".app-shell")).toBeNull();

      await fill(page, "#login-email", "demo@traceguard.local");
      await fill(page, "#login-password", "Demo@123");
      await page.click("button[type=submit]");
      await page.waitForSelector(".metric-grid", { timeout: 30_000 });
      await waitForDashboardData(page);

      const metrics = await page.$$eval(".metric-card strong", (nodes) =>
        nodes.map((node) => node.textContent),
      );
      expect(metrics[0]).toBe("150");
      expect(metrics[1]).toBe("75");
      // The seeded corpus ships 30 cases; analysts may add more in the demo database.
      expect(Number(metrics[2])).toBeGreaterThanOrEqual(30);
      expect(await textOf(page, "[data-testid=session-user]")).toContain("demo@traceguard.local");
    } finally {
      await page.close();
    }
  }, 120_000);

  it("renders the dashboard charts and filters records by date range", async () => {
    const { page, consoleErrors, failedRequests } = await openTrackedPage(browser);
    try {
      await signIn(page);

      await page.waitForSelector("[data-testid=risk-chart]", { timeout: 30_000 });
      await page.waitForSelector("[data-testid=platform-chart]", { timeout: 30_000 });
      await page.waitForSelector("[data-testid=activity-chart]", { timeout: 30_000 });

      await navigateTo(page, "Content Explorer");
      await page.waitForSelector("form.filters", { timeout: 30_000 });
      await page.waitForSelector("[data-testid=record-row]", { timeout: 30_000 });
      const before = await textOf(page, "[data-testid=record-count]");
      expect(before).toContain("150");

      await setDateInput(page, 'input[aria-label="Records from date"]', "2026-10-02");
      await setDateInput(page, 'input[aria-label="Records to date"]', "2026-10-05");
      await page.click("form.filters button[type=submit]");
      await page.waitForFunction(
        (previous) => {
          const node = document.querySelector("[data-testid=record-count]");
          return Boolean(node && node.textContent !== previous);
        },
        { timeout: 30_000 },
        before,
      );

      const after = await textOf(page, "[data-testid=record-count]");
      expect(after).not.toBe(before);
      expect(after).not.toContain("150 records");
      expect(Number(after.replace(/\D/g, ""))).toBeGreaterThan(0);
      expect(Number(after.replace(/\D/g, ""))).toBeLessThan(150);

      // A range without data must show the empty state instead of a stale table.
      await setDateInput(page, 'input[aria-label="Records from date"]', "2020-01-01");
      await setDateInput(page, 'input[aria-label="Records to date"]', "2020-01-02");
      await page.click("form.filters button[type=submit]");
      await page.waitForFunction(
        () => document.querySelector("[data-testid=record-count]")?.textContent === "0 records",
        { timeout: 30_000 },
      );
      expect(await textOf(page, ".empty-state")).toContain("No records match these filters");

      expect(consoleErrors).toEqual([]);
      expect(failedRequests).toEqual([]);
    } finally {
      await page.close();
    }
  }, 120_000);

  it("opens a record, shows its evidence and stores an analyst disposition", async () => {
    const { page, consoleErrors, failedRequests } = await openTrackedPage(browser);
    try {
      await signIn(page);
      await navigateTo(page, "Content Explorer");
      await page.waitForSelector("form.filters", { timeout: 30_000 });
      await page.waitForSelector("[data-testid=record-row]", { timeout: 30_000 });

      await page.evaluate(() => {
        const row = document.querySelector("[data-testid=record-row]");
        (row as HTMLElement | null)?.click();
      });
      await page.waitForSelector("[data-testid=record-drawer]", { timeout: 30_000 });
      const drawerText = await textOf(page, "[data-testid=record-drawer]");
      expect(drawerText).toContain("Review priority score");
      expect(drawerText).toContain("synthetic demo content");

      await page.select("#review-disposition", "Further Review Required");
      await page.waitForFunction(
        () =>
          (document.querySelector("#review-disposition") as HTMLSelectElement | null)?.value ===
          "Further Review Required",
        { timeout: 15_000 },
      );

      expect(consoleErrors).toEqual([]);
      expect(failedRequests).toEqual([]);
    } finally {
      await page.close();
    }
  }, 120_000);

  it("creates a case, attaches a record and stores an analyst note", async () => {
    const { page, consoleErrors, failedRequests } = await openTrackedPage(browser);
    try {
      await signIn(page);
      await navigateTo(page, "Investigations");
      await page.waitForSelector(".case-row", { timeout: 30_000 });

      const title = `E2E synthetic case ${Date.now()}`;
      await page.click("button.primary-button");
      await page.waitForSelector("#case-title", { timeout: 15_000 });
      await fill(page, "#case-title", title);
      await fill(page, "#case-description", "Created by the automated end-to-end suite.");
      await page.click("form.case-form button[type=submit]");
      await page.waitForFunction(
        (expected) => document.body.textContent?.includes(expected) ?? false,
        { timeout: 30_000 },
        title,
      );

      await page.evaluate((expected) => {
        const rows = Array.from(document.querySelectorAll(".case-row"));
        const target = rows.find((row) => row.textContent?.includes(expected));
        const button = target?.querySelector("button.secondary-button") as HTMLButtonElement | null;
        button?.click();
      }, title);
      await page.waitForSelector(".case-detail", { timeout: 30_000 });

      const marker = `NOTE-MARKER-${Date.now()}`;
      await page.type("#note-text", `Synthetic analyst note ${marker}.`);
      await page.click("form.note-form button[type=submit]");
      await page.waitForSelector(".note-row select", { timeout: 30_000 });
      expect(await textOf(page, ".note-row")).toContain(marker);

      await page.select(".note-row select", "Reviewed — No Action");
      await page.waitForFunction(
        () =>
          (document.querySelector(".note-row select") as HTMLSelectElement | null)?.value ===
          "Reviewed — No Action",
        { timeout: 15_000 },
      );
      expect(consoleErrors).toEqual([]);
      expect(failedRequests).toEqual([]);
    } finally {
      await page.close();
    }
  }, 120_000);

  it("renders the relationship graph and inspects a node", async () => {
    const { page, consoleErrors, failedRequests } = await openTrackedPage(browser);
    try {
      await signIn(page);
      await navigateTo(page, "Relationship Graph");
      await page.waitForSelector("[data-testid=graph-canvas]", { timeout: 30_000 });
      await page.waitForFunction(
        () => {
          const canvas = document.querySelector("[data-testid=graph-canvas]") as HTMLElement | null;
          return Boolean(canvas && canvas.dataset.nodes);
        },
        { timeout: 30_000 },
      );

      const nodeCount = await page.$eval(
        "[data-testid=graph-canvas]",
        (node) => (node as HTMLElement).dataset.nodes,
      );
      expect(nodeCount).toBe("75");

      const target = await page.evaluate(() => {
        const cy = (
          window as unknown as {
            __traceguardCytoscape?: {
              nodes: () => ArrayLike<{ renderedPosition: () => { x: number; y: number } }>;
            };
          }
        ).__traceguardCytoscape;
        const node = cy?.nodes()[0];
        if (!node) return null;
        const position = node.renderedPosition();
        const rect = (
          document.querySelector("[data-testid=graph-canvas]") as HTMLElement
        ).getBoundingClientRect();
        return { x: rect.left + position.x, y: rect.top + position.y };
      });
      expect(target).not.toBeNull();

      await page.mouse.click(target!.x, target!.y);
      await page.waitForFunction(
        () => {
          const panel = document.querySelector("[data-testid=graph-panel]");
          return Boolean(panel && panel.textContent && panel.textContent.length > 40);
        },
        { timeout: 30_000 },
      );
      const panelText = await textOf(page, "[data-testid=graph-panel]");
      expect(panelText).toMatch(/Related records|Highest review priority/);

      expect(consoleErrors).toEqual([]);
      expect(failedRequests).toEqual([]);
    } finally {
      await page.close();
    }
  }, 120_000);

  it("publishes the methodology principle and the synthetic-data notice", async () => {
    const { page } = await openTrackedPage(browser);
    try {
      await signIn(page);
      await navigateTo(page, "Methodology");
      await page.waitForSelector("[data-testid=methodology-principle]", { timeout: 30_000 });
      const principle = await textOf(page, "[data-testid=methodology-principle]");
      expect(principle).toContain("not a probability");
      expect(principle.toLowerCase()).toContain("synthetic");
    } finally {
      await page.close();
    }
  }, 120_000);

  it("serves the favicon and keeps the session across a reload", async () => {
    const { page, failedRequests } = await openTrackedPage(browser);
    try {
      await signIn(page);
      const faviconStatus = await page.evaluate(async () => {
        const response = await fetch("/favicon.svg");
        return response.status;
      });
      expect(faviconStatus).toBe(200);

      await page.reload({ waitUntil: "networkidle2" });
      await page.waitForSelector(".metric-grid", { timeout: 30_000 });
      await waitForDashboardData(page);
      expect(await page.$("#login-email")).toBeNull();
      expect(failedRequests).toEqual([]);
    } finally {
      await page.close();
    }
  }, 120_000);
});
