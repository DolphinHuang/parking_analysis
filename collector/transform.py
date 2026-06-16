from __future__ import annotations

from datetime import datetime
from typing import Any


REQUIRED_FIELDS = (
    "section_id",
    "ps_id",
    "ps_type",
    "latitude",
    "longitude",
    "status",
)


def _to_optional_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _to_optional_int(value: Any) -> int | None:
    text = _to_optional_text(value)

    if text is None:
        return None

    try:
        return int(float(text))
    except ValueError:
        return None


def _to_optional_float(value: Any) -> float | None:
    text = _to_optional_text(value)

    if text is None:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def validate_required_fields(
    resolved_fields: dict[str, str | None],
) -> None:
    missing_fields = [
        field_name
        for field_name in REQUIRED_FIELDS
        if resolved_fields.get(field_name) is None
    ]

    if missing_fields:
        raise ValueError(
            "寫入資料庫前缺少必要欄位："
            + ", ".join(missing_fields)
        )


def normalize_records_for_db(
    records: list[dict[str, Any]],
    resolved_fields: dict[str, str | None],
    collected_at: datetime,
) -> list[tuple[object, ...]]:
    validate_required_fields(resolved_fields)

    normalized_rows: list[tuple[object, ...]] = []

    section_id_field = resolved_fields["section_id"]
    ps_id_field = resolved_fields["ps_id"]
    ps_type_field = resolved_fields["ps_type"]
    latitude_field = resolved_fields["latitude"]
    longitude_field = resolved_fields["longitude"]
    status_field = resolved_fields["status"]

    for record in records:
        section_id = _to_optional_text(record.get(section_id_field))
        ps_id = _to_optional_text(record.get(ps_id_field))

        if section_id is None or ps_id is None:
            continue

        normalized_rows.append(
            (
                collected_at,
                section_id,
                ps_id,
                _to_optional_int(record.get(ps_type_field)),
                _to_optional_float(record.get(latitude_field)),
                _to_optional_float(record.get(longitude_field)),
                _to_optional_int(record.get(status_field)),
                _to_optional_text(record.get("CountyCode")),
                _to_optional_text(record.get("AgencyCodes")),
            )
        )

    if not normalized_rows:
        raise ValueError("沒有任何資料列可寫入資料庫。")

    return normalized_rows
