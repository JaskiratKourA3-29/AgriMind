"""
AgriMind Centralized Database Connection Pool.
Provides high-performance persistent connection pooling for Neon PostgreSQL
and connection management for local SQLite.
Eliminates TCP/SSL handshake latency (1.5s - 1.8s) on every database query.
"""
import os
import sqlite3
import threading
import urllib.parse
from contextlib import contextmanager
from typing import Optional, Any

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import pool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


_POOL_LOCK = threading.Lock()
_PG_POOL: Optional[Any] = None
_LAST_DB_URL: Optional[str] = None


def _normalize_pg_url(db_url: str) -> str:
    """Normalizes Neon connection string for Windows DNS and pooler compatibility."""
    if "-pooler" in db_url:
        parsed = urllib.parse.urlparse(db_url)
        netloc = parsed.netloc.replace("-pooler", "")
        return urllib.parse.urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
    return db_url


def get_pg_pool(db_url: str) -> Optional[Any]:
    """Returns or initializes the singleton ThreadedConnectionPool for PostgreSQL."""
    global _PG_POOL, _LAST_DB_URL
    if not PSYCOPG2_AVAILABLE:
        return None

    clean_url = _normalize_pg_url(db_url)
    if _PG_POOL is None or _LAST_DB_URL != clean_url:
        with _POOL_LOCK:
            if _PG_POOL is None or _LAST_DB_URL != clean_url:
                if _PG_POOL is not None:
                    try:
                        _PG_POOL.closeall()
                    except Exception:
                        pass
                _PG_POOL = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=6,
                    dsn=clean_url,
                    sslmode="require"
                )
                _LAST_DB_URL = clean_url
    return _PG_POOL


@contextmanager
def get_db_connection(db_path: str):
    """
    Context manager that yields an active database connection.
    For PostgreSQL: borrows from the connection pool, validates health, commits on exit, returns to pool.
    For SQLite: connects with standard timeout and row factory.
    """
    is_postgres = str(db_path).startswith("postgres://") or str(db_path).startswith("postgresql://")

    if is_postgres:
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("PostgreSQL specified but psycopg2 is not installed.")

        pg_pool = get_pg_pool(db_path)
        conn = None
        try:
            conn = pg_pool.getconn()
            # Verify connection is alive and clean
            if conn.closed != 0:
                pg_pool.putconn(conn, close=True)
                conn = pg_pool.getconn()
            try:
                conn.rollback()
            except Exception:
                try:
                    pg_pool.putconn(conn, close=True)
                except Exception:
                    pass
                conn = pg_pool.getconn()

            conn.autocommit = False
            yield conn
            conn.commit()
        except Exception:
            if conn is not None and conn.closed == 0:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if conn is not None and pg_pool is not None:
                try:
                    pg_pool.putconn(conn)
                except Exception:
                    pass
    else:
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
