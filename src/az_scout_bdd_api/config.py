"""Standalone API configuration.

Reads database connection parameters from environment variables.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    dbname: str = "azscout"
    user: str = "azscout"
    password: str = "azscout"
    sslmode: str = "disable"
    auth_method: str = "password"  # "password" or "msi"
    client_id: str = ""  # MSI client ID (optional, for user-assigned identity)

    @property
    def dsn(self) -> str:
        from urllib.parse import quote

        _CONN_OPTS = (
            "connect_timeout=10"
            " keepalives=1 keepalives_idle=30"
            " keepalives_interval=10 keepalives_count=5"
        )

        if self.auth_method == "msi":
            return (
                f"host={self.host} port={self.port} dbname={self.dbname}"
                f" user={self.user} sslmode={self.sslmode} {_CONN_OPTS}"
            )
        return (
            f"postgresql://{quote(self.user, safe='')}:{quote(self.password, safe='')}"
            f"@{self.host}:{self.port}/{self.dbname}"
            f"?sslmode={self.sslmode}&connect_timeout=10"
            f"&keepalives=1&keepalives_idle=30"
            f"&keepalives_interval=10&keepalives_count=5"
        )


@dataclass
class ApiConfig:
    database: DatabaseConfig


_config: ApiConfig | None = None


def load_config() -> ApiConfig:
    """Load configuration from environment variables or defaults."""
    db_cfg = DatabaseConfig(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "azscout"),
        user=os.environ.get("POSTGRES_USER", "azscout"),
        password=os.environ.get("POSTGRES_PASSWORD", "azscout"),
        sslmode=os.environ.get("POSTGRES_SSLMODE", "disable"),
        auth_method=os.environ.get("POSTGRES_AUTH_METHOD", "password"),
        client_id=os.environ.get("AZURE_CLIENT_ID", ""),
    )
    logger.info("Loaded API config from environment variables")
    return ApiConfig(database=db_cfg)


def get_config() -> ApiConfig:
    """Return cached config, loading on first call."""
    global _config
    if _config is None:
        _config = load_config()
    return _config
