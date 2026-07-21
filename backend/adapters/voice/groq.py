import httpx

from backend.adapters.voice.openai_compatible import OpenAICompatibleVoiceAdapter
from backend.constants import DEFAULT_GROQ_TRANSCRIPTION_MODEL, GROQ_API_BASE_URL


class GroqVoiceAdapter(OpenAICompatibleVoiceAdapter):
    """Configure the shared transcription transport for Groq-hosted Whisper."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        model: str = DEFAULT_GROQ_TRANSCRIPTION_MODEL,
    ) -> None:
        super().__init__(http_client, api_key, model, GROQ_API_BASE_URL)
