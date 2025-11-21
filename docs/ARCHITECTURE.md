# Architecture Overview

This document captures the current state of the ProbeTect architecture so new contributors can ramp up quickly.

## High-Level Flow
1. Anonymous visitors land on the marketing site (`blog` app) rendered from `templates/blog/home.html`.
2. Users register or log in through views in the `accounts` app, powered by the custom `User` model with role support.
3. Authenticated users access the dashboard and PDF upload experience (served by `accounts` and `materials`).
4. Uploaded PDFs are validated, stored in Supabase Storage, and tracked via the `Material` model.
5. Students or instructors trigger quiz generation from a material card; the system extracts text from Supabase, calls Gemini, and persists questions in the `quizzes` app.
6. Instructors create classes with join codes, assign quizzes to those classes, or generate direct share links for one-off access.
7. Students join classes (or use share links), take assignments, and submissions are graded server-side with attempts tracked for reporting.

## Applications
- **accounts**
  - Extends `AbstractUser` with a `role` enum and helper methods.
  - Provides signup, login (with email aliases), logout, and a lightweight dashboard view.
  - Custom admin registration exposes role management in Django admin.
- **materials**
  - Model: `Material` stores metadata, status, and storage location for each upload.
  - Forms: `MaterialUploadForm` performs file validation with Tailwind-friendly widgets.
  - Views: `MaterialUploadView` coordinates form handling, Supabase integration, flash messaging, and recent uploads list.
  - Supabase helpers: `_get_config`, `upload_file`, `download_file`, and `delete_file` abstract REST calls using environment variables.
- **quizzes**
  - Models: `Quiz` captures quiz metadata, status, and source `Material`; `QuizQuestion` stores prompts, choices, answers, and explanations; `QuizShareLink` enables direct quiz sharing with active tokens; `QuizAttempt` records scored submissions from assignments or share links.
  - Views: `GenerateQuizView` orchestrates quiz creation, `QuizListView` lists a user's quizzes (optionally filtered per material), `QuizDetailView` renders the owner-only take-and-score flow, `SharedQuizTakeView` handles token-based access, and export views generate PDF/DOCX copies.
  - Services: `services.py` handles text extraction from PDFs, prompt construction, Gemini API interaction, and JSON parsing with robust error handling; `utils.py` grades quiz submissions.
- **classrooms**
  - Models: `Classroom` (owned by instructors) issues join codes; `ClassroomMembership` tracks enrolled students; `QuizAssignment` links ready quizzes to a classroom with optional due dates and answer visibility.
  - Views: list/create/join flows for classes, class detail with members and assignments, assignment creation from either a quiz or a class, and assignment take pages that grade and store attempts.
- **lessons**
  - Lesson planning tools for instructors to track lesson content tied to materials; includes list/create/edit/delete views and a form for associating a `Material`.
- **blog**
  - Single `landing` view for the marketing homepage.
  - Templates present product messaging and call-to-actions while sharing the global layout.

## Settings & Configuration
- `mysite/settings.py` loads environment variables via `dotenv`, configures `dj_database_url` for Postgres/Supabase, and declares the custom `AUTH_USER_MODEL`.
- Gemini configuration is sourced from `GEMINI_API_KEY` and `GEMINI_MODEL` (defaulting to `gemini-2.5-flash`).
- Static assets: `STATICFILES_DIRS` points to `static/` for Tailwind CSS overrides. Use `collectstatic` during deployment.
- Media uploads: handled externally through Supabase; local `MEDIA_ROOT` exists for future use.

## Data Model Snapshot
- `accounts.User`
  - Inherits built-in username/email auth fields.
  - Adds `role` (`student` or `instructor`) to drive conditional UI and permissions.
- `materials.Material`
  - ForeignKey to `User` (owner).
  - Metadata fields: `title`, `subject`, `description`, `visibility`, `status`, file properties, timestamps.
  - `save()` auto-populates `storage_path` and title fallback from `original_filename`.
- `quizzes.Quiz`
  - ForeignKey to `User` (owner) and `Material` (source document).
  - Tracks status (`pending`, `processing`, `ready`, `error`), question count, Gemini model, and any error message.
- `quizzes.QuizQuestion`
  - ForeignKey to `Quiz`.
  - Stores the prompt, optional multiple-choice array, canonical answer, explanation, and ordering index.
- `classrooms.Classroom`
  - ForeignKey to `User` (owner) with a generated join `code`.
  - Name/description plus timestamps for class management.
- `classrooms.ClassroomMembership`
  - Links a `User` to a `Classroom` with a `role` (student by default).
- `classrooms.QuizAssignment`
  - Bridges a ready `Quiz` to a `Classroom` with optional due date and answer visibility toggle.
- `quizzes.QuizShareLink`
  - Tokenized link for sharing a quiz outside classes; includes active flag and creator.
- `quizzes.QuizAttempt`
  - Records graded submissions with score/percent, answers payload, and optional links to a `QuizAssignment` or `QuizShareLink`.

## AI & External Services
- **Supabase Storage** stores original PDFs; paths and public URLs live on each `Material` record.
- **Gemini 2.5 Flash** powers quiz generation via the `call_gemini` service function. Requests include extracted PDF text, and responses are normalized to strict JSON before persistence.

## Future Directions
- Background workers for long-running quiz generation and progress updates (transitioning quiz status off the request thread).
- Lesson planning features that aggregate quiz results to suggest study sessions.
- Instructor dashboards that surface class-level quiz performance using stored attempts and assignments.
- Storage lifecycle policies to purge Supabase files when materials or quizzes are deleted.

Keep `DOCS_UPDATES.md` in sync as these areas evolve.
