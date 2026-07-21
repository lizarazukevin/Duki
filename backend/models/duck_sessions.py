from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from backend.models.tasks import EasinessSource, TaskCategory

MAX_TRANSCRIPT_CHARACTERS = 100000
MAX_TASK_TREE_DEPTH = 8
MAX_EXTRACTED_TASKS = 100


class DuckSessionStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RawTranscript:
    """Unprocessed provider-neutral transcription text."""

    text: str

    def __post_init__(self) -> None:
        _validate_transcript(self.text)


@dataclass(frozen=True, slots=True)
class NormalizedTranscript:
    """Transcript text normalized by the dedicated transcript service."""

    text: str

    def __post_init__(self) -> None:
        _validate_transcript(self.text)


@dataclass(frozen=True, slots=True)
class ExtractedTask:
    """A provider-neutral task draft extracted from a transcript."""

    title: str
    description: str | None
    category: TaskCategory
    estimated_minutes: int | None
    initial_easiness_score: int | None
    easiness_source: EasinessSource | None
    children: tuple[ExtractedTask, ...]

    def __post_init__(self) -> None:
        if not self.title.strip() or len(self.title) > 500:
            raise ValueError("Extracted task title is invalid")
        if self.description is not None and len(self.description) > 10000:
            raise ValueError("Extracted task description is too long")
        if self.estimated_minutes is not None and self.estimated_minutes <= 0:
            raise ValueError("Extracted task estimate must be positive")
        score = self.initial_easiness_score
        if score is not None and not 1 <= score <= 5:
            raise ValueError("Extracted easiness score must be between 1 and 5")
        if (score is None) != (self.easiness_source is None):
            raise ValueError("Extracted easiness score and source must be provided together")


@dataclass(frozen=True, slots=True)
class ExtractedTaskTree:
    root: ExtractedTask

    def __post_init__(self) -> None:
        task_count = 0

        def validate_depth(task: ExtractedTask, depth: int) -> None:
            nonlocal task_count
            task_count += 1
            if task_count > MAX_EXTRACTED_TASKS:
                raise ValueError("Extracted task tree contains too many tasks")
            if depth > MAX_TASK_TREE_DEPTH:
                raise ValueError("Extracted task tree is too deeply nested")
            for child in task.children:
                validate_depth(child, depth + 1)

        validate_depth(self.root, 1)


@dataclass(frozen=True, slots=True)
class DuckSession:
    id: UUID
    user_id: UUID
    status: DuckSessionStatus
    transcript: str | None
    root_task_id: UUID | None
    failure_code: str | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.transcript is not None:
            _validate_transcript(self.transcript)
        if self.failure_code is not None and not 1 <= len(self.failure_code) <= 100:
            raise ValueError("Duck session failure code is invalid")
        if self.status is DuckSessionStatus.PROCESSING:
            if self.root_task_id or self.failure_code or self.finished_at:
                raise ValueError("Processing duck session has terminal state")
        elif self.status is DuckSessionStatus.COMPLETED:
            if self.transcript is None or self.failure_code is not None or self.finished_at is None:
                raise ValueError("Completed duck session is missing its result")
        elif self.root_task_id or self.failure_code is None or self.finished_at is None:
            raise ValueError("Failed duck session is missing failure state")


def _validate_transcript(text: str) -> None:
    if not text.strip():
        raise ValueError("Transcript cannot be blank")
    if len(text) > MAX_TRANSCRIPT_CHARACTERS:
        raise ValueError("Transcript exceeds the storage limit")
