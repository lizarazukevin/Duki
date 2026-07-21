# Duki
Maximize productivity with mood-based task management and a bright yellow rubber duck.

## Backend feature flags

Task endpoints are private and disabled by default. Set `TASKS_ENABLED=true` in the
backend run configuration to enable them.

Daily mood endpoints are private and disabled by default. Set `MOODS_ENABLED=true` in
the backend run configuration to enable calendar-aware mood tracking.

Voice transcription and structured task extraction use Groq's free-plan models by
default. Set `DUCK_SESSIONS_ENABLED=true` and `GROQ_API_KEY` in the backend run
configuration. `TRANSCRIPTION_PROVIDER=openai` or `TASK_EXTRACTION_PROVIDER=openai`
switches that individual stage to OpenAI without an automatic fallback.
`GROQ_TRANSCRIPTION_MODEL`, `GROQ_TASK_EXTRACTION_MODEL`,
`OPENAI_TRANSCRIPTION_MODEL`, and `OPENAI_TASK_EXTRACTION_MODEL` may override their
default models when needed. Enable Zero Data Retention in Groq Data Controls before
processing user audio outside local development.
