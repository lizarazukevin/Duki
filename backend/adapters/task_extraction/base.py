from collections.abc import Sequence
from typing import Protocol

from backend.models.duck_sessions import ExtractedTaskTree, NormalizedTranscript
from backend.models.tasks import Task


class TaskExtractionAdapter(Protocol):
    """Port for converting normalized transcript text into a task tree."""

    async def extract_tasks(
        self,
        transcript: NormalizedTranscript,
        user_identifier: str,
        open_tasks: Sequence[Task],
    ) -> ExtractedTaskTree: ...
