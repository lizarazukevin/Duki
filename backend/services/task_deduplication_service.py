import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from backend.models.duck_sessions import ExtractedTask
from backend.models.tasks import Task, TaskStatus

_NON_WORD_CHARACTERS = re.compile(r"[^\w]+", re.UNICODE)
_TITLE_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "continue",
        "continuing",
        "for",
        "my",
        "on",
        "the",
        "to",
    }
)
_TITLE_SIMILARITY_THRESHOLD = 0.8


@dataclass(frozen=True, slots=True)
class ReconciledTaskTree:
    root_task_id: UUID
    new_tasks: tuple[Task, ...]


class TaskDeduplicationService:
    """Reconcile an extracted tree against equivalent open tasks by parent context."""

    def reconcile(
        self,
        user_id: UUID,
        root: ExtractedTask,
        existing_tasks: tuple[Task, ...],
        created_at: datetime,
    ) -> ReconciledTaskTree:
        if created_at.utcoffset() is None:
            raise ValueError("Task reconciliation timestamp must include a timezone")

        candidates: dict[tuple[UUID | None, str], list[Task]] = {}
        for task in sorted(existing_tasks, key=lambda item: (item.created_at, item.id)):
            if task.status in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}:
                candidates.setdefault(
                    (task.parent_task_id, task.category.value),
                    [],
                ).append(task)

        new_tasks: list[Task] = []

        def reconcile_task(
            extracted: ExtractedTask,
            parent_task_id: UUID | None,
            position: int,
        ) -> UUID:
            group_key = (parent_task_id, extracted.category.value)
            matched_task = next(
                (
                    task
                    for task in candidates.get(group_key, ())
                    if self._titles_match(task.title, extracted.title)
                ),
                None,
            )
            if matched_task is not None:
                task_id = matched_task.id
            else:
                task_id = uuid4()
                matched_task = Task(
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
                candidates.setdefault(group_key, []).append(matched_task)
                new_tasks.append(matched_task)
            for child_position, child in enumerate(extracted.children):
                reconcile_task(child, task_id, child_position)
            return task_id

        root_task_id = reconcile_task(root, None, 0)
        return ReconciledTaskTree(root_task_id, tuple(new_tasks))

    @classmethod
    def _titles_match(cls, first_title: str, second_title: str) -> bool:
        first_tokens = cls._title_tokens(first_title)
        second_tokens = cls._title_tokens(second_title)
        if first_tokens == second_tokens:
            return True
        if not first_tokens or not second_tokens:
            return False
        matched_tokens = sum(
            any(cls._tokens_match(first, second) for second in second_tokens)
            for first in first_tokens
        )
        similarity = 2 * matched_tokens / (len(first_tokens) + len(second_tokens))
        return similarity >= _TITLE_SIMILARITY_THRESHOLD

    @staticmethod
    def _title_tokens(title: str) -> tuple[str, ...]:
        normalized_title = unicodedata.normalize("NFKC", title).casefold()
        normalized_title = " ".join(_NON_WORD_CHARACTERS.sub(" ", normalized_title).split())
        return tuple(token for token in normalized_title.split() if token not in _TITLE_STOP_WORDS)

    @staticmethod
    def _tokens_match(first_token: str, second_token: str) -> bool:
        if first_token == second_token:
            return True
        if min(len(first_token), len(second_token)) < 4:
            return False
        first_stem = first_token[:-3] if first_token.endswith("ing") else first_token
        second_stem = second_token[:-3] if second_token.endswith("ing") else second_token
        return first_stem.startswith(second_stem) or second_stem.startswith(first_stem)
