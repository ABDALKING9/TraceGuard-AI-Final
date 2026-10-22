# Antigravity Executor Prompt — Follow the Specification, Do Not Redesign

You are an implementation executor. The architecture and requirements have already been decided. Do not redesign the app, change the stack, add new features, or replace working code with a different approach.

## Rules
1. Inspect the current workspace, then create every file exactly as specified in the supplied project package. Preserve paths.
2. Do not create a different architecture. Use React + TypeScript + Vite, FastAPI + SQLAlchemy, and SQLite.
3. Do not connect to Telegram, WhatsApp, or Instagram. Do not scrape. No paid APIs, external AI, API keys, or cloud services.
4. Use synthetic data only.
5. Do not invent source code for files that are already supplied. Write the supplied contents verbatim.
6. You may correct only mechanical issues required to make the supplied code execute (for example, a missing import or an incorrect relative import). Every such change must be listed in the report and must not change requirements or design.
7. Do not claim success without running the relevant command.
8. Do not create a separate report file as the only report. Your final response must contain the full build report in chat, using `docs/BUILD_REPORT_TEMPLATE.md`.
9. If a command fails, capture the exact error, make the smallest mechanical correction, rerun the command, and record both attempts.
10. Do not spend time on speculative improvements. First make the specified code run.

## Execution sequence
A. Create the file tree from the provided package.
B. Install backend dependencies using `pip install -r backend/requirements.txt`.
C. Run `python -m backend.app.seed`.
D. Run `pytest backend/tests -q`.
E. Start backend and verify `GET http://127.0.0.1:8000/health` and `GET http://127.0.0.1:8000/api/v1/dashboard/summary`.
F. In `frontend`, run `npm install` and `npm run build`.
G. Start the frontend and confirm the page loads.
H. Perform the manual smoke test from `docs/TEST_PLAN.md`.
I. If any failure occurs, make the smallest code correction consistent with the documented design, then rerun affected checks.
J. Respond in chat with the complete report.

## Required chat report
Include:
- Verdict: PASS / PARTIAL / FAIL.
- Environment versions.
- Every command run, exit code, and meaningful output.
- Files created and any deviations from supplied source.
- Database tables, seed counts, and idempotency result.
- API health and endpoint checks.
- Backend test output.
- Frontend build output.
- Manual smoke-test checklist with evidence.
- External dependency audit (expected: no platform integrations, no paid APIs, no API keys).
- All defects with severity, reproduction steps, exact errors, and affected file paths.
- Features incomplete by design, including CSV/PDF export/import if not implemented.
- Whether the MVP is ready to demonstrate, with caveats.

Never say “all tests pass” unless the tests ran and passed. If a step could not be run, mark it NOT RUN and explain why. Begin execution now.
