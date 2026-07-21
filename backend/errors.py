class DukiError(Exception):
    """Base class for expected domain failures."""

    code = "domain_error"
    status_code = 400


class TranscriptionError(DukiError):
    code = "transcription_failed"
    status_code = 503


class TranscriptionRateLimitError(TranscriptionError):
    code = "transcription_rate_limited"


class UnsupportedAudioTypeError(TranscriptionError):
    code = "unsupported_audio_type"
    status_code = 422


class AudioTooLargeError(TranscriptionError):
    code = "audio_too_large"
    status_code = 422


class NoSpeechDetectedError(TranscriptionError):
    code = "no_speech_detected"
    status_code = 422


class TranscriptionConfigurationError(TranscriptionError):
    code = "transcription_configuration_error"


class TaskExtractionError(DukiError):
    code = "task_extraction_failed"
    status_code = 503


class TaskExtractionRateLimitError(TaskExtractionError):
    code = "task_extraction_rate_limited"

    def __init__(
        self,
        message: str,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class NoTasksExtractedError(TaskExtractionError):
    code = "no_tasks_extracted"
    status_code = 422


class TaskExtractionConfigurationError(TaskExtractionError):
    code = "task_extraction_configuration_error"


class DuckSessionNotFoundError(DukiError):
    code = "duck_session_not_found"
    status_code = 404


class DuckSessionPersistenceError(DukiError):
    code = "duck_session_persistence_unavailable"
    status_code = 503


class DuckSessionConfigurationError(DukiError):
    code = "duck_session_configuration_error"
    status_code = 503


class AuthConfigurationError(DukiError):
    code = "auth_configuration_error"
    status_code = 503


class CalendarPersistenceError(DukiError):
    code = "calendar_persistence_unavailable"
    status_code = 503


class CalendarAuthorizationError(DukiError):
    code = "calendar_authorization_failed"
    status_code = 401


class CalendarConfigurationError(DukiError):
    code = "calendar_configuration_error"
    status_code = 503


class CalendarRateLimitError(DukiError):
    code = "calendar_rate_limited"
    status_code = 503


class CalendarUnavailableError(DukiError):
    code = "calendar_unavailable"
    status_code = 503


class GoogleCredentialsNotFoundError(DukiError):
    code = "google_credentials_not_found"
    status_code = 409


class AuthenticationError(DukiError):
    code = "invalid_session"
    status_code = 401


class AuthorizationExchangeError(DukiError):
    code = "authorization_exchange_failed"
    status_code = 401


class CredentialEncryptionError(DukiError):
    code = "credential_encryption_failed"
    status_code = 500


class FeatureDisabledError(DukiError):
    code = "feature_disabled"
    status_code = 503


class IdentityProviderUnavailableError(DukiError):
    code = "identity_provider_unavailable"
    status_code = 503


class InvalidPaginationCursorError(DukiError):
    code = "invalid_pagination_cursor"
    status_code = 422


class PersistenceError(DukiError):
    code = "persistence_unavailable"
    status_code = 503


class TaskNotFoundError(DukiError):
    code = "task_not_found"
    status_code = 404


class TaskConfigurationError(DukiError):
    code = "task_configuration_error"
    status_code = 503


class InvalidTaskHierarchyError(DukiError):
    code = "invalid_task_hierarchy"
    status_code = 422


class TaskPersistenceError(DukiError):
    code = "task_persistence_unavailable"
    status_code = 503


class TaskCompletionConflictError(DukiError):
    code = "task_completion_conflict"
    status_code = 409


class GoalNotFoundError(DukiError):
    code = "goal_not_found"
    status_code = 404


class GoalPersistenceError(DukiError):
    code = "goal_persistence_unavailable"
    status_code = 503


class MoodNotFoundError(DukiError):
    code = "mood_not_found"
    status_code = 404


class MoodPersistenceError(DukiError):
    code = "mood_persistence_unavailable"
    status_code = 503


class MoodConfigurationError(DukiError):
    code = "mood_configuration_error"
    status_code = 503


class SchedulerConfigurationError(DukiError):
    code = "scheduler_configuration_error"
    status_code = 503


class RedirectNotAllowedError(DukiError):
    code = "redirect_not_allowed"
    status_code = 422


class SessionRefreshError(DukiError):
    code = "session_refresh_failed"
    status_code = 401
