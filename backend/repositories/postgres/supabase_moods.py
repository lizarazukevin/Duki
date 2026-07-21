from datetime import UTC, date, datetime
from uuid import UUID

import httpx

from backend.errors import MoodNotFoundError, MoodPersistenceError
from backend.models.moods import DailyMood, MoodComputation, MoodPoll
from backend.repositories.moods import MoodRepository

_NETWORK_ERRORS = (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError)


class SupabaseMoodRepository(MoodRepository):
    """Persist private daily mood records through Supabase PostgREST."""

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        supabase_url: str,
        secret_key: str,
    ) -> None:
        self._http_client = http_client
        self._moods_url = f"{supabase_url.rstrip('/')}/rest/v1/daily_moods"
        self._read_headers = {"apikey": secret_key}
        self._write_headers = {
            "apikey": secret_key,
            "Prefer": "resolution=merge-duplicates,return=representation",
        }

    async def upsert_mood(
        self,
        user_id: UUID,
        poll: MoodPoll,
        computation: MoodComputation,
    ) -> DailyMood:
        payload = {
            "user_id": str(user_id),
            "mood_date": poll.mood_date.isoformat(),
            "reported_mood_score": poll.reported_mood_score,
            "calendar_load_score": computation.calendar_load_score,
            "computed_mood_score": computation.computed_mood_score,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        try:
            response = await self._http_client.post(
                self._moods_url,
                params={"on_conflict": "user_id,mood_date", "select": "*"},
                headers=self._write_headers,
                json=payload,
            )
        except _NETWORK_ERRORS as error:
            raise MoodPersistenceError("Mood could not be saved") from error
        if response.status_code >= 400:
            raise MoodPersistenceError("Mood could not be saved")
        return self._parse_single_row(response, "Saved mood is invalid")

    async def get_mood(self, user_id: UUID, mood_date: date) -> DailyMood:
        try:
            response = await self._http_client.get(
                self._moods_url,
                params={
                    "select": "*",
                    "user_id": f"eq.{user_id}",
                    "mood_date": f"eq.{mood_date.isoformat()}",
                    "limit": "1",
                },
                headers=self._read_headers,
            )
        except _NETWORK_ERRORS as error:
            raise MoodPersistenceError("Mood could not be loaded") from error
        if response.status_code >= 400:
            raise MoodPersistenceError("Mood could not be loaded")
        return self._parse_single_row(response, "Stored mood is invalid", allow_missing=True)

    @staticmethod
    def _parse_single_row(
        response: httpx.Response,
        invalid_message: str,
        *,
        allow_missing: bool = False,
    ) -> DailyMood:
        try:
            payload: object = response.json()
            if not isinstance(payload, list):
                raise TypeError("Invalid mood collection")
            if not payload:
                if allow_missing:
                    raise MoodNotFoundError("Mood was not found")
                raise TypeError("Missing saved mood")
            return SupabaseMoodRepository._parse_mood(payload[0])
        except MoodNotFoundError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise MoodPersistenceError(invalid_message) from error

    @staticmethod
    def _parse_mood(row: object) -> DailyMood:
        if not isinstance(row, dict):
            raise TypeError("Invalid mood row")
        reported_score = row["reported_mood_score"]
        if not isinstance(reported_score, int) or isinstance(reported_score, bool):
            raise TypeError("Invalid reported mood score")
        return DailyMood(
            id=UUID(_required_string(row, "id")),
            user_id=UUID(_required_string(row, "user_id")),
            mood_date=date.fromisoformat(_required_string(row, "mood_date")),
            reported_mood_score=reported_score,
            calendar_load_score=float(row["calendar_load_score"]),
            computed_mood_score=float(row["computed_mood_score"]),
            created_at=datetime.fromisoformat(_required_string(row, "created_at")),
            updated_at=datetime.fromisoformat(_required_string(row, "updated_at")),
        )


def _required_string(row: dict[str, object], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise TypeError("Invalid stored mood")
    return value
