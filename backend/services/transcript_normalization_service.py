import re

from backend.errors import NoSpeechDetectedError
from backend.models.duck_sessions import NormalizedTranscript, RawTranscript

_FILLER_WORDS = re.compile(r"\b(?:um+|uh+|erm+|hmm+)\b[,\s]*", re.IGNORECASE)
_WHITESPACE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCTUATION = re.compile(r"\s+([,.!?;:])")


class TranscriptNormalizationService:
    """Normalize transcript mechanics without changing the user's meaning."""

    def normalize(self, transcript: RawTranscript) -> NormalizedTranscript:
        text = _FILLER_WORDS.sub("", transcript.text)
        text = _WHITESPACE.sub(" ", text).strip()
        text = _SPACE_BEFORE_PUNCTUATION.sub(r"\1", text)
        if not text:
            raise NoSpeechDetectedError("No meaningful speech was detected")
        if text[-1] not in ".!?":
            text = f"{text}."
        return NormalizedTranscript(text=text)
