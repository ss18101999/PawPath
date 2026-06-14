"""Environment configuration for Meta Marketing API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(ValueError):
    """Raised when required Meta credentials are missing or invalid."""


@dataclass(frozen=True)
class MetaConfig:
    app_id: str
    app_secret: str
    access_token: str
    ad_account_id: str

    @property
    def normalized_ad_account_id(self) -> str:
        account_id = self.ad_account_id.strip()
        if account_id.startswith("act_"):
            return account_id
        return f"act_{account_id}"


def _find_env_file() -> Path | None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def load_config(*, env_file: Path | None = None) -> MetaConfig:
    """Load Meta credentials from environment / .env file."""
    path = env_file or _find_env_file()
    if path:
        load_dotenv(path)

    required = {
        "META_APP_ID": os.getenv("META_APP_ID"),
        "META_APP_SECRET": os.getenv("META_APP_SECRET"),
        "META_ACCESS_TOKEN": os.getenv("META_ACCESS_TOKEN"),
        "META_AD_ACCOUNT_ID": os.getenv("META_AD_ACCOUNT_ID"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise ConfigError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Copy .env.example values into your .env file."
        )

    return MetaConfig(
        app_id=required["META_APP_ID"] or "",
        app_secret=required["META_APP_SECRET"] or "",
        access_token=required["META_ACCESS_TOKEN"] or "",
        ad_account_id=required["META_AD_ACCOUNT_ID"] or "",
    )
