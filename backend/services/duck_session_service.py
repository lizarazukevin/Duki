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
    TaskExtractionError,
    TaskExtractionRateLimitError,
    TranscriptionError,
)
from backend.models.duck_sessions import (
    DuckSession,
    DuckSessionStatus,
    ExtractedTaskTree,
    NormalizedTranscript,
    SuggestedTaskAction,
    TaskResolutionSuggestion,
)
from backend.models.tasks import Task
from backend.repositories.duck_sessions import DuckSessionRepository
from backend.repositories.tasks import TaskRepository
from backend.services.task_deduplication_service import TaskDeduplicationService
from backend.services.transcript_normalization_service import TranscriptNormalizationService

TASK_EXTRACTION_ATTEMPTS = 3
TASK_EXTRACTION_RETRY_BASE_SECONDS = 1.0

logger = logging.getLogger(LOGGER_NAME)


class DuckSessionService:
    """Orchestrate streamed transcription into an atomically persisted task tree."""

    def __init__(
        self,
        voice_adapter: VoiceAdapter,
        task_extraction_adapter: TaskExtractionAdapter,
        session_repository: DuckSessionRepository,
        transcript_normalization_service: TranscriptNormalizationService,
        task_repository: TaskRepository,
        task_deduplication_service: TaskDeduplicationService,
    ) -> None:
        self._voice_adapter = voice_adapter
        self._task_extraction_adapter = task_extraction_adapter
        self._session_repository = session_repository
        self._transcript_normalization_service = transcript_normalization_service
        self._task_repository = task_repository
        self._task_deduplication_service = task_deduplication_service

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
            resolution_suggestions=(),
            confirmed_resolutions=(),
            confirmed_at=None,
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
            existing_tasks = await self._task_repository.list_tasks(
                user_id,
                include_archived=False,
            )
            extracted_tree = await self._extract_with_retry(
                normalized_transcript,
                user_identifier=str(user_id),
                open_tasks=existing_tasks,
            )
            finished_at = datetime.now(UTC)
            reconciled_tree = (
                self._task_deduplication_service.reconcile(
                    user_id,
                    extracted_tree.root,
                    existing_tasks,
                    finished_at,
                )
                if extracted_tree.root is not None
                else None
            )
            completed_session = replace(
                session,
                status=DuckSessionStatus.COMPLETED,
                transcript=normalized_text,
                root_task_id=(
                    reconciled_tree.root_task_id if reconciled_tree is not None else None
                ),
                resolution_suggestions=(
                    extracted_tree.resolution_suggestions
                    + (
                        (
                            TaskResolutionSuggestion(
                                reconciled_tree.root_task_id,
                                SuggestedTaskAction.COMPLETE,
                                extracted_tree.root_completion.actual_minutes,
                                extracted_tree.root_completion.actual_easiness_score,
                            ),
                        )
                        if reconciled_tree is not None
                        and extracted_tree.root_completion is not None
                        else ()
                    )
                ),
                finished_at=finished_at,
                updated_at=finished_at,
            )
            await self._session_repository.complete_session(
                completed_session,
                reconciled_tree.new_tasks if reconciled_tree is not None else (),
            )
            return completed_session
        except (TranscriptionError, TaskExtractionError) as error:
            await self._record_failure(session, normalized_text, error.code)
            raise

    async def _extract_with_retry(
        self,
        transcript: NormalizedTranscript,
        user_identifier: str,
        open_tasks: tuple[Task, ...],
    ) -> ExtractedTaskTree:
        for attempt in range(TASK_EXTRACTION_ATTEMPTS):
            try:
                return await self._task_extraction_adapter.extract_tasks(
                    transcript,
                    user_identifier,
                    open_tasks,
                )
            except TaskExtractionRateLimitError as error:
                if attempt + 1 == TASK_EXTRACTION_ATTEMPTS:
                    raise
                retry_delay = error.retry_after_seconds or (
                    TASK_EXTRACTION_RETRY_BASE_SECONDS * (2**attempt)
                )
                await asyncio.sleep(retry_delay)
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
