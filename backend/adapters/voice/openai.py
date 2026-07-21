import httpx

from backend.adapters.voice.openai_compatible import OpenAICompatibleVoiceAdapter
from backend.constants import DEFAULT_OPENAI_TRANSCRIPTION_MODEL, OPENAI_API_BASE_URL


class OpenAIVoiceAdapter(OpenAICompatibleVoiceAdapter):
    """Configure the shared transcription transport for OpenAI."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        model: str = DEFAULT_OPENAI_TRANSCRIPTION_MODEL,
    ) -> None:
        super().__init__(http_client, api_key, model, OPENAI_API_BASE_URL)
