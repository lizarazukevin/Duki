import re
from collections.abc import Sequence

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from backend.adapters.task_extraction.base import TaskExtractionAdapter
from backend.constants import DEFAULT_TASK_EXTRACTION_MODEL, OPENAI_API_BASE_URL
from backend.errors import (
    NoTasksExtractedError,
    OpenAIConfigurationError,
    TaskExtractionError,
    TaskExtractionRateLimitError,
)
from backend.models.duck_sessions import (
    MAX_EXTRACTED_TASKS,
    ExtractedTask,
    ExtractedTaskTree,
    NormalizedTranscript,
)
from backend.models.tasks import EasinessSource, TaskCategory

TASK_EXTRACTION_TIMEOUT_SECONDS = 90.0
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")
_NETWORK_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError)
_EXTRACTION_INSTRUCTIONS = """Convert the user's voice note into one actionable task tree.

Success means:
- set can_extract=false and tasks=[] when the note contains no actionable work
- otherwise return exactly one root task with parent_local_id=null
- assign every other task to an existing parent using short unique local IDs
- preserve the user's intent; do not invent unrelated work
- use work, chore, or personal for category
- estimate minutes when reasonably inferable, otherwise use null
- use easiness_source=user only when the user explicitly states difficulty or ease
- otherwise infer a 1-5 score when supported by the note, or set score and source to null
"""


class _ExtractedTaskPayload(BaseModel):
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
    def validate_easiness_pair(self) -> _ExtractedTaskPayload:
        if (self.initial_easiness_score is None) != (self.easiness_source is None):
            raise ValueError("Easiness score and source must be provided together")
        return self


class _ExtractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    can_extract: bool
    tasks: list[_ExtractedTaskPayload] = Field(max_length=MAX_EXTRACTED_TASKS)

    @model_validator(mode="after")
    def validate_task_presence(self) -> _ExtractionPayload:
        if self.can_extract != bool(self.tasks):
            raise ValueError("Task presence must match can_extract")
        return self


_TASK_TREE_SCHEMA = _ExtractionPayload.model_json_schema()


class OpenAITaskExtractionAdapter(TaskExtractionAdapter):
    """Extract a validated task tree with OpenAI Responses structured output."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        model: str = DEFAULT_TASK_EXTRACTION_MODEL,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key cannot be blank")
        if not _MODEL_PATTERN.fullmatch(model):
            raise ValueError("OpenAI extraction model identifier is invalid")
        self._http_client = http_client
        self._api_key = api_key
        self._model = model
        self._responses_url = f"{OPENAI_API_BASE_URL}/responses"

    async def extract_tasks(
        self,
        transcript: NormalizedTranscript,
        safety_identifier: str,
    ) -> ExtractedTaskTree:
        if not safety_identifier or len(safety_identifier) > 64:
            raise ValueError("OpenAI safety identifier is invalid")
        try:
            response = await self._http_client.post(
                self._responses_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "reasoning": {"effort": "none"},
                    "store": False,
                    "instructions": _EXTRACTION_INSTRUCTIONS,
                    "input": transcript.text,
                    "safety_identifier": safety_identifier,
                    "max_output_tokens": 6000,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "duki_task_tree",
                            "strict": True,
                            "schema": _TASK_TREE_SCHEMA,
                        }
                    },
                },
                timeout=TASK_EXTRACTION_TIMEOUT_SECONDS,
            )
        except _NETWORK_ERRORS as error:
            raise TaskExtractionError("Task extraction is unavailable") from error

        if response.status_code in {401, 403}:
            raise OpenAIConfigurationError("OpenAI task extraction is not authorized")
        if response.status_code == 429:
            raise TaskExtractionRateLimitError("Task extraction is rate limited")
        if response.status_code >= 400:
            raise TaskExtractionError("Tasks could not be extracted")

        try:
            response_payload: object = response.json()
            output_text = self._output_text(response_payload)
            extraction = _ExtractionPayload.model_validate_json(output_text)
            if not extraction.can_extract:
                raise NoTasksExtractedError("No actionable tasks were found")
            return self._build_tree(extraction.tasks)
        except NoTasksExtractedError:
            raise
        except (TypeError, ValueError, ValidationError) as error:
            raise TaskExtractionError("Task extraction response is invalid") from error

    @staticmethod
    def _output_text(payload: object) -> str:
        if not isinstance(payload, dict) or payload.get("status") != "completed":
            raise TypeError("Incomplete task extraction response")
        output = payload.get("output")
        if not isinstance(output, list):
            raise TypeError("Missing task extraction output")

        output_texts: list[str] = []
        for output_item in output:
            if not isinstance(output_item, dict) or output_item.get("type") != "message":
                continue
            content = output_item.get("content")
            if not isinstance(content, list):
                raise TypeError("Invalid task extraction message")
            for content_item in content:
                if not isinstance(content_item, dict):
                    raise TypeError("Invalid task extraction content")
                if content_item.get("type") == "refusal":
                    raise TaskExtractionError("Task extraction was refused")
                if content_item.get("type") == "output_text":
                    text = content_item.get("text")
                    if not isinstance(text, str):
                        raise TypeError("Invalid task extraction text")
                    output_texts.append(text)
        if len(output_texts) != 1:
            raise TypeError("Unexpected task extraction output count")
        return output_texts[0]

    @staticmethod
    def _build_tree(tasks: Sequence[_ExtractedTaskPayload]) -> ExtractedTaskTree:
        tasks_by_id = {task.local_id: task for task in tasks}
        if len(tasks_by_id) != len(tasks):
            raise ValueError("Extracted task IDs must be unique")
        roots = [task for task in tasks if task.parent_local_id is None]
        if len(roots) != 1:
            raise ValueError("Extracted task tree must have exactly one root")

        children_by_parent: dict[str, list[_ExtractedTaskPayload]] = {}
        for task in tasks:
            if task.parent_local_id is None:
                continue
            if task.parent_local_id not in tasks_by_id:
                raise ValueError("Extracted task parent does not exist")
            children_by_parent.setdefault(task.parent_local_id, []).append(task)

        visited_ids: set[str] = set()

        def build_task(task: _ExtractedTaskPayload, ancestor_ids: frozenset[str]) -> ExtractedTask:
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
