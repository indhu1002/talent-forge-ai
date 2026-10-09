# Talent Forge AI

A full-stack recruitment platform built with React, Django REST Framework, MySQL support and JWT authentication.

Candidates can manage resumes, analyze a resume against a specific job description, receive proposed edits, and prepare for interviews. Recruiters can publish jobs and manage applications. Administrators can manage workspace roles.

## Features

- Three roles: candidate, recruiter and administrator.
- JWT authentication, token refresh rotation, refresh-token blacklisting and password validation.
- Private PDF resume uploads and text extraction.
- Local resume scoring across 18 transparent criteria.
- Resume builder with live preview, save/analyze and browser PDF export.
- Skill-based job matching, applications and recruiter status updates.
- Analytics based on actual stored data.
- OpenAI-powered JD coaching with requirement evidence, gaps and proposed resume rewrites.
- 20 tailored practice questions with sample answers and follow-ups: 6 technical, 4 project, 4 behavioral, 4 scenario and 2 HR.
- Five-day preparation plans, private saved reports and text export.
- Responsive candidate and recruiter workspaces.

Resume scores describe presentation and keyword evidence. Job matching measures skill overlap. These are guidance tools, not hiring decisions or predictions of candidate ability. The project's claimed 60% screening-time reduction has not been benchmarked.

## Requirements

- Python 3.14.
- Node.js and npm.
- MySQL 8+ for the MySQL configuration; SQLite is available for local development.
- An OpenAI API key and available API quota for AI-generated JD reports.

## Quick start

Clone this repository, then run:

    cd backend
    python -m venv .venv

Activate the environment:

Windows PowerShell:

    .\.venv\Scripts\Activate.ps1

macOS/Linux:

    source .venv/bin/activate

Install dependencies, initialize the database and create local demo accounts:

    python -m pip install -r requirements.txt
    python manage.py migrate
    python manage.py seed_demo
    python manage.py runserver 127.0.0.1:8000

In a second terminal:

    cd frontend
    npm ci
    npm run dev

Open http://localhost:5173. Demo usernames are candidate, recruiter and administrator. The generated local demo password is written to backend/DEMO-CREDENTIALS.txt, which is excluded from Git. Demo jobs are illustrative, and no real resumes or database contents are included in this repository.

Without backend/.env, the app uses SQLite and local analysis. To configure AI or MySQL, copy backend/.env.example to backend/.env and edit its values. Never commit that file.

## MySQL

Create a dedicated database and application user, then configure backend/.env:

    DB_ENGINE=mysql
    MYSQL_DATABASE=talentforge
    MYSQL_USER=talentforge
    MYSQL_PASSWORD=your-private-database-password
    MYSQL_HOST=127.0.0.1
    MYSQL_PORT=3306

Apply migrations with python manage.py migrate after changing the database. MySQL test execution also needs permissions on test_talentforge.

For Docker MySQL, copy the root .env.example to .env, set strong unique database/root passwords, and run:

    docker compose up -d

Configure matching values in backend/.env. Docker Compose binds MySQL to loopback port 3306; change the host port if it is already occupied.

## AI setup

Set these values in backend/.env and restart Django:

    OPENAI_API_KEY=your-private-api-key
    OPENAI_MODEL=gpt-5.6-terra
    CAREER_AI_MODEL=gpt-5.6-terra

Candidate users open JD & interview, select or upload a resume, paste a JD and agree to send the selected text to OpenAI before generating a report. API usage may incur charges. Reports run in the background and remain private to their owner, including after a resume is shared through an application.

The Responses API uses structured output and store=false. Provider responses are validated before being marked successful. Unverified requirement evidence is marked unevidenced; edits with an unverified source excerpt require confirmation. Each report includes a resume snapshot. Refreshing/viewing an existing report does not start another provider request.

Suggestions do not change the original resume. Verify every statement and replace bracketed placeholders with truthful details. Unsupported skills are development targets, not qualifications to claim. Interview questions are realistic practice predictions; actual questions cannot be guaranteed. Practice notes stay in the current page and are not persisted.

Generic resume AI feedback is separately enabled by ENABLE_AI_FEEDBACK=1. Local 18-criterion scoring works without a key.

If OpenAI returns HTTP 429, check API billing, credits and rate limits. Credential presence alone does not confirm provider access. The initial live tests encountered HTTP 429; a successful live provider report has not yet been verified. The complete report UI was validated with an explicitly labeled test fixture, not a substitute AI report.

## Windows helpers

- Setup-TalentForge.ps1: install dependencies, apply migrations and seed demo accounts.
- Start-TalentForge.ps1 / Stop-TalentForge.ps1: start/stop local development servers.
- Restart-Backend.ps1: restart Django after changing configuration.
- Set-OpenAIKey.ps1: enter an API key locally with masked input.

The start/stop helpers can manage a project-local MySQL instance on port 3307 when configured and initialized on Windows. That machine-specific data directory and its passwords are excluded from this repository. Other users should use SQLite, an existing MySQL database or Docker Compose.

## Tests and build

Backend:

    cd backend
    python manage.py check
    python manage.py test recruitment

Frontend:

    cd frontend
    npm ci
    npm run build

30 backend tests cover authentication, token rotation/logout, role and ownership permissions, PDF validation/extraction, applications, report privacy/consent, background workers, structured provider output, evidence verification and provider failure handling. Automated browser checks exercised the report UI using isolated fixtures. CI runs the backend suite on SQLite and builds the frontend.

## API

Routes begin with /api/. Authenticated requests use Authorization: Bearer <access-token>.

| Route | Purpose |
| --- | --- |
| auth/register/, auth/login/, auth/refresh/, auth/logout/, auth/me/ | Authentication |
| resumes/, resumes/{id}/, resumes/{id}/download/ | Private resume management |
| jobs/, jobs/{id}/, jobs/matches/?resume={id} | Job management and matching |
| applications/, applications/{id}/ | Applications and recruiter status |
| analytics/ | Role-scoped analytics |
| users/ | Administrator role management |
| career-config/ | Model/configuration presence, never the API key |
| career-reports/, career-reports/{id}/ | Private JD coaching reports |

## Production hosting

Uploading this repository to GitHub publishes the source; it does not run Django, MySQL or the complete application. GitHub Pages alone cannot host the backend.

For deployment, configure DEBUG=0, a unique SECRET_KEY, allowed hosts, CORS, HTTPS, a production WSGI server, database backups and a reverse proxy. Serve frontend/dist and proxy same-origin /api to Django. The Vite proxy is for local development only.

Replace demo accounts and establish resume consent, retention and deletion policies. Use a durable background task queue instead of the development thread pool, and centralized throttling/cache for multiple workers. JWTs currently use sessionStorage; consider HttpOnly-cookie handling as part of production hardening. The development build has not undergone a production security audit.

## References

- [Django REST Framework permissions](https://www.django-rest-framework.org/api-guide/permissions/)
- [Simple JWT blacklisting](https://django-rest-framework-simplejwt.readthedocs.io/en/stable/blacklist_app.html)
- [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [OpenAI API error codes](https://developers.openai.com/api/docs/guides/error-codes)