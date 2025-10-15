# ProbeTect
 
ProbeTect is a Django 5.2 web app that helps students and instructors turn course PDFs into practice quizzes, feedback, and lesson-planning prompts. Upload a file, we store it in Supabase, generate quiz content with Google Gemini, and surface everything through a Tailwind-powered dashboard.
 
Key capabilities:
- PDF upload queue with Supabase-backed storage and extraction via `pypdf`.
- Quiz generation that enforces a strict JSON schema and repairs malformed responses automatically.
- Dashboard for managing materials, reviewing generated quizzes, and downloading results.
- Progress indicators and accessibility touches (skip links, keyboard-friendly navigation).
 
## Tech Stack
- **Backend:** Python 3.11+, Django 5.2, PostgreSQL (via `DATABASE_URL`), Supabase storage helpers, Google Gemini API.
- **Frontend:** Tailwind CSS (delivered through CDN), HTMX-lite interactivity with Django templates, vanilla JS enhancements.
- **Supporting Tools:** `pypdf` for PDF parsing, `python-dotenv` for config loading, GitHub Actions (planned) for CI.
 
## Setup & Run
1. **Clone & environment:**  
   ```bash
   git clone <repo-url>
   cd ProbeTect
   python -m venv .venv
   .venv\Scripts\activate  # or source .venv/bin/activate on macOS/Linux
   ```
2. **Install dependencies:**  
   ```bash
   pip install -r requirements.txt
   ```
3. **Environment variables:** copy the template and set secrets.
   ```bash
   cp .env.example .env
   ```
   Required values:
   - `DATABASE_URL` – Postgres connection string.
   - `SUPABASE_URL`, `SUPABASE_KEY` – Supabase project credentials.
   - `SUPABASE_BUCKET` – bucket name for stored PDFs.
   - `GEMINI_API_KEY` – Google Generative Language API key.
4. **Database:**  
   ```bash
   python manage.py migrate
   ```
5. **Development server:**  
   ```bash
   python manage.py runserver
   ```
6. **Optional checks:**  
   ```bash
   python manage.py check
   python manage.py test
   ```
 
## Team Members
| Name | Role | CIT-U Email |
| --- | --- | --- |
| John Lawrence C. Regis | Product Owner | johnlawrence.regis@cit.edu |
| Elijah Thomas N. Rellon | Business Analyst | elijahthomas.rellon@cit.edu |
| Jeremiah T. Ramos | Scrum Master | jeremiah.ramos@cit.edu |
| Kurt David M. Monteclaro | Lead Developer | kurtdavid.monteclaro@cit.edu |
| Dilton Rowan S. Morales | Junior Developer | diltonrowan.morales@cit.edu |
| Primo Christian C. Montejo | Junior Developer | primochristian.montejo@cit.edu |
 
## Deployment
No public deployment yet. Once a test or production environment is live we will list the URL and access notes here.