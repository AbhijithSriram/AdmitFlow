"""The test-database safeguards (tests/db_safety.py). None of these tests needs, or touches, a database:
the checks are plain functions, and the two subprocess tests are refused before any connection is made."""
import os
import pathlib
import subprocess
import sys

import pytest

from tests import db_safety as safety
from tests.db_safety import UnsafeTestDatabase

BACKEND = pathlib.Path(__file__).resolve().parents[1]
OK = "postgresql://u:p@localhost:5432/admitflow_test"


# ------------------------------------------------------- same database as DATABASE_URL
@pytest.mark.parametrize("a, b", [
    (OK, OK),
    (OK, "postgresql+psycopg2://u2:p2@localhost:5432/admitflow_test"),   # driver and credentials differ
    (OK, "postgresql://u:p@127.0.0.1:5432/admitflow_test"),              # localhost == 127.0.0.1
    (OK, "postgresql://u:p@localhost/admitflow_test"),                   # default port
])
def test_same_database_is_recognised(a, b):
    assert safety.same_database(a, b)


@pytest.mark.parametrize("b", [
    "postgresql://u:p@localhost:5432/admitflow",            # same server, different database
    "postgresql://u:p@localhost:5433/admitflow_test",       # different port
    "postgresql://u:p@db.internal:5432/admitflow_test",     # different host
])
def test_different_databases_are_not_the_same(b):
    assert not safety.same_database(OK, b)


def test_refuses_when_test_url_is_the_real_database_url():
    with pytest.raises(UnsafeTestDatabase, match="same database as DATABASE_URL"):
        safety.check_test_url(OK, [OK])
    with pytest.raises(UnsafeTestDatabase, match="same database as DATABASE_URL"):
        safety.check_test_url(OK, ["postgresql://x:y@localhost:5432/other", OK])   # any of them


def test_a_separate_local_test_database_is_allowed():
    safety.check_test_url(OK, ["postgresql://u:p@localhost:5432/admitflow"])
    safety.check_test_url(OK, [])


def test_refuses_when_test_url_is_missing():
    with pytest.raises(UnsafeTestDatabase, match="not set"):
        safety.check_test_url(None, [])


# ------------------------------------------------------------------------ host checks
@pytest.mark.parametrize("url", [
    "postgresql://u:p@localhost:5432/admitflow_test",
    "postgresql://u:p@127.0.0.1:5432/admitflow_test",
    "postgresql://u:p@[::1]:5432/admitflow_test",
    "postgresql:///admitflow_test",                                        # local socket, no host
    "postgresql:///admitflow_test?host=/var/run/postgresql",               # socket directory
    "postgresql+psycopg2://u:p@LOCALHOST/admitflow_test",
])
def test_local_hosts_are_allowed(url):
    safety.check_test_url(url, [])


@pytest.mark.parametrize("url", [
    "postgresql://u:p@db.example.com:5432/admitflow_test",
    "postgresql://u:p@10.0.0.7:5432/admitflow_test",
    "postgresql:///admitflow_test?host=db.example.com",
])
def test_remote_hosts_are_refused_unless_explicitly_allowed(url):
    with pytest.raises(UnsafeTestDatabase, match="non-local host"):
        safety.check_test_url(url, [])
    with pytest.raises(UnsafeTestDatabase, match="non-local host"):
        safety.check_test_url(url, [], allow_remote=False)
    safety.check_test_url(url, [], allow_remote=True)          # ALLOW_REMOTE_TEST_DB=1


def test_allow_remote_does_not_switch_off_the_same_database_check():
    remote = "postgresql://u:p@db.example.com:5432/admitflow_test"
    with pytest.raises(UnsafeTestDatabase, match="same database as DATABASE_URL"):
        safety.check_test_url(remote, [remote], allow_remote=True)


# ------------------------------------------------------------- database name (server-reported)
@pytest.mark.parametrize("name", ["admitflow_test", "ADMITFLOW_TEST", "Test_DB", "test"])
def test_names_containing_test_are_allowed(name):
    safety.check_database_name(name)


@pytest.mark.parametrize("name", ["admitflow", "postgres", "admitflow_dev", "", None])
def test_names_without_test_are_refused(name):
    with pytest.raises(UnsafeTestDatabase, match="does not contain 'test'"):
        safety.check_database_name(name)


# ------------------------------------------------------------ where DATABASE_URL comes from
def test_database_url_is_read_from_the_environment_and_from_dot_env(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://u:p@localhost:5432/from_dot_env\nOTHER=1\n")
    urls = safety.configured_database_urls(env={"DATABASE_URL": "postgresql://u:p@localhost:5432/from_env"},
                                           env_file=env_file)
    assert urls == ["postgresql://u:p@localhost:5432/from_env", "postgresql://u:p@localhost:5432/from_dot_env"]


def test_no_database_url_anywhere_gives_an_empty_list(tmp_path):
    assert safety.configured_database_urls(env={}, env_file=tmp_path / "missing.env") == []


# ------------------------------------------------- the checks really run before DROP SCHEMA
def test_conftest_runs_every_check_before_the_destructive_sql():
    src = (BACKEND / "tests" / "conftest.py").read_text()
    drop = src.index("DROP SCHEMA public CASCADE")
    assert src.index("check_test_url(") < src.index("psycopg2.connect(") < src.index("SELECT current_database()") \
        < src.index("check_database_name(") < drop
    assert src.count("DROP SCHEMA public CASCADE") == 1       # the only destructive statement


def _run_pytest_with(env_extra: dict):
    """Run one DB-using test file in a child pytest whose TEST_DATABASE_URL we control."""
    env = {k: v for k, v in os.environ.items() if k not in ("TEST_DATABASE_URL", "DATABASE_URL", "ALLOW_REMOTE_TEST_DB")}
    env.update(env_extra)
    return subprocess.run([sys.executable, "-m", "pytest", "tests/test_admin_tests.py", "-x", "-q",
                           "-p", "no:cacheprovider"], cwd=BACKEND, env=env, capture_output=True, text=True, timeout=120)


def test_pytest_refuses_to_start_when_test_and_real_database_are_the_same():
    url = "postgresql://u:p@localhost:5999/prod_copy"          # nothing listens on 5999; refused before connecting
    r = _run_pytest_with({"TEST_DATABASE_URL": url, "DATABASE_URL": url})
    assert r.returncode == 2, r.stdout + r.stderr
    assert "Refusing to run the tests" in r.stdout + r.stderr and "same database as DATABASE_URL" in r.stdout + r.stderr


def test_pytest_refuses_to_start_on_a_remote_host():
    r = _run_pytest_with({"TEST_DATABASE_URL": "postgresql://u:p@db.example.invalid:5432/admitflow_test"})
    assert r.returncode == 2, r.stdout + r.stderr
    assert "non-local host" in r.stdout + r.stderr and "ALLOW_REMOTE_TEST_DB=1" in r.stdout + r.stderr
