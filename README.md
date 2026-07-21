# Duki
Maximize productivity with mood-based task management and a bright yellow rubber duck.

## Backend feature flags

Task endpoints are private and disabled by default. Set `TASKS_ENABLED=true` in the
backend run configuration to enable them.

Voice transcription and task extraction use OpenAI. Set `OPENAI_API_KEY` in the backend
run configuration and `DUCK_SESSIONS_ENABLED=true` to enable the private voice pipeline.
`OPENAI_TRANSCRIPTION_MODEL` and `OPENAI_TASK_EXTRACTION_MODEL` may override the default
models when needed.
