from typing import Final

PRODUCT_NAME: Final = "Duki"
API_TITLE: Final = f"{PRODUCT_NAME} API"
LOGGER_NAME: Final = PRODUCT_NAME.casefold()
API_V1_PREFIX: Final = "/api/v1"
PRIMARY_CALENDAR_ID: Final = "primary"
OPENAI_API_BASE_URL: Final = "https://api.openai.com/v1"
GROQ_API_BASE_URL: Final = "https://api.groq.com/openai/v1"
DEFAULT_TRANSCRIPTION_PROVIDER: Final = "groq"
DEFAULT_OPENAI_TRANSCRIPTION_MODEL: Final = "gpt-4o-transcribe"
DEFAULT_GROQ_TRANSCRIPTION_MODEL: Final = "whisper-large-v3-turbo"
DEFAULT_TASK_EXTRACTION_PROVIDER: Final = "groq"
DEFAULT_GROQ_TASK_EXTRACTION_MODEL: Final = "openai/gpt-oss-20b"
DEFAULT_OPENAI_TASK_EXTRACTION_MODEL: Final = "gpt-5.6-luna"
