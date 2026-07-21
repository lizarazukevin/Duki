import re

import httpx

from backend.adapters.task_extraction.base import TaskExtractionAdapter
from backend.adapters.task_extraction.structured import (
    EXTRACTION_INSTRUCTIONS,
    TASK_TREE_SCHEMA,
    decode_task_tree,
)
from backend.constants import DEFAULT_OPENAI_TASK_EXTRACTION_MODEL, OPENAI_API_BASE_URL
from backend.errors import (
    TaskExtractionConfigurationError,
    TaskExtractionError,
    TaskExtractionRateLimitError,
)
from backend.models.duck_sessions import ExtractedTaskTree, NormalizedTranscript

TASK_EXTRACTION_TIMEOUT_SECONDS = 90.0
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:-]+$")
_NETWORK_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError)


class OpenAITaskExtractionAdapter(TaskExtractionAdapter):
    """Extract a validated task tree with OpenAI Responses structured output."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        api_key: str,
        model: str = DEFAULT_OPENAI_TASK_EXTRACTION_MODEL,
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
        user_identifier: str,
    ) -> ExtractedTaskTree:
        if not user_identifier or len(user_identifier) > 64:
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
                    "instructions": EXTRACTION_INSTRUCTIONS,
                    "input": transcript.text,
                    "safety_identifier": user_identifier,
                    "max_output_tokens": 6000,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "duki_task_tree",
                            "strict": True,
                            "schema": TASK_TREE_SCHEMA,
                        }
                    },
                },
                timeout=TASK_EXTRACTION_TIMEOUT_SECONDS,
            )
        except _NETWORK_ERRORS as error:
            raise TaskExtractionError("Task extraction is unavailable") from error

        if response.status_code in {401, 403}:
            raise TaskExtractionConfigurationError("Task extraction is not authorized")
        if response.status_code == 429:
            raise TaskExtractionRateLimitError("Task extraction is rate limited")
        if response.status_code >= 400:
            raise TaskExtractionError("Tasks could not be extracted")

        try:
            response_payload: object = response.json()
            return decode_task_tree(self._output_text(response_payload))
        except TaskExtractionError:
            raise
        except (TypeError, ValueError) as error:
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
