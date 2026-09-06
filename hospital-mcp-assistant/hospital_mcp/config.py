"""Environment-based configuration for the MCP server and Groq host."""

from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

from .errors import ConfigurationError


load_dotenv()


def _read_positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc

    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    user: str
    password: str
    database: str
    pool_size: int
    connect_timeout: int


@dataclass(frozen=True)
class HostSettings:
    groq_api_key: str
    groq_model: str


def load_database_settings() -> DatabaseSettings:
    """Load database settings used only by the MCP server process."""

    return DatabaseSettings(
        host=os.getenv("MYSQL_HOST", "127.0.0.1").strip(),
        port=_read_positive_int("MYSQL_PORT", 3306),
        user=os.getenv("MYSQL_USER", "hospital_app").strip(),
        password=os.getenv("MYSQL_PASSWORD", "hospital_password"),
        database=os.getenv("MYSQL_DATABASE", "hospital_mcp").strip(),
        pool_size=_read_positive_int("MYSQL_POOL_SIZE", 5),
        connect_timeout=_read_positive_int("MYSQL_CONNECT_TIMEOUT", 10),
    )


def load_host_settings() -> HostSettings:
    """Load settings required by the user-facing Groq host."""

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key == "replace_with_your_groq_api_key":
        raise ConfigurationError(
            "GROQ_API_KEY is missing. Copy .env.example to .env and add your key."
        )

    return HostSettings(
        groq_api_key=api_key,
        groq_model=os.getenv(
            "GROQ_MODEL", "llama-3.3-70b-versatile"
        ).strip(),
    )

