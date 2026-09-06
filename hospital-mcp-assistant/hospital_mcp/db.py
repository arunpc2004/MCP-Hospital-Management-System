"""Lazy MySQL connection-pool management for the MCP server."""

from __future__ import annotations

from contextlib import contextmanager
from threading import Lock
from typing import Any, Iterator

from mysql.connector.pooling import MySQLConnectionPool

from .config import DatabaseSettings


class MySQLDatabase:
    """Create the MySQL pool on first use and return connections safely."""

    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings
        self._pool: MySQLConnectionPool | None = None
        self._pool_lock = Lock()

    def _get_pool(self) -> MySQLConnectionPool:
        if self._pool is None:
            with self._pool_lock:
                if self._pool is None:
                    self._pool = MySQLConnectionPool(
                        pool_name=f"hospital_mcp_{id(self)}",
                        pool_size=self._settings.pool_size,
                        pool_reset_session=True,
                        host=self._settings.host,
                        port=self._settings.port,
                        user=self._settings.user,
                        password=self._settings.password,
                        database=self._settings.database,
                        connection_timeout=self._settings.connect_timeout,
                        autocommit=False,
                    )
        return self._pool

    @contextmanager
    def connection(self) -> Iterator[Any]:
        connection = self._get_pool().get_connection()
        try:
            yield connection
        finally:
            if connection.is_connected():
                connection.close()

