import logging
import re
from collections.abc import Sequence

import httpx

from backend.adapters.task_extraction.base import TaskExtractionAdapter
from backend.adapters.task_extraction.structured import (
    EXTRACTION_INSTRUCTIONS,
    TASK_TREE_SCHEMA,
    build_extraction_input,
    decode_task_tree,
    select_open_task_context,
)
from backend.constants import DEFAULT_GROQ_TASK_EXTRACTION_MODEL, GROQ_API_BASE_URL, LOGGER_NAME
from backend.errors import (
    TaskExtractionConfigurationError,
    TaskExtractionError,
    TaskExtractionRateLimitError,
)
from backend.models.duck_sessions import ExtractedTaskTree, NormalizedTranscript
from backend.models.tasks import Task

TASK_EXTRACTION_TIMEOUT_SECONDS = 90.0
MAX_RETRY_AFTER_SECONDS = 10.0
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]+$")
_NETWORK_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError)

logger = logging.getLogger(LOGGER_NAME)


class GroqTaskExtractionAdapter(TaskExtractionAdapter):
    """Extract strict task-tree JSON with Groq-hosted GPT-OSS."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        model: str = DEFAULT_GROQ_TASK_EXTRACTION_MODEL,
    ) -> None:
        if not api_key:
            raise ValueError("Groq API key cannot be blank")
        if not _MODEL_PATTERN.fullmatch(model):
            raise ValueError("Groq extraction model identifier is invalid")
        self._http_client = http_client
        self._api_key = api_key
        self._model = model
        self._completions_url = f"{GROQ_API_BASE_URL}/chat/completions"

    async def extract_tasks(
        self,
        transcript: NormalizedTranscript,
        user_identifier: str,
        open_tasks: Sequence[Task],
    ) -> ExtractedTaskTree:
        if not user_identifier or len(user_identifier) > 64:
            raise ValueError("Task extraction user identifier is invalid")
        context_tasks = select_open_task_context(open_tasks)
        try:
            response = await self._http_client.post(
                self._completions_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": EXTRACTION_INSTRUCTIONS},
                        {
                            "role": "user",
                            "content": build_extraction_input(transcript, context_tasks),
                        },
                    ],
                    "max_completion_tokens": 6000,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "duky_task_tree",
                            "strict": True,
                            "schema": TASK_TREE_SCHEMA,
                        },
                    },
                },
                timeout=TASK_EXTRACTION_TIMEOUT_SECONDS,
            )
        except _NETWORK_ERRORS as error:
            raise TaskExtractionError("Task extraction is unavailable") from error

        if response.status_code in {401, 403}:
            raise TaskExtractionConfigurationError("Task extraction is not authorized")
        if response.status_code == 429:
            raise TaskExtractionRateLimitError(
                "Task extraction is rate limited",
                retry_after_seconds=self._retry_after_seconds(response),
            )
        if response.status_code >= 400:
            logger.warning(
                "task_extraction_provider_error provider=groq status=%s error_type=%s "
                "error_category=%s",
                response.status_code,
                self._error_type(response),
                self._error_category(response),
            )
            raise TaskExtractionError("Tasks could not be extracted")

        try:
            response_payload: object = response.json()
            return decode_task_tree(
                self._message_content(response_payload),
                frozenset(task.id for task in context_tasks),
            )
        except TaskExtractionError:
            raise
        except (TypeError, ValueError) as error:
            raise TaskExtractionError("Task extraction response is invalid") from error

    @staticmethod
    def _message_content(payload: object) -> str:
        if not isinstance(payload, dict):
            raise TypeError("Invalid task extraction response")
        choices = payload.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise TypeError("Unexpected task extraction choice count")
        choice = choices[0]
        if not isinstance(choice, dict):
            raise TypeError("Invalid task extraction choice")
        message = choice.get("message")
        if not isinstance(message, dict):
            raise TypeError("Missing task extraction message")
        if message.get("refusal"):
            raise TaskExtractionError("Task extraction was refused")
        content = message.get("content")
        if not isinstance(content, str):
            raise TypeError("Missing task extraction content")
        return content

    @staticmethod
    def _error_type(response: httpx.Response) -> str:
        try:
            payload: object = response.json()
        except ValueError:
            return "unknown"
        if not isinstance(payload, dict):
            return "unknown"
        error = payload.get("error")
        if not isinstance(error, dict):
            return "unknown"
        error_type = error.get("type")
        if not isinstance(error_type, str) or not error_type:
            return "unknown"
        return error_type[:100]

    @staticmethod
    def _error_category(response: httpx.Response) -> str:
        try:
            payload: object = response.json()
        except ValueError:
            return "unclassified"
        if not isinstance(payload, dict):
            return "unclassified"
        error = payload.get("error")
        if not isinstance(error, dict):
            return "unclassified"
        message = error.get("message")
        if not isinstance(message, str):
            return "unclassified"
        normalized_message = message.casefold()
        categories = (
            ("schema", "invalid_schema"),
            ("response_format", "invalid_response_format"),
            ("max_completion_tokens", "invalid_token_limit"),
            ("model", "invalid_model"),
            ("messages", "invalid_messages"),
            ("reasoning", "invalid_reasoning_configuration"),
        )
        for marker, category in categories:
            if marker in normalized_message:
                return category
        return "unclassified"

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float | None:
        retry_after = response.headers.get("retry-after")
        if retry_after is None:
            return None
        try:
            parsed_delay = float(retry_after)
        except ValueError:
            return None
        if parsed_delay <= 0:
            return None
        return min(parsed_delay, MAX_RETRY_AFTER_SECONDS)
