from __future__ import annotations

import json
import logging
import os
import sys
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ---------------------------------------------------------
# 專案路徑
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENV_FILE = PROJECT_ROOT / ".env"
LOG_DIR = PROJECT_ROOT / "logs"
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


# ---------------------------------------------------------
# API 可能使用的欄位名稱
# ---------------------------------------------------------

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "section_id": (
        "Section_ID",
        "section_id",
        "SectionID",
    ),
    "ps_id": (
        "PS_ID",
        "ps_id",
        "PSID",
    ),
    "ps_type": (
        "PS_type",
        "ps_type",
        "PSType",
    ),
    "latitude": (
        "Lat",
        "lat",
        "latitude",
        "PS_Lat",
        "ps_lat",
    ),
    "longitude": (
        "Lng",
        "lng",
        "longitude",
        "PS_Lng",
        "ps_lng",
    ),
    "status": (
        "status",
        "Status",
        "STATUS",
    ),
}


def configure_logging() -> logging.Logger:
    """
    建立主控台與檔案日誌。

    logs/ 不需要事先建立，程式啟動時會自動建立。
    """

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("parking_api_test")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        LOG_DIR / "api_test.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_timeout() -> tuple[float, float]:
    """從環境變數取得連線逾時與讀取逾時設定。"""

    try:
        connect_timeout = float(
            os.getenv("REQUEST_CONNECT_TIMEOUT", "10")
        )
        read_timeout = float(
            os.getenv("REQUEST_READ_TIMEOUT", "60")
        )
    except ValueError as exc:
        raise ValueError(
            "REQUEST_CONNECT_TIMEOUT 與 "
            "REQUEST_READ_TIMEOUT 必須是數字。"
        ) from exc

    if connect_timeout <= 0 or read_timeout <= 0:
        raise ValueError("timeout 必須大於 0。")

    return connect_timeout, read_timeout


def build_http_session() -> requests.Session:
    """建立包含重試機制的 HTTP Session。"""

    retry_strategy = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)

    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update(
        {
            "Accept": "application/json, text/json, */*",
            "User-Agent": (
                "parking-analysis/1.0 "
                "(Feng Chia University academic project)"
            ),
        }
    )

    return session


def parse_response_content(response: requests.Response) -> Any:
    """
    將 API 回應解析成 Python 物件。

    支援：
    1. 一般 JSON
    2. 含 UTF-8 BOM 的 JSON
    3. ZIP 壓縮檔中的 JSON
    """

    content = response.content

    if not content:
        raise ValueError("API 回傳內容為空。")

    # ZIP 檔案通常以 PK 開頭
    if content.startswith(b"PK"):
        with zipfile.ZipFile(BytesIO(content)) as zip_file:
            json_files = [
                filename
                for filename in zip_file.namelist()
                if filename.lower().endswith(".json")
            ]

            if not json_files:
                raise ValueError(
                    "API 回傳 ZIP 檔，但 ZIP 中找不到 JSON 檔案。"
                )

            selected_file = json_files[0]

            with zip_file.open(selected_file) as file:
                text = file.read().decode("utf-8-sig")

            return json.loads(text)

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode(
            response.encoding or "utf-8",
            errors="replace",
        )

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        preview = text[:500].replace("\n", " ")

        raise ValueError(
            "API 回傳內容不是有效 JSON。\n"
            f"Content-Type："
            f"{response.headers.get('Content-Type', '未提供')}\n"
            f"內容前 500 字：{preview}"
        ) from exc


def fetch_api_data(
    api_url: str,
    timeout: tuple[float, float],
    logger: logging.Logger,
) -> Any:
    """呼叫臺中市政府停車資料 API。"""

    session = build_http_session()

    logger.info("開始呼叫臺中市政府停車資料 API。")
    logger.info("API URL：%s", api_url)

    try:
        response = session.get(
            api_url,
            timeout=timeout,
            allow_redirects=True,
        )
    except requests.Timeout as exc:
        raise RuntimeError(
            f"API 請求逾時，timeout={timeout}。"
        ) from exc
    except requests.ConnectionError as exc:
        raise RuntimeError(
            "無法連線至 API，請檢查網路、DNS 或防火牆。"
        ) from exc
    except requests.RequestException as exc:
        raise RuntimeError(
            f"API 請求失敗：{exc}"
        ) from exc

    logger.info("HTTP 狀態碼：%s", response.status_code)
    logger.info(
        "Content-Type：%s",
        response.headers.get("Content-Type", "未提供"),
    )
    logger.info(
        "回傳大小：%,d bytes",
        len(response.content),
    )
    logger.info("最終 URL：%s", response.url)

    if not response.ok:
        response_preview = response.text[:500].replace("\n", " ")

        raise RuntimeError(
            f"API 回傳 HTTP {response.status_code}。\n"
            f"回應內容前 500 字：{response_preview}"
        )

    return parse_response_content(response)


