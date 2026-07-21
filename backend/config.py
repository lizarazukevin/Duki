from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True, slots=True)
class Settings:
    app_environment: str
    auth_enabled: bool

    @property
    def is_local(self) -> bool:
        return self.app_environment == "local"


def _is_enabled(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes"}


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_environment=os.getenv("APP_ENV", "local").lower(),
        auth_enabled=_is_enabled(os.getenv("AUTH_ENABLED", "false")),
    )
