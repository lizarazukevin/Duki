# Duky
Maximize productivity with mood-based task management and a bright yellow rubber duck.

## Authenticated app

The browser app now provides dedicated Tasks, Calendar, Insights, and Profile views
behind the existing Google sign-in. Calendar reads the connected primary Google
calendar and can save a suggested task there without leaving Duky. Later task edits
update that same calendar event, and the event appears immediately in Duky's timeline.
Mood check-ins shape deadline-aware daily suggestions, and voice uploads support both
task capture and microphone-first ad hoc debriefs. Home also includes a focused Duky
timer for staying with one task. Insights reports only metrics supported by current
data, and Profile keeps unpersisted preferences clearly marked as unavailable.

## Backend feature flags

Task endpoints are private and disabled by default. Set `TASKS_ENABLED=true` in the
backend run configuration to enable them.

Daily mood endpoints are private and disabled by default. Set `MOODS_ENABLED=true` in
the backend run configuration to enable calendar-aware mood tracking.

Daily schedule plans are private and disabled by default. Set `SCHEDULER_ENABLED=true`
to rank tasks into free blocks from the primary Google calendar.

Voice transcription and structured task extraction use Groq's free-plan models by
default. Set `DUCK_SESSIONS_ENABLED=true` and `GROQ_API_KEY` in the backend run
configuration. `TRANSCRIPTION_PROVIDER=openai` or `TASK_EXTRACTION_PROVIDER=openai`
switches that individual stage to OpenAI without an automatic fallback.
`GROQ_TRANSCRIPTION_MODEL`, `GROQ_TASK_EXTRACTION_MODEL`,
`OPENAI_TRANSCRIPTION_MODEL`, and `OPENAI_TASK_EXTRACTION_MODEL` may override their
default models when needed. Enable Zero Data Retention in Groq Data Controls before
processing user audio outside local development.

Each duck session is an ad hoc debrief. It can return suggested `complete`,
`keep_open`, or `archive` actions for matching open tasks, but it does not change task
state until the user confirms those suggestions. Completed work that was not planned is
captured as a new task with its completion feedback preserved for confirmation.
Confirmation is single-use and applies every accepted or overridden decision together.
