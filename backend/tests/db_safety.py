"""Checks that must pass before the test setup runs DROP SCHEMA on TEST_DATABASE_URL.

The test setup wipes the whole `public` schema of the database it points at. These checks make sure
that can only ever be a dedicated, local, test database. They are plain functions (no database
needed) so tests/test_db_safety.py can exercise them without touching any real database.

  1. TEST_DATABASE_URL must not be the same database as DATABASE_URL (environment or backend/.env).
  2. The host must be local, unless ALLOW_REMOTE_TEST_DB=1 is set on purpose.
  3. The database's own name (SELECT current_database()) must contain "test".
"""
import os
import pathlib
from urllib.parse import parse_qs, urlsplit

LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1"}
ENV_FILE = pathlib.Path(__file__).resolve().parents[1] / ".env"


class UnsafeTestDatabase(Exception):
    """The configured test database is not safe to wipe. The message says why and what to do."""


def _parts(url: str) -> tuple[str, int, str]:
    """(host, port, database name) of a PostgreSQL URL; an empty host means the local socket."""
    u = urlsplit(url.replace("postgresql+psycopg2://", "postgresql://"))
    host = (u.hostname or (parse_qs(u.query).get("host") or [""])[0]).lower()
    if host.startswith("/"):          # a unix-socket directory
        host = ""
    return host, u.port or 5432, u.path.lstrip("/")


def _is_local(host: str) -> bool:
    return host in LOCAL_HOSTS


def same_database(a: str, b: str) -> bool:
    """True when both URLs point at the same server and database (localhost == 127.0.0.1)."""
    (ha, pa, da), (hb, pb, db_) = _parts(a), _parts(b)
    if _is_local(ha):
        ha = "localhost"
    if _is_local(hb):
        hb = "localhost"
    return (ha, pa, da) == (hb, pb, db_)


def configured_database_urls(env=None, env_file: pathlib.Path = ENV_FILE) -> list[str]:
    """The app's real DATABASE_URL, from the environment and from backend/.env if it exists."""
    env = os.environ if env is None else env
    urls = [env.get("DATABASE_URL")]
    try:
        from dotenv import dotenv_values
        urls.append(dotenv_values(env_file).get("DATABASE_URL") if env_file.exists() else None)
    except ImportError:  # python-dotenv is in requirements.txt; be safe if it is missing
        pass
    return [u for u in urls if u]


def check_test_url(test_url: str | None, database_urls=(), allow_remote: bool = False) -> None:
    """Checks 1 and 2: they need only the URLs, so they run before any connection is made."""
    if not test_url:
        raise UnsafeTestDatabase("TEST_DATABASE_URL is not set.")
    for real in database_urls:
        if same_database(test_url, real):
            raise UnsafeTestDatabase(
                "TEST_DATABASE_URL points at the same database as DATABASE_URL. "
                "Create a separate database for tests (for example `createdb admitflow_test`).")
    host = _parts(test_url)[0]
    if not _is_local(host) and not allow_remote:
        raise UnsafeTestDatabase(
            f"TEST_DATABASE_URL points at a non-local host ({host}). The test setup wipes the database. "
            "If this really is a disposable remote test database, set ALLOW_REMOTE_TEST_DB=1.")


def check_database_name(name: str | None) -> None:
    """Check 3: the name reported by the server itself (SELECT current_database()) must say 'test'."""
    if not name or "test" not in name.lower():
        raise UnsafeTestDatabase(
            f"The database is named {name!r}, which does not contain 'test'. "
            "The test setup wipes the whole public schema, so only a database named like "
            "'admitflow_test' is allowed.")
