import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

/**
 * jsdom does not implement ResizeObserver, which Recharts uses through its
 * ResponsiveContainer.  A minimal stub keeps the chart components mountable in
 * the unit tests.
 */
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (!("ResizeObserver" in globalThis)) {
  (globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverStub;
}

if (typeof window !== "undefined" && !("ResizeObserver" in window)) {
  (window as unknown as { ResizeObserver: unknown }).ResizeObserver = ResizeObserverStub;
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  try {
    window.sessionStorage.clear();
  } catch {
    /* storage disabled */
  }
});
