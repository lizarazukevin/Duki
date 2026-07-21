class DukyError(Exception):
    """Base class for expected domain failures."""

    code = "domain_error"
    status_code = 400


class TranscriptionError(DukyError):
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


class TaskExtractionError(DukyError):
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


class DuckSessionNotFoundError(DukyError):
    code = "duck_session_not_found"
    status_code = 404


class DuckSessionPersistenceError(DukyError):
    code = "duck_session_persistence_unavailable"
    status_code = 503


class DuckSessionConfirmationConflictError(DukyError):
    code = "duck_session_confirmation_conflict"
    status_code = 409


class DuckSessionConfigurationError(DukyError):
    code = "duck_session_configuration_error"
    status_code = 503


class AuthConfigurationError(DukyError):
    code = "auth_configuration_error"
    status_code = 503


class CalendarPersistenceError(DukyError):
    code = "calendar_persistence_unavailable"
    status_code = 503


class CalendarAuthorizationError(DukyError):
    code = "calendar_authorization_failed"
    status_code = 401


class CalendarConfigurationError(DukyError):
    code = "calendar_configuration_error"
    status_code = 503


class CalendarRateLimitError(DukyError):
    code = "calendar_rate_limited"
    status_code = 503


class CalendarUnavailableError(DukyError):
    code = "calendar_unavailable"
    status_code = 503


class GoogleCredentialsNotFoundError(DukyError):
    code = "google_credentials_not_found"
    status_code = 409


class AuthenticationError(DukyError):
    code = "invalid_session"
    status_code = 401


class AuthorizationExchangeError(DukyError):
    code = "authorization_exchange_failed"
    status_code = 401


class CredentialEncryptionError(DukyError):
    code = "credential_encryption_failed"
    status_code = 500


class FeatureDisabledError(DukyError):
    code = "feature_disabled"
    status_code = 503


class IdentityProviderUnavailableError(DukyError):
    code = "identity_provider_unavailable"
    status_code = 503


class InvalidPaginationCursorError(DukyError):
    code = "invalid_pagination_cursor"
    status_code = 422


class PersistenceError(DukyError):
    code = "persistence_unavailable"
    status_code = 503


class TaskNotFoundError(DukyError):
    code = "task_not_found"
    status_code = 404


class TaskConfigurationError(DukyError):
    code = "task_configuration_error"
    status_code = 503


class InvalidTaskHierarchyError(DukyError):
    code = "invalid_task_hierarchy"
    status_code = 422


class TaskPersistenceError(DukyError):
    code = "task_persistence_unavailable"
    status_code = 503


class TaskCompletionConflictError(DukyError):
    code = "task_completion_conflict"
    status_code = 409


class GoalNotFoundError(DukyError):
    code = "goal_not_found"
    status_code = 404


class GoalPersistenceError(DukyError):
    code = "goal_persistence_unavailable"
    status_code = 503


class MoodNotFoundError(DukyError):
    code = "mood_not_found"
    status_code = 404


class MoodPersistenceError(DukyError):
    code = "mood_persistence_unavailable"
    status_code = 503


class MoodConfigurationError(DukyError):
    code = "mood_configuration_error"
    status_code = 503


class SchedulerConfigurationError(DukyError):
    code = "scheduler_configuration_error"
    status_code = 503


class RedirectNotAllowedError(DukyError):
    code = "redirect_not_allowed"
    status_code = 422


class SessionRefreshError(DukyError):
    code = "session_refresh_failed"
    status_code = 401
