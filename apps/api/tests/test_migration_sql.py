from __future__ import annotations

from apps.api.migrations.sql import split_sql_statements


def test_split_sql_statements_preserves_function_bodies() -> None:
    statements = split_sql_statements(
        "CREATE FUNCTION f() RETURNS void AS $$ BEGIN SELECT 1; END; $$; SELECT 2;"
    )

    assert len(statements) == 2
    assert statements[0].startswith("CREATE FUNCTION f()")
    assert "SELECT 1;" in statements[0]
    assert statements[1] == "SELECT 2"


def test_split_sql_statements_preserves_quoted_semicolon() -> None:
    statements = split_sql_statements("SELECT 'a; b'; SELECT 2;")

    assert statements == ("SELECT 'a; b'", "SELECT 2")
