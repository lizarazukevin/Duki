from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from backend.errors import NoTasksExtractedError, TaskExtractionError
from backend.models.duck_sessions import MAX_EXTRACTED_TASKS, ExtractedTask, ExtractedTaskTree
from backend.models.tasks import EasinessSource, TaskCategory

EXTRACTION_INSTRUCTIONS = """Convert the user's voice note into one actionable task tree.

Success means:
- treat intentions, obligations, desired outcomes, and ongoing work as actionable
- convert ongoing work such as "I'm working on my project" into a continuation task
- set can_extract=false and tasks=[] only when the note contains no work, intention,
  obligation, desired outcome, or action to continue
- otherwise return exactly one root task with parent_local_id=null
- assign every other task to an existing parent using short unique local IDs
- preserve the user's intent; do not invent unrelated work
- ignore greetings, identity details, and incidental present activity unless the user
  expresses an intention or obligation involving them
- use work, chore, or personal for category
- estimate minutes when reasonably inferable, otherwise use null
- use easiness_source=user only when the user explicitly states difficulty or ease
- otherwise infer a 1-5 score when supported by the note, or set score and source to null
"""


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


class ExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_extract: bool
    tasks: list[ExtractedTaskPayload] = Field(max_length=MAX_EXTRACTED_TASKS)

    @model_validator(mode="after")
    def validate_task_presence(self) -> ExtractionPayload:
        if self.can_extract != bool(self.tasks):
            raise ValueError("Task presence must match can_extract")
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
    },
    "required": ["can_extract", "tasks"],
    "additionalProperties": False,
}


def decode_task_tree(output_text: str) -> ExtractedTaskTree:
    """Validate structured provider output and build a provider-neutral tree."""
    try:
        extraction = ExtractionPayload.model_validate_json(output_text)
        if not extraction.can_extract:
            raise NoTasksExtractedError("No actionable tasks were found")
        return _build_tree(extraction.tasks)
    except NoTasksExtractedError:
        raise
    except (TypeError, ValueError, ValidationError) as error:
        raise TaskExtractionError("Task extraction response is invalid") from error


def _build_tree(tasks: Sequence[ExtractedTaskPayload]) -> ExtractedTaskTree:
    tasks_by_id = {task.local_id: task for task in tasks}
    if len(tasks_by_id) != len(tasks):
        raise ValueError("Extracted task IDs must be unique")
    roots = [task for task in tasks if task.parent_local_id is None]
    if len(roots) != 1:
        raise ValueError("Extracted task tree must have exactly one root")

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
    return ExtractedTaskTree(root=root)
