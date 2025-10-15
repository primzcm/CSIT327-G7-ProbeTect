# Documentation & Changes Log

Record of notable changes to code and docs. Add entries with date, scope, and brief summary.

## 2025-10-15 - Landing page updates

- Landing: Took out the pricing buttons and the pricing section on the home page so the focus stays on the free workflow.
- Quizzes: When you click “Generate quiz” on the upload page, the button now shows a loading bar and disables itself until the request finishes.
- Accessibility: Added a “Skip to main content” shortcut for keyboard users, a quick note under the instructor sign-up button, and small badges on the feature cards while still loading Tailwind from the CDN script.

## 2025-09-27 - Quiz UX polish & Gemini update

- Quizzes: Added list/detail templates so users can view and take generated quizzes.
- Navigation: Linked quizzes into the main nav and material queue for quicker access.
- AI Config: Switched the default Gemini model to `gemini-2.5-flash` and updated environment settings.\n- Gemini JSON: Hardened the prompt with explicit schema instructions and added automatic comma repair for malformed payloads.
- Docs: Refreshed README architecture snapshot and architecture.md to document the new quiz pipeline.

## 2025-09-25 - Repository documentation overhaul

- Docs: Replaced the bare README with a full project overview, setup workflow, and created this changelog.
- Architecture: Added `docs/ARCHITECTURE.md` outlining the system at a high level.
- Conventions: Authored `AGENTS.md` covering automation practices, repo agreements, and moved it to the repo root.