def find_record_list(value: Any) -> list[dict[str, Any]] | None:
    """
    從不同 JSON 結構中尋找 list[dict]。

    支援範例：
    [
        {...},
        {...}
    ]

    或：

    {
        "data": [
            {...},
            {...}
        ]
    }

    或：

    {
        "result": {
            "records": [
                {...}
            ]
        }
    }
    """

    if isinstance(value, list):
        if not value:
            return []

        if all(isinstance(item, dict) for item in value):
            return value

        return None

    if not isinstance(value, dict):
        return None

    priority_keys = (
        "data",
        "records",
        "result",
        "results",
        "items",
        "rows",
        "value",
    )

    for key in priority_keys:
        if key not in value:
            continue

        result = find_record_list(value[key])

        if result is not None:
            return result

    for nested_value in value.values():
        result = find_record_list(nested_value)

        if result is not None:
            return result

    return None


def extract_records(payload: Any) -> list[dict[str, Any]]:
    """從完整 JSON 中取出停車格資料列。"""

    records = find_record_list(payload)

    if records is None:
        raise ValueError(
            "無法從 API JSON 中找到資料陣列。"
            f"JSON 根節點型態為 {type(payload).__name__}。"
        )

    if not records:
        raise ValueError("API JSON 中的資料陣列為空。")

    return records


def collect_available_fields(
    records: list[dict[str, Any]],
) -> set[str]:
    """收集 API 回傳的所有欄位名稱。"""

    fields: set[str] = set()

    for record in records[:500]:
        fields.update(record.keys())

    return fields


def find_actual_field(
    available_fields: set[str],
    aliases: tuple[str, ...],
) -> str | None:
    """根據候選名稱找出實際欄位。"""

    lowercase_mapping = {
        field.lower(): field
        for field in available_fields
    }

    for alias in aliases:
        if alias in available_fields:
            return alias

        matched_field = lowercase_mapping.get(alias.lower())

        if matched_field is not None:
            return matched_field

    return None


def resolve_fields(
    records: list[dict[str, Any]],
) -> dict[str, str | None]:
    """辨識 API 實際使用的欄位名稱。"""

    available_fields = collect_available_fields(records)

    return {
        semantic_name: find_actual_field(
            available_fields,
            aliases,
        )
        for semantic_name, aliases in FIELD_ALIASES.items()
    }


def build_field_summary(
    records: list[dict[str, Any]],
) -> pd.DataFrame:
    """整理欄位名稱、型態、空值與範例。"""

    fields = collect_available_fields(records)
    summary_rows: list[dict[str, Any]] = []

    for field in sorted(fields):
        values = [
            record.get(field)
            for record in records
            if field in record
        ]

        non_null_values = [
            value
            for value in values
            if value is not None
        ]

        type_names = sorted(
            {
                type(value).__name__
                for value in non_null_values
            }
        )

        example_value = (
            non_null_values[0]
            if non_null_values
            else None
        )

        example_text = repr(example_value)

        if len(example_text) > 100:
            example_text = example_text[:97] + "..."

        summary_rows.append(
            {
                "欄位名稱": field,
                "出現筆數": len(values),
                "非空值筆數": len(non_null_values),
                "Python型態": ", ".join(type_names) or "None",
                "範例值": example_text,
            }
        )

    return pd.DataFrame(summary_rows)


