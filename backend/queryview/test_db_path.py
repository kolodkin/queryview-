"""Where the SQLite store lives.

The default used to be package-relative (`Path(__file__).parent.parent`), which
meant `backend/queryview.db` in a checkout but `<site-packages>/queryview.db`
once the wheel shipped — under `uvx`, that is inside uv's *cache*, where a
`uv cache clean` or a version bump silently takes the DB with it. The default
is now the platform's user-data directory.
"""

from __future__ import annotations

from pathlib import Path

import platformdirs

import queryview
from queryview.connect import _db_path, _key_path


def test_db_path_defaults_to_user_data_dir(monkeypatch):
    monkeypatch.delenv("DB_PATH", raising=False)
    expected = Path(platformdirs.user_data_dir("queryview")) / "queryview.db"
    assert _db_path() == expected


def test_db_path_is_not_inside_the_installed_package(monkeypatch):
    """The regression: a package-relative default puts user data in
    site-packages (and under uvx, in a disposable cache directory)."""
    monkeypatch.delenv("DB_PATH", raising=False)
    package_root = Path(queryview.__file__).resolve().parent.parent
    assert package_root not in _db_path().resolve().parents


def test_db_path_env_var_still_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "custom.db"))
    assert _db_path() == tmp_path / "custom.db"
    # The key file follows the DB unless DB_KEY_PATH says otherwise.
    monkeypatch.delenv("DB_KEY_PATH", raising=False)
    assert _key_path() == tmp_path / "custom.db.key"


def test_ensure_schema_creates_a_missing_data_dir(monkeypatch, tmp_path):
    """The user-data dir does not exist on a fresh install, so startup has to
    create it — SQLite will not create a missing parent directory."""
    import asyncio

    import queryview.connect as c

    target = tmp_path / "fresh" / "nested" / "queryview.db"
    monkeypatch.setenv("DB_PATH", str(target))
    monkeypatch.setenv("DB_KEY_PATH", str(target.with_suffix(".db.key")))
    monkeypatch.setattr(c, "_engine", None)
    monkeypatch.setattr(c, "_schema_ready", False)
    assert not target.parent.exists()

    asyncio.run(c._ensure_schema())

    assert target.parent.is_dir()
