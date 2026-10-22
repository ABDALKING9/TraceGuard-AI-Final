import { spawn } from "node:child_process";
import { copyFileSync, existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_DIR = path.resolve(here, "..", "..");
const PROJECT_ROOT = path.resolve(FRONTEND_DIR, "..");

export const BACKEND_PORT = 8000;
export const FRONTEND_PORT = 4173;
export const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
export const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}`;

async function waitForHttp(url: string, timeoutMs = 90_000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastError = "";
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
      lastError = `status ${response.status}`;
    } catch (e) {
      lastError = e instanceof Error ? e.message : String(e);
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for ${url} (${lastError})`);
}

/**
 * Boots an isolated backend (a copy of the demonstration database) and the
 * production preview server so the end-to-end suite never touches the real
 * `data/traceguard.db` file.
 */
export async function setup() {
  const workspace = mkdtempSync(path.join(tmpdir(), "traceguard-e2e-"));
  const databasePath = path.join(workspace, "traceguard-e2e.db");
  const sourceDatabase = path.join(PROJECT_ROOT, "data", "traceguard.db");
  if (existsSync(sourceDatabase)) copyFileSync(sourceDatabase, databasePath);

  const python = path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe");
  const backend = spawn(
    python,
    [
      "-m",
      "uvicorn",
      "backend.app.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(BACKEND_PORT),
    ],
    {
      cwd: PROJECT_ROOT,
      env: {
        ...process.env,
        TRACEGUARD_DATABASE_URL: `sqlite:///${databasePath.replace(/\\/g, "/")}`,
        TRACEGUARD_SECRET_KEY: "traceguard-e2e-signing-key",
      },
      stdio: "pipe",
    },
  );
  backend.stdout?.on("data", (chunk) => process.stdout.write(`[backend] ${chunk}`));
  backend.stderr?.on("data", (chunk) => process.stderr.write(`[backend] ${chunk}`));

  const viteBin = path.join(FRONTEND_DIR, "node_modules", "vite", "bin", "vite.js");
  const frontend = spawn(
    process.execPath,
    [viteBin, "preview", "--host", "127.0.0.1", "--port", String(FRONTEND_PORT)],
    { cwd: FRONTEND_DIR, stdio: "pipe" },
  );
  frontend.stdout?.on("data", (chunk) => process.stdout.write(`[preview] ${chunk}`));
  frontend.stderr?.on("data", (chunk) => process.stderr.write(`[preview] ${chunk}`));

  await waitForHttp(`${BACKEND_URL}/health`);
  await waitForHttp(FRONTEND_URL);

  return async () => {
    backend.kill();
    frontend.kill();
    await new Promise((resolve) => setTimeout(resolve, 300));
  };
}
