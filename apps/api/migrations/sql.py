"""Asyncpg-safe SQL script execution for Alembic migrations."""

from __future__ import annotations

import re
from collections.abc import Iterator

from alembic import op

_DOLLAR_TAG = re.compile(r"\$[A-Za-z_0-9]*\$")


def split_sql_statements(script: str) -> tuple[str, ...]:
    """Split SQL on top-level semicolons while preserving quoted/function bodies."""

    statements: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    dollar_tag: str | None = None
    line_comment = False
    block_comment_depth = 0
    index = 0

    while index < len(script):
        character = script[index]
        if dollar_tag is not None:
            if script.startswith(dollar_tag, index):
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                dollar_tag = None
            else:
                buffer.append(character)
                index += 1
            continue
        if line_comment:
            buffer.append(character)
            index += 1
            if character == "\n":
                line_comment = False
            continue
        if block_comment_depth:
            if script.startswith("/*", index):
                buffer.extend("/*")
                block_comment_depth += 1
                index += 2
            elif script.startswith("*/", index):
                buffer.extend("*/")
                block_comment_depth -= 1
                index += 2
            else:
                buffer.append(character)
                index += 1
            continue
        if quote is not None:
            buffer.append(character)
            index += 1
            if character == quote:
                if index < len(script) and script[index] == quote:
                    buffer.append(script[index])
                    index += 1
                else:
                    quote = None
            continue
        if script.startswith("--", index):
            buffer.extend("--")
            line_comment = True
            index += 2
            continue
        if script.startswith("/*", index):
            buffer.extend("/*")
            block_comment_depth = 1
            index += 2
            continue
        if character in {"'", '"'}:
            quote = character
            buffer.append(character)
            index += 1
            continue
        if character == "$":
            match = _DOLLAR_TAG.match(script, index)
            if match is not None:
                dollar_tag = match.group(0)
                buffer.append(dollar_tag)
                index += len(dollar_tag)
                continue
        if character == ";":
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer.clear()
            index += 1
            continue
        buffer.append(character)
        index += 1

    statement = "".join(buffer).strip()
    if statement:
        statements.append(statement)
    return tuple(statements)


def execute_script(script: str) -> None:
    """Execute each SQL statement separately so asyncpg never prepares a batch."""

    for statement in split_sql_statements(script):
        op.execute(statement)


def iter_statements(script: str) -> Iterator[str]:
    """Expose statement splitting to migration tests without executing SQL."""

    yield from split_sql_statements(script)
