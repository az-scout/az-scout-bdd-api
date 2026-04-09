"""Lightweight async DB helper for the API (query-only).

Supports two auth modes:
- ``password``: classic user/password DSN.
- ``msi``: Azure Managed Identity — acquires an OAuth2 token from
  ``azure.identity.DefaultAzureCredential`` and passes it as the
  password on every new physical connection opened by the pool.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import psycopg
import psycopg_pool

from az_scout_bdd_api.config import DatabaseConfig, get_config

logger = logging.getLogger(__name__)

_pool: psycopg_pool.AsyncConnectionPool | None = None

_PG_ENTRA_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"

# Cached credential + token to avoid re-authenticating on every connection.
_credential: Any = None
_credential_client_id: str = ""
_cached_token: str = ""
_cached_token_expires: float = 0.0
_TOKEN_REFRESH_MARGIN = 300  # refresh 5 min before expiry


def _get_credential(client_id: str = "") -> Any:
    """Return a cached DefaultAzureCredential."""
    global _credential, _credential_client_id
    if _credential is None or _credential_client_id != client_id:
        from azure.identity import DefaultAzureCredential

        kwargs: dict[str, str] = {}
        if client_id:
            kwargs["managed_identity_client_id"] = client_id
        _credential = DefaultAzureCredential(**kwargs)
        _credential_client_id = client_id
    return _credential


def _get_token(cfg: DatabaseConfig) -> str:
    """Return a valid Entra ID token, refreshing only when near expiry."""
    global _cached_token, _cached_token_expires
    now = time.time()
    if _cached_token and now < _cached_token_expires - _TOKEN_REFRESH_MARGIN:
        return _cached_token

    credential = _get_credential(cfg.client_id)
    result = credential.get_token(_PG_ENTRA_SCOPE)
    _cached_token = result.token
    _cached_token_expires = result.expires_on
    logger.debug("Acquired fresh PG Entra token (expires in %ds)", int(result.expires_on - now))
    return _cached_token


async def _check_conn(conn: psycopg.AsyncConnection[Any]) -> None:
    """Discard broken connections before handing them to callers.

    Called by the pool on checkout.  If the underlying socket is closed
    or the connection is in an error state, raise to force the pool to
    open a fresh one instead.
    """
    if conn.broken:
        raise psycopg.OperationalError("connection is broken")
    if conn.closed:
        raise psycopg.OperationalError("connection is closed")


async def ensure_pool() -> psycopg_pool.AsyncConnectionPool:
    global _pool
    if _pool is not None:
        return _pool

    cfg = get_config().database
    logger.debug(
        "DSN (redacted password): host=%s port=%s db=%s user=%s ssl=%s auth=%s",
        cfg.host,
        cfg.port,
        cfg.dbname,
        cfg.user,
        cfg.sslmode,
        cfg.auth_method,
    )

    conninfo = cfg.dsn

    if cfg.auth_method == "msi":
        # NullConnectionPool opens a fresh connection per checkout,
        # so the check callback is less critical but still useful.
        pool: psycopg_pool.AsyncConnectionPool = psycopg_pool.AsyncNullConnectionPool(
            conninfo=conninfo,
            max_size=20,
            open=False,
            kwargs=lambda: {"password": _get_token(cfg)},
            reconnect_timeout=30,
            check=_check_conn,
        )
        logger.info("DB NullPool configured with Managed Identity auth (token auto-refresh)")
    else:
        pool = psycopg_pool.AsyncConnectionPool(
            conninfo=conninfo,
            min_size=3,
            max_size=20,
            open=False,
            reconnect_timeout=30,
            check=_check_conn,
        )
        logger.info("DB pool configured with password auth")

    await pool.open()
    _pool = pool
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_conn() -> AsyncIterator[psycopg.AsyncConnection[Any]]:
    pool = await ensure_pool()
    async with pool.connection() as conn:
        yield conn


async def is_healthy() -> bool:
    try:
        async with get_conn() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False
