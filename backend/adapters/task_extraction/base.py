from typing import Protocol

from backend.models.duck_sessions import ExtractedTaskTree, NormalizedTranscript


class TaskExtractionAdapter(Protocol):
    """Port for converting normalized transcript text into a task tree."""

    async def extract_tasks(
        self,
        transcript: NormalizedTranscript,
        user_identifier: str,
    ) -> ExtractedTaskTree: ...
