"""Configuration helpers for the Telegram music bot.

The original bot implementation in the prompt hard-coded several sensitive
values such as API credentials and tokens.  Storing secrets in source control is
problematic for a number of reasons:

* It makes rotating credentials difficult because any rotation requires a code
  change.
* Secrets end up in the repository history which is risky if the code is ever
  shared.
* The configuration cannot be customised for different environments without
  editing the source.

To address these concerns we provide a small utility for loading the required
settings from environment variables.  This makes the runtime behaviour
configurable while keeping the project free from hard-coded secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Iterable, Mapping, MutableMapping, Optional


class ConfigError(ValueError):
    """Raised when the configuration cannot be loaded correctly."""


@dataclass(frozen=True)
class BotConfig:
    """Container for the Telegram bot configuration.

    Attributes:
        api_id: Numeric identifier for the Telegram API application.
        api_hash: Secret hash for the Telegram API application.
        bot_token: Token for authenticating the bot with Telegram.
        admin_username: Optional username that is allowed to trigger privileged
            commands such as force-playing or stopping music.
        download_dir: Directory where downloaded audio files should be stored.
    """

    api_id: int
    api_hash: str
    bot_token: str
    admin_username: Optional[str] = None
    download_dir: str = "music"

    def ensure_download_dir(self) -> str:
        """Ensure that the download directory exists.

        Returns:
            The absolute path to the directory after ensuring it exists.
        """

        path = os.path.abspath(self.download_dir)
        os.makedirs(path, exist_ok=True)
        return path


_DEFAULT_ENV_KEYS: Mapping[str, Iterable[str]] = {
    "api_id": ("TELEGRAM_API_ID", "API_ID"),
    "api_hash": ("TELEGRAM_API_HASH", "API_HASH"),
    "bot_token": ("TELEGRAM_BOT_TOKEN", "BOT_TOKEN"),
    "admin_username": ("TELEGRAM_ADMIN_USERNAME", "ADMIN_USERNAME"),
    "download_dir": ("TELEGRAM_MUSIC_DIR", "MUSIC_DIR", "DOWNLOAD_DIR"),
}


def _normalise_env(env: Optional[Mapping[str, str]]) -> Mapping[str, str]:
    """Return a case-sensitive mapping backed by strings.

    The helper accepts ``None`` for convenience (falling back to
    :data:`os.environ`) and coerces values to plain ``str`` instances which is
    useful when tests provide mutable mappings with different types.
    """

    if env is None:
        env = os.environ
    # ``os.environ`` already behaves like ``Mapping[str, str]`` but tests might
    # pass dictionaries with other value types.  Coerce everything to ``str`` for
    # predictable behaviour.
    return {key: str(value) for key, value in env.items()}


def _get_env_value(
    env: Mapping[str, str],
    keys: Iterable[str],
    *,
    required: bool,
) -> Optional[str]:
    """Retrieve the first non-empty value for ``keys`` from ``env``."""

    for key in keys:
        value = env.get(key)
        if value is not None:
            value = value.strip()
            if value:
                return value
    if required:
        raise ConfigError(
            "Missing required environment variable. Tried: "
            + ", ".join(keys)
        )
    return None


def load_config_from_env(
    env: Optional[Mapping[str, str]] = None,
    *,
    overrides: Optional[MutableMapping[str, str]] = None,
) -> BotConfig:
    """Load the bot configuration from environment variables.

    Args:
        env: Optional mapping of environment variables.  When omitted the
            process environment is used.
        overrides: Optional mapping allowing callers (for example tests) to
            inject or override values after they have been read from ``env``.

    Returns:
        A :class:`BotConfig` populated with the resolved configuration values.

    Raises:
        ConfigError: If a required environment variable is missing or invalid.
    """

    normalised_env = _normalise_env(env)
    if overrides:
        for key, value in overrides.items():
            # ``str(None)`` would result in "None" which is undesirable, so we
            # filter out ``None`` explicitly.
            if value is None:
                normalised_env.pop(key, None)
            else:
                normalised_env[key] = str(value)

    api_id_raw = _get_env_value(normalised_env, _DEFAULT_ENV_KEYS["api_id"], required=True)
    try:
        api_id = int(api_id_raw)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive guard
        raise ConfigError("API_ID must be an integer") from exc

    api_hash = _get_env_value(normalised_env, _DEFAULT_ENV_KEYS["api_hash"], required=True)
    bot_token = _get_env_value(normalised_env, _DEFAULT_ENV_KEYS["bot_token"], required=True)
    admin_username = _get_env_value(
        normalised_env,
        _DEFAULT_ENV_KEYS["admin_username"],
        required=False,
    )
    download_dir = _get_env_value(
        normalised_env,
        _DEFAULT_ENV_KEYS["download_dir"],
        required=False,
    ) or BotConfig.download_dir

    return BotConfig(
        api_id=api_id,
        api_hash=api_hash,
        bot_token=bot_token,
        admin_username=admin_username,
        download_dir=download_dir,
    )


__all__ = ["BotConfig", "ConfigError", "load_config_from_env"]
