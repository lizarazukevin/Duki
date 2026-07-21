import re
from collections.abc import AsyncIterable, AsyncIterator
from uuid import uuid4

import httpx

from backend.adapters.voice.base import VoiceAdapter
from backend.errors import (
    AudioTooLargeError,
    TranscriptionConfigurationError,
    TranscriptionError,
    TranscriptionRateLimitError,
    UnsupportedAudioTypeError,
)
from backend.models.duck_sessions import RawTranscript

MAX_AUDIO_BYTES = 25 * 1024 * 1024
TRANSCRIPTION_TIMEOUT_SECONDS = 90.0
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]+$")
_AUDIO_FILE_EXTENSIONS = {
    "audio/m4a": "m4a",
    "audio/mp4": "mp4",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/webm": "webm",
    "audio/x-m4a": "m4a",
    "audio/x-wav": "wav",
    "video/mp4": "mp4",
    "video/webm": "webm",
}
_NETWORK_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError)


class OpenAICompatibleVoiceAdapter(VoiceAdapter):
    """Translate streamed audio through an OpenAI-compatible transcription API."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        model: str,
        api_base_url: str,
    ) -> None:
        if not api_key:
            raise ValueError("Transcription API key cannot be blank")
        if not _MODEL_PATTERN.fullmatch(model):
            raise ValueError("Transcription model identifier is invalid")
        self._http_client = http_client
        self._api_key = api_key
        self._model = model
        self._transcriptions_url = f"{api_base_url.rstrip('/')}/audio/transcriptions"

    async def transcribe(
        self,
        audio_chunks: AsyncIterable[bytes],
        media_type: str,
    ) -> RawTranscript:
        normalized_media_type = media_type.partition(";")[0].strip().lower()
        extension = _AUDIO_FILE_EXTENSIONS.get(normalized_media_type)
        if extension is None:
            raise UnsupportedAudioTypeError("The audio format is not supported")

        boundary = f"duky-{uuid4().hex}"
        try:
            response = await self._http_client.post(
                self._transcriptions_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                content=self._multipart_body(
                    audio_chunks=audio_chunks,
                    media_type=normalized_media_type,
                    extension=extension,
                    boundary=boundary,
                ),
                timeout=TRANSCRIPTION_TIMEOUT_SECONDS,
            )
        except _NETWORK_ERRORS as error:
            raise TranscriptionError("Audio transcription is unavailable") from error

        if response.status_code in {401, 403}:
            raise TranscriptionConfigurationError("Transcription is not authorized")
        if response.status_code == 429:
            raise TranscriptionRateLimitError("Audio transcription is rate limited")
        if response.status_code >= 400:
            raise TranscriptionError("Audio could not be transcribed")

        try:
            payload: object = response.json()
            if not isinstance(payload, dict):
                raise TypeError("Invalid transcription response")
            text = payload.get("text")
            if not isinstance(text, str):
                raise TypeError("Missing transcription text")
            return RawTranscript(text=text)
        except (TypeError, ValueError) as error:
            raise TranscriptionError("Transcription response is invalid") from error

    async def _multipart_body(
        self,
        *,
        audio_chunks: AsyncIterable[bytes],
        media_type: str,
        extension: str,
        boundary: str,
    ) -> AsyncIterator[bytes]:
        yield self._text_part(boundary, "model", self._model)
        yield self._text_part(boundary, "response_format", "json")
        yield (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="audio.{extension}"\r\n'
            f"Content-Type: {media_type}\r\n\r\n"
        ).encode("ascii")

        audio_size = 0
        async for chunk in audio_chunks:
            if not isinstance(chunk, bytes):
                raise TranscriptionError("Audio stream contained an invalid chunk")
            if not chunk:
                continue
            audio_size += len(chunk)
            if audio_size > MAX_AUDIO_BYTES:
                raise AudioTooLargeError("Audio cannot exceed 25 MB")
            yield chunk
        if audio_size == 0:
            raise TranscriptionError("Audio stream was empty")
        yield f"\r\n--{boundary}--\r\n".encode("ascii")

    @staticmethod
    def _text_part(boundary: str, name: str, value: str) -> bytes:
        return (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        ).encode("ascii")
