from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import psycopg
from psycopg import Connection


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = PROJECT_ROOT / "sql" / "schema.sql"


@dataclass(frozen=True)
class DatabaseSettings:
    host: str   
    port: int
    name: str
    user: str
    password: str
    sslmode: str

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        host = os.getenv("DB_HOST", "").strip()
        name = os.getenv("DB_NAME", "").strip()
        user = os.getenv("DB_USER", "").strip()
        password = os.getenv("DB_PASSWORD", "").strip()
        sslmode = os.getenv("DB_SSLMODE", "disable").strip() or "disable"

        if not host:
            raise ValueError("找不到 DB_HOST。")
        if not name:
            raise ValueError("找不到 DB_NAME。")
        if not user:
            raise ValueError("找不到 DB_USER。")
        if not password:
            raise ValueError("找不到 DB_PASSWORD。")

        try:
            port = int(os.getenv("DB_PORT", "5432"))
        except ValueError as exc:
            raise ValueError("DB_PORT 必須是整數。") from exc

        if port <= 0:
            raise ValueError("DB_PORT 必須大於 0。")

        return cls(
            host=host,
            port=port,
            name=name,
            user=user,
            password=password,
            sslmode=sslmode,
        )


def connect_database(settings: DatabaseSettings) -> Connection:
    return psycopg.connect(
        host=settings.host,
        port=settings.port,
        dbname=settings.name,
        user=settings.user,
        password=settings.password,
        sslmode=settings.sslmode,
    )


def _load_sql_statements(schema_file: Path) -> list[str]:
    if not schema_file.exists():
        raise FileNotFoundError(f"找不到 schema 檔案：{schema_file}")

    buffer: list[str] = []
    statements: list[str] = []

    for raw_line in schema_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("--"):
            continue

        buffer.append(raw_line)

        if line.endswith(";"):
            statements.append("\n".join(buffer).strip())
            buffer.clear()

    if buffer:
        statements.append("\n".join(buffer).strip())

    return statements


def ensure_schema(connection: Connection) -> None:
    with connection.cursor() as cursor:
        for statement in _load_sql_statements(SCHEMA_FILE):
            cursor.execute(statement)


def insert_parking_records(
    connection: Connection,
    rows: Iterable[tuple[object, ...]],
) -> int:
    insert_sql = """
        INSERT INTO parking_status_raw (
            collected_at_utc,
            section_id,
            ps_id,
            ps_type,
            lat,
            lng,
            status,
            county_code,
            agency_codes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (collected_at_utc, section_id, ps_id) DO UPDATE
        SET
            section_id = EXCLUDED.section_id,
            ps_type = EXCLUDED.ps_type,
            lat = EXCLUDED.lat,
            lng = EXCLUDED.lng,
            status = EXCLUDED.status,
            county_code = EXCLUDED.county_code,
            agency_codes = EXCLUDED.agency_codes
    """

    row_list = list(rows)

    if not row_list:
        return 0

    with connection.cursor() as cursor:
        cursor.executemany(insert_sql, row_list)

    return len(row_list)
