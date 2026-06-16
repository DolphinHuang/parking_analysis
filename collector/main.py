from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from collector.api_test import (
    ENV_FILE,
    configure_logging,
    extract_records,
    fetch_api_data,
    get_timeout,
    resolve_fields,
    save_results,
    validate_records,
)
from collector.db import (
    DatabaseSettings,
    connect_database,
    ensure_schema,
    insert_parking_records,
)
from collector.transform import normalize_records_for_db


def main() -> int:
    load_dotenv(ENV_FILE)

    logger = configure_logging()

    api_url = os.getenv("TAICHUNG_PARKING_API_URL", "").strip()

    if not api_url:
        logger.error("找不到 TAICHUNG_PARKING_API_URL。")
        return 1

    collected_at = datetime.now(timezone.utc)

    try:
        timeout = get_timeout()
        db_settings = DatabaseSettings.from_env()

        payload = fetch_api_data(
            api_url=api_url,
            timeout=timeout,
            logger=logger,
        )

        records = extract_records(payload)
        logger.info("成功取得資料：%s 筆", f"{len(records):,}")

        resolved_fields = resolve_fields(records)

        validate_records(
            records=records,
            resolved_fields=resolved_fields,
            logger=logger,
        )

        normalized_rows = normalize_records_for_db(
            records=records,
            resolved_fields=resolved_fields,
            collected_at=collected_at,
        )

        json_path = save_results(
            payload=payload,
            collected_at=collected_at,
            logger=logger,
        )

        with connect_database(db_settings) as connection:
            ensure_schema(connection)
            inserted_rows = insert_parking_records(
                connection,
                normalized_rows,
            )
            connection.commit()

        logger.info("成功寫入資料庫：%s 筆", f"{inserted_rows:,}")

        print("\nCollector 執行完成。")
        print(f"資料筆數：{len(records):,}")
        print(f"寫入資料庫：{inserted_rows:,} 筆")
        print(f"JSON 檔案：{json_path}")
        print(f"擷取時間 UTC：{collected_at.isoformat()}")

        return 0

    except Exception:
        logger.exception("Collector 執行失敗。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
