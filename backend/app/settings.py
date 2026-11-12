"""Application settings (pydantic-settings).

Canvas live credentials come from environment / ``backend/.env``.
Never log ``canvas_api_token``.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_PATH = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Subset of process settings needed for Canvas + shared config."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_PATH) if _ENV_PATH.is_file() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    canvas_base_url: str | None = Field(default=None)
    canvas_api_token: SecretStr | None = Field(default=None)
    # Legacy env name — prefer canvas_api_token / CANVAS_API_TOKEN.
    canvas_access_token: SecretStr | None = Field(default=None)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Tests set env explicitly; never let a developer .env flip them to live.
        if "pytest" in sys.modules:
            return init_settings, env_settings, file_secret_settings
        return init_settings, env_settings, dotenv_settings, file_secret_settings

    @model_validator(mode="after")
    def _prefer_api_token(self) -> Settings:
        if self.canvas_api_token is None and self.canvas_access_token is not None:
            object.__setattr__(self, "canvas_api_token", self.canvas_access_token)
        return self

    def resolved_canvas_token(self) -> str:
        if self.canvas_api_token is None:
            return ""
        return self.canvas_api_token.get_secret_value().strip()

    def resolved_canvas_base_url(self) -> str:
        return (self.canvas_base_url or "").strip().rstrip("/")


class CanvasConfigError(RuntimeError):
    """Raised when live Canvas credentials are missing or incomplete."""


def require_canvas_live_credentials(settings: Settings | None = None) -> tuple[str, str]:
    """Return ``(base_url, token)`` or fail fast with a clear error.

    Never include the token value in the error message.
    """
    cfg = settings or get_settings()
    base = cfg.resolved_canvas_base_url()
    token = cfg.resolved_canvas_token()
    if base and token:
        return base, token
    missing: list[str] = []
    if not base:
        missing.append("CANVAS_BASE_URL")
    if not token:
        missing.append("CANVAS_API_TOKEN")
    raise CanvasConfigError(
        "Canvas live API is not configured. Set "
        + " and ".join(missing)
        + " in the environment or backend/.env "
        "(see backend/.env.example)."
    )


def canvas_credentials_or_none(settings: Settings | None = None) -> tuple[str, str] | None:
    """Return live credentials when both are set; None when both absent.

    Fail fast if only one of the two is present (misconfiguration).
    """
    cfg = settings or get_settings()
    base = cfg.resolved_canvas_base_url()
    token = cfg.resolved_canvas_token()
    if base and token:
        return base, token
    if base or token:
        missing = "CANVAS_API_TOKEN" if base and not token else "CANVAS_BASE_URL"
        raise CanvasConfigError(
            f"Canvas is misconfigured: {missing} is missing. "
            "Set both CANVAS_BASE_URL and CANVAS_API_TOKEN, or neither."
        )
    return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
