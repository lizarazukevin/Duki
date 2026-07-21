import asyncio
import logging
from collections.abc import AsyncIterable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

from backend.adapters.task_extraction.base import TaskExtractionAdapter
from backend.adapters.voice.base import VoiceAdapter
from backend.constants import LOGGER_NAME
from backend.errors import (
    DuckSessionPersistenceError,
    OpenAIConfigurationError,
    TaskExtractionError,
    TaskExtractionRateLimitError,
    TranscriptionError,
)
from backend.models.duck_sessions import (
    DuckSession,
    DuckSessionStatus,
    ExtractedTask,
    ExtractedTaskTree,
    NormalizedTranscript,
)
from backend.models.tasks import Task, TaskStatus
from backend.repositories.duck_sessions import DuckSessionRepository
from backend.services.transcript_normalization_service import TranscriptNormalizationService

TASK_EXTRACTION_ATTEMPTS = 2
TASK_EXTRACTION_RETRY_DELAY_SECONDS = 0.25

logger = logging.getLogger(LOGGER_NAME)


class DuckSessionService:
    """Orchestrate streamed transcription into an atomically persisted task tree."""

    def __init__(
        self,
        voice_adapter: VoiceAdapter,
        task_extraction_adapter: TaskExtractionAdapter,
        session_repository: DuckSessionRepository,
        transcript_normalization_service: TranscriptNormalizationService,
    ) -> None:
        self._voice_adapter = voice_adapter
        self._task_extraction_adapter = task_extraction_adapter
        self._session_repository = session_repository
        self._transcript_normalization_service = transcript_normalization_service

    async def process_audio(
        self,
        user_id: UUID,
        audio_chunks: AsyncIterable[bytes],
        media_type: str,
    ) -> DuckSession:
        started_at = datetime.now(UTC)
        session = DuckSession(
            id=uuid4(),
            user_id=user_id,
            status=DuckSessionStatus.PROCESSING,
            transcript=None,
            root_task_id=None,
            failure_code=None,
            finished_at=None,
            created_at=started_at,
            updated_at=started_at,
        )
        await self._session_repository.create_session(session)

        normalized_text: str | None = None
        try:
            raw_transcript = await self._voice_adapter.transcribe(audio_chunks, media_type)
            normalized_transcript = self._transcript_normalization_service.normalize(raw_transcript)
            normalized_text = normalized_transcript.text
            extracted_tree = await self._extract_with_retry(
                normalized_transcript,
                safety_identifier=str(user_id),
            )
            tasks = self._build_tasks(user_id, extracted_tree.root)
            finished_at = datetime.now(UTC)
            completed_session = replace(
                session,
                status=DuckSessionStatus.COMPLETED,
                transcript=normalized_text,
                root_task_id=tasks[0].id,
                finished_at=finished_at,
                updated_at=finished_at,
            )
            await self._session_repository.complete_session(completed_session, tasks)
            return completed_session
        except (
            TranscriptionError,
            TaskExtractionError,
            OpenAIConfigurationError,
        ) as error:
            await self._record_failure(session, normalized_text, error.code)
            raise

    async def _extract_with_retry(
        self,
        transcript: NormalizedTranscript,
        safety_identifier: str,
    ) -> ExtractedTaskTree:
        for attempt in range(TASK_EXTRACTION_ATTEMPTS):
            try:
                return await self._task_extraction_adapter.extract_tasks(
                    transcript,
                    safety_identifier,
                )
            except TaskExtractionRateLimitError:
                if attempt + 1 == TASK_EXTRACTION_ATTEMPTS:
                    raise
                await asyncio.sleep(TASK_EXTRACTION_RETRY_DELAY_SECONDS)
        raise AssertionError("Task extraction attempts must be positive")

    async def _record_failure(
        self,
        session: DuckSession,
        transcript: str | None,
        failure_code: str,
    ) -> None:
        finished_at = datetime.now(UTC)
        failed_session = replace(
            session,
            status=DuckSessionStatus.FAILED,
            transcript=transcript,
            failure_code=failure_code,
            finished_at=finished_at,
            updated_at=finished_at,
        )
        try:
            await self._session_repository.update_session(failed_session)
        except DuckSessionPersistenceError:
            logger.warning(
                "duck_session_failure_not_persisted user_id=%s session_id=%s failure_code=%s",
                session.user_id,
                session.id,
                failure_code,
            )

    @staticmethod
    def _build_tasks(user_id: UUID, root: ExtractedTask) -> tuple[Task, ...]:
        created_at = datetime.now(UTC)
        tasks: list[Task] = []

        def append_task(
            extracted: ExtractedTask, parent_task_id: UUID | None, position: int
        ) -> None:
            task_id = uuid4()
            tasks.append(
                Task(
                    id=task_id,
                    user_id=user_id,
                    parent_task_id=parent_task_id,
                    title=extracted.title.strip(),
                    description=extracted.description,
                    category=extracted.category,
                    status=TaskStatus.PENDING,
                    estimated_minutes=extracted.estimated_minutes,
                    initial_easiness_score=extracted.initial_easiness_score,
                    easiness_source=extracted.easiness_source,
                    scheduled_date=None,
                    due_at=None,
                    position=position,
                    completed_at=None,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
            for child_position, child in enumerate(extracted.children):
                append_task(child, task_id, child_position)

        append_task(root, None, 0)
        return tuple(tasks)
