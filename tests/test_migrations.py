"""Regression coverage for additive migration of legacy user databases."""

from sqlalchemy import create_engine, inspect, text

import api


def test_legacy_user_rows_survive_password_hash_migration(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "legacy-careeros.db"
    legacy_engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr(api, "engine", legacy_engine)

    try:
        # This is the pre-authentication users table: no password_hash column yet.
        with legacy_engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE users ("
                    "id INTEGER PRIMARY KEY, "
                    "name VARCHAR(150) NOT NULL, "
                    "email VARCHAR(320) NOT NULL UNIQUE)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO users (id, name, email) "
                    "VALUES (1, 'Existing User', 'existing@example.com')"
                )
            )

        api.create_tables()

        columns = {column["name"] for column in inspect(legacy_engine).get_columns("users")}
        assert "password_hash" in columns

        with legacy_engine.connect() as connection:
            row = connection.execute(
                text("SELECT id, name, email, password_hash FROM users WHERE id = 1")
            ).one()

        assert row.id == 1
        assert row.name == "Existing User"
        assert row.email == "existing@example.com"
        assert row.password_hash is None
    finally:
        legacy_engine.dispose()
