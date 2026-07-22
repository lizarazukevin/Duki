[![Python](https://img.shields.io/badge/python-3.14%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js)](https://nextjs.org)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3FCF8E?logo=supabase&logoColor=white)](https://supabase.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

<h1 align="center">
  <img src="frontend/public/images/duky-3d.webp" alt="Duky, a yellow rubber duck" width="180" />
  <br>Duky
</h1>
<p align="center">
  A mood-aware productivity companion built around a bright yellow rubber duck.
  <br />
  Talk through the work, find a realistic place for it, and learn from what actually happened.
  <br />
  <a href="#about">About</a>
  ·
  <a href="#quickstart">Quickstart</a>
  ·
  <a href="#features">Features</a>
  ·
  <a href="#how-codex-and-gpt-56-were-used">Codex</a>
  ·
  <a href="#contributing-and-development">Development</a>
  ·
  <a href="#roadmap">Roadmap</a>
</p>

---

## About

Task lists usually assume every hour and every day feel the same. They collect work,
but they do not help when the task is still vague, the calendar is already crowded,
or the person doing it has very little energy left.

Duky starts with the way people actually think: out loud and imperfectly. Talk to the
duck about a project or an ad hoc debrief, and Duky turns the transcript into structured
tasks or suggested resolutions. It combines those tasks with the connected primary
Google Calendar and a daily energy check-in to suggest a plan that fits the time and
attention available.

When work is finished, Duky records the actual time and easiness alongside the original
estimate. The user keeps the final say throughout: extracted work, debrief resolutions,
calendar placement, and completion feedback are all reviewable actions.

> **Status:** Active development. The core authenticated daily loop is working locally.
> See the [Roadmap](#roadmap) for what has landed and what comes next.

## Quickstart

Running the complete app locally requires a Supabase project, Google OAuth credentials,
and a Groq API key when voice transcription or task extraction is enabled. Configuration
comes from environment variables in the shell, IDE run configuration, or deployment
provider; Duky does not require a dotenv file.

**1. Install the pinned runtimes and dependencies**

```bash
mise install
mise exec -- python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"

cd frontend
mise exec -- npm install
cd ..
```

**2. Prepare Supabase** – Run the files in [`supabase/migrations`](supabase/migrations)
in numeric order. Enable the Google provider and allow
`http://localhost:3000/auth/callback` in the Supabase Auth redirect URL list.

**3. Configure the applications** – Add the variables from
[Running locally](#running-locally) to the backend and frontend run configurations.

**4. Start both processes**

```bash
# Terminal 1 — API
.venv/bin/python backend/main.py

# Terminal 2 — web app
cd frontend
mise exec -- npm run dev
```

Open [http://localhost:3000](http://localhost:3000), sign in with Google, and Duky will
return to the authenticated home screen.

| Setup action | Link |
|---|---|
| Create or open the database and Auth project | [Supabase Dashboard](https://supabase.com/dashboard) |
| Configure the Google OAuth client | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| Create the voice and extraction API key | [Groq Console](https://console.groq.com/keys) |

## Features

**Talk tasks into shape.** Upload or record an audio note and Duky uses provider-neutral
transcription and structured extraction adapters to turn it into a task tree. Groq-hosted
Whisper and task extraction are the defaults; OpenAI adapters remain available.

**Debrief without pretending the plan was perfect.** A duck session can match completed
work to an open task, keep it open, archive it, or capture unplanned work as something
new. Nothing changes until the user confirms the suggestions.

**Plan around real calendar space.** Duky reads cached events from the connected primary
Google Calendar, finds usable gaps, and ranks estimated tasks using deadlines and the
day's energy. A suggestion can be written directly to Google without leaving Duky.

**Keep calendar edits connected.** Once a task has a Google Calendar event, Duky stores
the relationship. Later edits update that exact event and refresh the in-app timeline
instead of creating title-based duplicates.

**Treat energy as part of the plan.** A daily 1–5 check-in is combined with calendar
shape so low-energy days can favor shorter or easier work and clearer days can surface
more demanding tasks.

**Learn from completion.** Marking a task complete captures actual time and easiness,
preserving both alongside the original estimates for future analysis.

**Focus with the duck.** Focus mode keeps the current priority and an interactive Duky
front and center with a pauseable timer and browser-level attention nudges.

**See one private workspace.** Tasks, Calendar, Insights, and Profile sit behind Google
sign-in. User data is isolated with Supabase Row Level Security, and provider credentials
are encrypted before persistence.

### Daily loop

| Step | What Duky does |
|---|---|
| Check in | Records today's energy and considers the shape of the calendar. |
| Capture | Turns typed or spoken thoughts into structured tasks and goals. |
| Plan | Fits estimated work into open primary-calendar blocks. |
| Focus | Keeps one priority visible in focused duck mode. |
| Complete | Records actual time and easiness against the original estimate. |
| Debrief | Suggests resolutions for planned and unplanned work, then waits for confirmation. |

## How Codex and GPT-5.6 were used

> 📋 **This README has setup instructions and explains how Codex and GPT-5.6 were used.**

[Codex](https://developers.openai.com/codex/overview) with
[GPT-5.6](https://developers.openai.com/api/docs/models/gpt-5.6-sol) was used as a
development collaborator throughout Duky's design and implementation. It helped inspect
the PRD and roadmap, divide work into reviewable changes, propose the ports-and-adapters
backend structure, implement backend and frontend features, diagnose integration
failures, and run the project's formatting, linting, type-checking, test, and
production-build commands.

The developer reviewed changes and retained control of environment configuration,
database migrations, live provider credentials, manual product testing, and every Git
commit. Codex did not commit or deploy changes on the developer's behalf.

Codex and GPT-5.6 are development tools, not runtime dependencies of Duky. The running
application does not call Codex, and end-user task, mood, calendar, or transcript data is
not automatically sent to Codex. Runtime transcription and structured task extraction
use the explicitly configured Groq or OpenAI adapters described below.

## Contributing and development

Duky is a monorepo with a FastAPI backend and a Next.js frontend. Backend workflows use
ports and adapters: routers validate HTTP input, services orchestrate work, adapters
translate external APIs, and repositories own persistence. Frontend code is organized by
feature so each product surface owns its API contract, state, and presentation.

Before opening a pull request, run the existing quality checks:

```bash
# Backend
.venv/bin/ruff format --check backend
.venv/bin/ruff check backend
.venv/bin/mypy backend
.venv/bin/python -m unittest discover -s backend/tests -p "test_*.py"

# Frontend
cd frontend
mise exec -- npm run check
mise exec -- npm run test
mise exec -- npm run build
```

### Running locally

The pinned toolchain is Python 3.14 and Node.js 24 through
[`mise.toml`](mise.toml). Supabase provides Auth, Postgres, PostgREST, and RLS. Google
OAuth provides Calendar access, and Groq provides the default free-plan-compatible voice
and extraction models subject to the provider's current quotas.

Backend variables for the full local application:

| Variable | Required | Description |
|---|---|---|
| `APP_ENV` | No | `local` enables local API documentation. Defaults to `local`. |
| `AUTH_ENABLED` | Yes | Set to `true` for Google sign-in and session exchange. |
| `CALENDAR_SYNC_ENABLED` | Yes | Set to `true` for primary-calendar reads and writes. |
| `TASKS_ENABLED` | Yes | Set to `true` for private task and goal workflows. |
| `DUCK_SESSIONS_ENABLED` | Yes | Set to `true` for voice capture and ad hoc debriefs. |
| `MOODS_ENABLED` | Yes | Set to `true` for daily energy check-ins. |
| `SCHEDULER_ENABLED` | Yes | Set to `true` for mood-aware daily plans. |
| `SUPABASE_URL` | Yes | Supabase project URL. |
| `SUPABASE_PUBLISHABLE_KEY` | Yes | Browser-safe project key used by the auth flow. |
| `SUPABASE_SECRET_KEY` | Yes | Server-only key used for private persistence. Never expose it to the frontend. |
| `GOOGLE_OAUTH_CLIENT_ID` | Yes | OAuth client ID from Google Cloud. |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes | OAuth client secret from Google Cloud. |
| `CREDENTIAL_ENCRYPTION_KEYS` | Yes | Comma-separated Fernet keys; the first encrypts and the rest allow rotation. |
| `GROQ_API_KEY` | For voice | Groq key used by the default transcription and extraction providers. |
| `ALLOWED_OAUTH_REDIRECT_HOSTS` | No | Allowed callback hosts. Defaults to `localhost,127.0.0.1`. |
| `ALLOWED_CORS_ORIGINS` | No | Allowed frontend origins. Defaults to both local port-3000 origins. |

Generate a local credential-encryption key with:

```bash
.venv/bin/python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Frontend variables:

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | Backend origin, such as `http://127.0.0.1:8000`. |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL. |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Yes | Browser-safe Supabase publishable key. |

Optional provider overrides are available through `TRANSCRIPTION_PROVIDER`,
`TASK_EXTRACTION_PROVIDER`, `GROQ_TRANSCRIPTION_MODEL`, `GROQ_TASK_EXTRACTION_MODEL`,
`OPENAI_API_KEY`, `OPENAI_TRANSCRIPTION_MODEL`, and `OPENAI_TASK_EXTRACTION_MODEL`.
Enable Zero Data Retention in Groq Data Controls before processing real user audio
outside local development.

## Roadmap

#### Shipped

- [x] Supabase Google sign-in with offline Calendar consent and encrypted credentials.
- [x] Private primary-calendar sync, free-block discovery, direct event creation, and linked updates.
- [x] Hierarchical tasks, goals, grouping, search, deadlines, estimates, and completion feedback.
- [x] Provider-neutral voice transcription and structured task extraction with Groq defaults.
- [x] User-confirmed ad hoc debriefs with open-task matching and duplicate prevention.
- [x] Daily energy check-ins and deadline-aware scheduling into real calendar gaps.
- [x] Mobile-first Home, Tasks, Calendar, Insights, Profile, and focused duck views.

#### In progress

- [ ] Production deployment and end-to-end environment verification.
- [ ] Read-side analytics that turn completion and mood history into durable weekly trends.
- [ ] Expanded duck affirmations, nudges, and evening boundary-setting messages.

#### Planned

- [ ] Multi-calendar discovery and user-selected planning calendars.
- [ ] Local event and lighter-task break recommendations.
- [ ] Automated background calendar refresh.
- [ ] Native mobile focus controls beyond the browser's fullscreen and blur signals.

The detailed delivery sequence lives in [`ROADMAP.md`](ROADMAP.md), and product intent
lives in [`PRD.md`](PRD.md).

## License

MIT, © 2026 Kevin Lizarazu-Ampuero. See [LICENSE](LICENSE).
