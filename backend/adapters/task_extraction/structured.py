import json
from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from backend.errors import NoTasksExtractedError, TaskExtractionError
from backend.models.duck_sessions import (
    MAX_EXTRACTED_TASKS,
    ExtractedCompletionFeedback,
    ExtractedTask,
    ExtractedTaskTree,
    NormalizedTranscript,
    SuggestedTaskAction,
    TaskResolutionSuggestion,
)
from backend.models.tasks import EasinessSource, Task, TaskCategory, TaskStatus

EXTRACTION_INSTRUCTIONS = """Convert the user's voice note into one actionable task tree.

Success means:
- compare the transcript with the supplied open-task context
- when the user references an existing task, return a resolution for its exact task_id
- copy resolution task_id values exactly from the supplied context; never invent an ID
- suggest complete only when the user says the task is done; include actual time/ease
  only when explicitly stated
- suggest archive only when the user explicitly abandons or dismisses the task
- otherwise suggest keep_open for referenced existing work
- do not recreate referenced open work as a new task
- for existing-task resolutions, keep tasks empty and root_is_completed=false
- when completed work does not match an open task, create it as a new root task and set
  root_is_completed=true so the user can confirm and retain the unplanned work
- put explicitly stated completion duration/ease in root_actual_minutes and
  root_actual_easiness_score; otherwise set those fields to null
- do not copy actual completion feedback into estimate or initial-easiness fields
- treat intentions, obligations, desired outcomes, and ongoing work as actionable
- convert ongoing work such as "I'm working on my project" into a continuation task
- set can_extract=false with tasks=[] and resolutions=[] only when the note contains no
  work, intention, obligation, desired outcome, or referenced open task
- when creating new work, return exactly one root task with parent_local_id=null
- assign every other task to an existing parent using short unique local IDs
- preserve the user's intent; do not invent unrelated work
- ignore greetings, identity details, and incidental present activity unless the user
  expresses an intention or obligation involving them
- use work, chore, or personal for category
- estimate minutes for future work when reasonably inferable, otherwise use null
- use easiness_source=user only when the user explicitly states difficulty or ease
- otherwise infer a 1-5 score when supported by the note, or set score and source to null
"""
MAX_OPEN_TASK_CONTEXT = 100


class ExtractedTaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    parent_local_id: str | None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(max_length=10000)
    category: TaskCategory
    estimated_minutes: int | None = Field(gt=0)
    initial_easiness_score: int | None = Field(ge=1, le=5)
    easiness_source: EasinessSource | None

    @model_validator(mode="after")
    def validate_easiness_pair(self) -> ExtractedTaskPayload:
        if (self.initial_easiness_score is None) != (self.easiness_source is None):
            raise ValueError("Easiness score and source must be provided together")
        return self


class TaskResolutionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: UUID
    suggested_action: SuggestedTaskAction
    actual_minutes: int | None = Field(gt=0)
    actual_easiness_score: int | None = Field(ge=1, le=5)

    @model_validator(mode="after")
    def validate_feedback_scope(self) -> TaskResolutionPayload:
        TaskResolutionSuggestion(
            self.task_id,
            self.suggested_action,
            self.actual_minutes,
            self.actual_easiness_score,
        )
        return self


class ExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_extract: bool
    tasks: list[ExtractedTaskPayload] = Field(max_length=MAX_EXTRACTED_TASKS)
    resolutions: list[TaskResolutionPayload] = Field(max_length=MAX_EXTRACTED_TASKS)
    root_is_completed: bool
    root_actual_minutes: int | None = Field(gt=0)
    root_actual_easiness_score: int | None = Field(ge=1, le=5)

    @model_validator(mode="after")
    def validate_task_presence(self) -> ExtractionPayload:
        if self.can_extract != bool(self.tasks or self.resolutions):
            raise ValueError("Task presence must match can_extract")
        if self.root_is_completed and not self.tasks:
            raise ValueError("Completed root requires an extracted task")
        if not self.root_is_completed and (
            self.root_actual_minutes is not None or self.root_actual_easiness_score is not None
        ):
            raise ValueError("Root feedback requires completed work")
        return self


