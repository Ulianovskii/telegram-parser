import os
import sqlite3
import subprocess
import sys


def test_migration_repeat_and_cleanup(tmp_path):
    path = tmp_path / "migrated.db"
    env = dict(os.environ, AUTH_DATABASE_URL=f"sqlite+aiosqlite:///{path}")
    for command in ("migrate", "migrate", "cleanup"):
        subprocess.run(
            [sys.executable, "-m", "product_auth.cli", command],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    with sqlite3.connect(path) as db:
        names = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {
        "auth_users",
        "auth_sessions",
        "auth_login_flows",
        "auth_alembic_version",
    } <= names
