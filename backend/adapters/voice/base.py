from collections.abc import AsyncIterable
from typing import Protocol

from backend.models.duck_sessions import RawTranscript


class VoiceAdapter(Protocol):
    """Port for streaming audio transcription without retaining the audio."""

    async def transcribe(
        self,
        audio_chunks: AsyncIterable[bytes],
        media_type: str,
    ) -> RawTranscript: ...
