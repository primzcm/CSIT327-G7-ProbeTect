# Documentation & Changes Log

Record of notable changes to code and docs. Add entries with date, scope, and brief summary.

## 2025-11-22 - Classrooms & quiz sharing

- Classrooms: Added a new app with class creation for instructors, join-by-code for students, and class detail pages.
- Assignments: Instructors can assign any ready quiz to a class and students can take it from the assignment view; timers are supported.
- Direct share: Instructors can generate or disable share links so students can take quizzes without joining a class.
- Models/Admin: Introduced `Classroom`, `ClassroomMembership`, `QuizAssignment`, `QuizShareLink`, and `QuizAttempt` with admin registration and migrations.
- Docs/UI: New Classes nav item plus architecture doc updated to describe the classroom/assignment/sharing flow.

## 2025-11-10 - Quiz option contrast

- Quizzes: Restyled the option radio inputs so the selected state uses a blue inner dot while ensuring unselected circles remain light for clarity in both themes.
- Marketing site: Matched the dark-mode background transition for the "From upload to insight" section with the light-mode layout so the color shift happens at the same scroll position.
- Marketing site: Boosted the contrast of the step-number pills in the same section so the numerals stay as visible in dark mode as they are in light mode.
- Marketing site: Rewrote the hero “Sample PDF” card to describe the actual ProbeTect pipeline (Supabase storage, pypdf extraction, Gemini quiz generation) instead of placeholder metrics.
- Marketing site: Restored the classic sample card layout (Outline, Quiz Preview, Insights) but kept the realistic pipeline details so the content matches the product, then tightened the copy/file naming so the card stays readable in both themes and clarified the “extra variants” and storage labels.

## 2025-11-10 - Dark mode + richer profiles

- UI: Added a persistent light/dark toggle in the global chrome, themed the header/footer/cards, and layered CSS overrides so every page respects the selected scheme.
- Accounts: Expanded the profile page with learning-focus fields, usage stats, optional photo upload w/ validation, and success messaging.
- Models: Introduced optional `headline`, `bio`, and `profile_photo` fields on the custom `User` plus admin exposure; created the accompanying migration.
- Dependencies: Added Pillow 11 to requirements for avatar validation and documented the new capability in the README.

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