def validate_records(
    records: list[dict[str, Any]],
    resolved_fields: dict[str, str | None],
    logger: logging.Logger,
) -> None:
    """檢查座標、status 與車格編號。"""

    dataframe = pd.DataFrame(records)

    missing_fields = [
        semantic_name
        for semantic_name, actual_name
        in resolved_fields.items()
        if actual_name is None
    ]

    if missing_fields:
        logger.warning(
            "找不到下列欄位：%s",
            ", ".join(missing_fields),
        )
    else:
        logger.info("主要欄位均已辨識。")

    latitude_field = resolved_fields["latitude"]
    longitude_field = resolved_fields["longitude"]

    if latitude_field and longitude_field:
        latitude = pd.to_numeric(
            dataframe[latitude_field],
            errors="coerce",
        )
        longitude = pd.to_numeric(
            dataframe[longitude_field],
            errors="coerce",
        )

        valid_coordinates = (
            latitude.between(-90, 90)
            & longitude.between(-180, 180)
        )

        logger.info(
            "有效座標：%,d / %,d",
            int(valid_coordinates.sum()),
            len(dataframe),
        )

        if not valid_coordinates.all():
            logger.warning(
                "共有 %,d 筆座標無法解析或超出合理範圍。",
                int((~valid_coordinates).sum()),
            )

    status_field = resolved_fields["status"]

    if status_field:
        numeric_status = pd.to_numeric(
            dataframe[status_field],
            errors="coerce",
        )

        valid_status = numeric_status.isin([0, 1, 2])

        logger.info(
            "status 為 0、1、2：%,d / %,d",
            int(valid_status.sum()),
            len(dataframe),
        )

        print("\nstatus 原始值分布：")
        print(
            dataframe[status_field]
            .astype("string")
            .value_counts(dropna=False)
            .sort_index()
            .to_string()
        )

    ps_id_field = resolved_fields["ps_id"]

    if ps_id_field:
        duplicate_count = int(
            dataframe[ps_id_field]
            .astype("string")
            .duplicated()
            .sum()
        )

        logger.info(
            "本次回應中重複的 PS_ID：%,d 筆",
            duplicate_count,
        )


def print_sample_records(
    records: list[dict[str, Any]],
    sample_size: int = 3,
) -> None:
    """顯示前幾筆資料。"""

    actual_size = min(sample_size, len(records))

    print(f"\n前 {actual_size} 筆資料：")

    for index, record in enumerate(
        records[:actual_size],
        start=1,
    ):
        print(f"\n--- 第 {index} 筆 ---")
        print(
            json.dumps(
                record,
                ensure_ascii=False,
                indent=2,
            )
        )


def save_results(
    payload: Any,
    records: list[dict[str, Any]],
    collected_at: datetime,
    logger: logging.Logger,
) -> tuple[Path, Path]:
    """
    保存第一次擷取結果。

    data/raw/ 不需要事先建立。
    API 成功並完成解析後才會建立。
    """

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    timestamp_text = collected_at.strftime(
        "%Y%m%dT%H%M%SZ"
    )

    json_path = (
        RAW_DATA_DIR
        / f"taichung_parking_{timestamp_text}.json"
    )

    csv_path = (
        RAW_DATA_DIR
        / f"taichung_parking_{timestamp_text}.csv"
    )

    with json_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

    dataframe = pd.DataFrame(records)

    dataframe.insert(
        loc=0,
        column="collected_at_utc",
        value=collected_at.isoformat(),
    )

    dataframe.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    logger.info("原始 JSON 已儲存：%s", json_path)
    logger.info("CSV 已儲存：%s", csv_path)

    return json_path, csv_path


def main() -> int:
    """程式進入點。"""

    load_dotenv(ENV_FILE)

    logger = configure_logging()

    api_url = os.getenv(
        "TAICHUNG_PARKING_API_URL",
        "",
    ).strip()

    if not api_url:
        logger.error(
            "找不到 TAICHUNG_PARKING_API_URL。"
            "請確認專案根目錄存在 .env。"
        )
        return 1

    collected_at = datetime.now(timezone.utc)

    try:
        timeout = get_timeout()

        payload = fetch_api_data(
            api_url=api_url,
            timeout=timeout,
            logger=logger,
        )

        logger.info(
            "JSON 根節點型態：%s",
            type(payload).__name__,
        )

        records = extract_records(payload)

        logger.info(
            "成功取得資料：%,d 筆",
            len(records),
        )

        resolved_fields = resolve_fields(records)

        print("\n辨識到的實際欄位：")

        for semantic_name, actual_name in resolved_fields.items():
            print(
                f"{semantic_name:<12} -> "
                f"{actual_name or '找不到'}"
            )

        field_summary = build_field_summary(records)

        print("\n欄位與資料型態：")
        print(
            field_summary.to_string(index=False)
        )

        print_sample_records(records)

        validate_records(
            records=records,
            resolved_fields=resolved_fields,
            logger=logger,
        )

        json_path, csv_path = save_results(
            payload=payload,
            records=records,
            collected_at=collected_at,
            logger=logger,
        )

        print("\nAPI 擷取測試完成。")
        print(f"資料筆數：{len(records):,}")
        print(f"JSON 檔案：{json_path}")
        print(f"CSV 檔案：{csv_path}")
        print(
            f"擷取時間 UTC：{collected_at.isoformat()}"
        )

        return 0

    except Exception:
        logger.exception("API 擷取測試失敗。")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())