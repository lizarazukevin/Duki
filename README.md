# Duki
Maximize productivity with mood-based task management and a bright yellow rubber duck.

## Backend feature flags

Task endpoints are private and disabled by default. Set `TASKS_ENABLED=true` in the
backend run configuration to enable them.

Voice transcription uses Groq-hosted Whisper by default, while task extraction uses
another free model initially. Set `DUCK_SESSIONS_ENABLED=true`, `GROQ_API_KEY`, and `OPENAI_API_KEY` in the
backend run configuration. `TRANSCRIPTION_PROVIDER=openai` switches transcription back
to OpenAI without an automatic fallback. `GROQ_TRANSCRIPTION_MODEL`,
`OPENAI_TRANSCRIPTION_MODEL`, and `OPENAI_TASK_EXTRACTION_MODEL` may override their
default models when needed. Enable Zero Data Retention in Groq Data Controls before
processing user audio outside local development.