_NULL_SCHEMA = {"type": "null"}
_TASK_PROPERTIES = {
    "local_id": {"type": "string"},
    "parent_local_id": {"anyOf": [{"type": "string"}, _NULL_SCHEMA]},
    "title": {"type": "string"},
    "description": {"anyOf": [{"type": "string"}, _NULL_SCHEMA]},
    "category": {"type": "string", "enum": ["work", "chore", "personal"]},
    "estimated_minutes": {"anyOf": [{"type": "integer"}, _NULL_SCHEMA]},
    "initial_easiness_score": {"anyOf": [{"type": "integer"}, _NULL_SCHEMA]},
    "easiness_source": {
        "anyOf": [
            {"type": "string", "enum": ["user", "inferred"]},
            _NULL_SCHEMA,
        ]
    },
}
_RESOLUTION_PROPERTIES = {
    "task_id": {"type": "string"},
    "suggested_action": {
        "type": "string",
        "enum": ["complete", "keep_open", "archive"],
    },
    "actual_minutes": {"anyOf": [{"type": "integer"}, _NULL_SCHEMA]},
    "actual_easiness_score": {"anyOf": [{"type": "integer"}, _NULL_SCHEMA]},
}
TASK_TREE_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "can_extract": {"type": "boolean"},
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": _TASK_PROPERTIES,
                "required": list(_TASK_PROPERTIES),
                "additionalProperties": False,
            },
        },
        "resolutions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": _RESOLUTION_PROPERTIES,
                "required": list(_RESOLUTION_PROPERTIES),
                "additionalProperties": False,
            },
        },
        "root_is_completed": {"type": "boolean"},
        "root_actual_minutes": {"anyOf": [{"type": "integer"}, _NULL_SCHEMA]},
        "root_actual_easiness_score": {"anyOf": [{"type": "integer"}, _NULL_SCHEMA]},
    },
    "required": [
        "can_extract",
        "tasks",
        "resolutions",
        "root_is_completed",
        "root_actual_minutes",
        "root_actual_easiness_score",
    ],
    "additionalProperties": False,
}


def decode_task_tree(
    output_text: str,
    allowed_task_ids: frozenset[UUID] = frozenset(),
) -> ExtractedTaskTree:
    """Validate structured provider output and build a provider-neutral tree."""
    try:
        extraction = ExtractionPayload.model_validate_json(output_text)
        if not extraction.can_extract:
            raise NoTasksExtractedError("No actionable tasks were found")
        suggestions = tuple(
            TaskResolutionSuggestion(
                resolution.task_id,
                resolution.suggested_action,
                resolution.actual_minutes,
                resolution.actual_easiness_score,
            )
            for resolution in extraction.resolutions
        )
        if any(suggestion.task_id not in allowed_task_ids for suggestion in suggestions):
            raise ValueError("Resolution references an unknown open task")
        root_completion = (
            ExtractedCompletionFeedback(
                extraction.root_actual_minutes,
                extraction.root_actual_easiness_score,
            )
            if extraction.root_is_completed
            else None
        )
        return _build_tree(extraction.tasks, suggestions, root_completion)
    except NoTasksExtractedError:
        raise
    except (TypeError, ValueError, ValidationError) as error:
        raise TaskExtractionError("Task extraction response is invalid") from error


def _build_tree(
    tasks: Sequence[ExtractedTaskPayload],
    suggestions: tuple[TaskResolutionSuggestion, ...],
    root_completion: ExtractedCompletionFeedback | None,
) -> ExtractedTaskTree:
    tasks_by_id = {task.local_id: task for task in tasks}
    if len(tasks_by_id) != len(tasks):
        raise ValueError("Extracted task IDs must be unique")
    roots = [task for task in tasks if task.parent_local_id is None]
    if len(roots) > 1 or (tasks and len(roots) != 1):
        raise ValueError("Extracted task tree must have exactly one root")
    if not tasks:
        return ExtractedTaskTree(None, suggestions)

    children_by_parent: dict[str, list[ExtractedTaskPayload]] = {}
    for task in tasks:
        if task.parent_local_id is None:
            continue
        if task.parent_local_id not in tasks_by_id:
            raise ValueError("Extracted task parent does not exist")
        children_by_parent.setdefault(task.parent_local_id, []).append(task)

    visited_ids: set[str] = set()

    def build_task(task: ExtractedTaskPayload, ancestor_ids: frozenset[str]) -> ExtractedTask:
        if task.local_id in ancestor_ids:
            raise ValueError("Extracted task tree contains a cycle")
        visited_ids.add(task.local_id)
        path = ancestor_ids | {task.local_id}
        return ExtractedTask(
            title=task.title.strip(),
            description=task.description,
            category=task.category,
            estimated_minutes=task.estimated_minutes,
            initial_easiness_score=task.initial_easiness_score,
            easiness_source=task.easiness_source,
            children=tuple(
                build_task(child, path) for child in children_by_parent.get(task.local_id, ())
            ),
        )

    root = build_task(roots[0], frozenset())
    if len(visited_ids) != len(tasks_by_id):
        raise ValueError("Extracted task tree contains disconnected tasks")
    return ExtractedTaskTree(
        root=root,
        resolution_suggestions=suggestions,
        root_completion=root_completion,
    )


def select_open_task_context(tasks: Sequence[Task]) -> tuple[Task, ...]:
    open_tasks = (
        task for task in tasks if task.status in {TaskStatus.PENDING, TaskStatus.IN_PROGRESS}
    )
    return tuple(
        sorted(open_tasks, key=lambda task: (task.updated_at, task.id), reverse=True)[
            :MAX_OPEN_TASK_CONTEXT
        ]
    )


def build_extraction_input(transcript: NormalizedTranscript, open_tasks: Sequence[Task]) -> str:
    context = [
        {
            "task_id": str(task.id),
            "title": task.title,
            "category": task.category.value,
            "status": task.status.value,
        }
        for task in open_tasks
    ]
    return (
        f"Open-task context:\n{json.dumps(context, separators=(',', ':'))}"
        f"\n\nUser transcript:\n{transcript.text}"
    )
