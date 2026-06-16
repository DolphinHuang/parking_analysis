# parking_analysis

逢甲商圈周邊路邊停車壓力分析專題的資料蒐集程式。

目前專案已完成臺中市路邊剩餘車位 API 擷取、原始資料保存，以及寫入 PostgreSQL / TimescaleDB 的本機 collector 流程。後續目標是加入逢甲大學周邊 1 公里篩選、定時蒐集與 Azure VM 部署。

## 一、目前階段

目前已完成下列工作：

1. 呼叫臺中市政府停車資料 API。
2. 檢查 HTTP 狀態碼。
3. 設定連線與讀取逾時。
4. 解析 JSON。
5. 辨識實際欄位名稱。
6. 檢查座標格式。
7. 驗證 `status` 是否為 `0`、`1` 或 `2`。
8. 加入資料擷取時間。
9. 保存原始 JSON。
10. 記錄程式執行日誌。
11. 建立 TimescaleDB schema。
12. 將資料寫入 `parking_status_raw`。
13. 提供 `Dockerfile` 與 `docker-compose.yml`。

目前尚未加入：

* 逢甲大學周邊 1 公里篩選
* Haversine distance
* 每 10 分鐘排程
* Azure VM
* Grafana
* Streamlit

上述功能會在本機資料庫流程確認後逐步加入。

## 二、資料來源

資料集名稱：

```text
臺中市路邊剩餘車位
```

資料集頁面：

```text
https://opendata.taichung.gov.tw/search/1fd63eca-063d-4e4e-9443-1d66bf3f2051
```

目前使用的 JSON API：

```text
https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=1744bc00-cd16-48f3-9632-309f364662bb
```

請將實際 API 網址填入 `.env` 的 `TAICHUNG_PARKING_API_URL`。

預期主要欄位包括：

| 欄位 | 說明 |
| --- | --- |
| `Section_ID` | 路段編號 |
| `PS_ID` | 停車格編號 |
| `PS_type` | 停車格類型 |
| `PS_Lat` 或 `Lat` | 緯度 |
| `PS_Lng` 或 `Lng` | 經度 |
| `status` | 停車格狀態 |

`status` 定義：

| status | 說明 |
| ---: | --- |
| 0 | 車格沒有車 |
| 1 | 車格有車 |
| 2 | 感測器異常或故障 |

實際欄位名稱必須以 API 執行當下的 JSON 回傳結果為準。

## 三、開發環境

本專案使用：

* Python 3.12
* uv
* requests
* python-dotenv
* pandas
* psycopg
* PostgreSQL / TimescaleDB

確認 uv 已安裝：

```powershell
uv --version
```

## 四、建立專案

第一次建立專案時，在 PowerShell 執行：

```powershell
uv init --app parking_analysis
cd parking_analysis
```

固定 Python 版本：

```powershell
uv python pin 3.12
```

建立資料蒐集程式目錄：

```powershell
mkdir collector
mkdir sql
```

若 `uv init` 自動建立了根目錄的 `main.py`，可將其移除：

```powershell
Remove-Item main.py
```

加入專案套件：

```powershell
uv add requests python-dotenv pandas "psycopg[binary]"
```

`uv` 會自動建立：

```text
.venv/
pyproject.toml
uv.lock
```

本專案不需要手動執行 `pip install`，也不需要自行建立 `requirements.txt`。

## 五、專案結構

目前專案結構：

```text
parking_analysis/
├── collector/
│   ├── __init__.py
│   ├── api_test.py
│   ├── db.py
│   ├── main.py
│   └── transform.py
├── sql/
│   └── schema.sql
├── data/
│   └── raw/
│       └── taichung_parking_YYYYMMDDTHHMMSSZ.json
├── logs/
│   └── api_test.log
├── .env
├── .env.example
├── .gitignore
├── .python-version
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

其中：

* `collector/api_test.py` 用於 API 驗證與欄位檢查。
* `collector/main.py` 是正式 collector 入口。
* `sql/schema.sql` 定義 TimescaleDB schema。
* `data/raw/` 保存每次抓下來的原始 JSON。
* `logs/` 保存執行日誌。

## 六、環境變數設定

建立 `.env.example`：

```env
TAICHUNG_PARKING_API_URL=https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=1744bc00-cd16-48f3-9632-309f364662bb

REQUEST_CONNECT_TIMEOUT=10
REQUEST_READ_TIMEOUT=60

DB_HOST=localhost
DB_PORT=5432
DB_NAME=parking_analysis
DB_USER=parking_user
DB_PASSWORD=parking_password
DB_SSLMODE=disable
```

複製成 `.env`：

```powershell
Copy-Item .env.example .env
```

環境變數說明：

| 變數 | 說明 |
| --- | --- |
| `TAICHUNG_PARKING_API_URL` | 臺中市政府 JSON API 網址 |
| `REQUEST_CONNECT_TIMEOUT` | 建立連線的逾時秒數 |
| `REQUEST_READ_TIMEOUT` | 等待 API 回應內容的逾時秒數 |
| `DB_HOST` | PostgreSQL / TimescaleDB 主機 |
| `DB_PORT` | PostgreSQL / TimescaleDB 連線埠 |
| `DB_NAME` | 資料庫名稱 |
| `DB_USER` | 資料庫使用者 |
| `DB_PASSWORD` | 資料庫密碼 |
| `DB_SSLMODE` | PostgreSQL SSL 模式 |

`.env` 不應提交到 Git。

本機執行 `uv run python -m collector.main` 時使用 `.env`。

Docker 執行 `collector` 時使用 `.env.docker`，其中 `DB_HOST` 必須是 `timescaledb`，不能是 `localhost`。

## 七、安裝相依套件

若專案是從 Git clone 下來，執行：

```powershell
uv sync
```

`uv sync` 會依照 `pyproject.toml` 與 `uv.lock` 建立環境並安裝相同版本的套件。

## 八、執行 API 驗證腳本

確認目前位於專案根目錄：

```text
parking_analysis/
```

執行：

```powershell
uv run python collector\api_test.py
```

此腳本用途：

1. 驗證 API 是否可用。
2. 檢查 JSON 結構與欄位名稱。
3. 輸出 raw JSON。
4. 確認座標與 `status` 格式。

## 九、執行正式 Collector

先啟動 TimescaleDB：

```powershell
docker compose up -d timescaledb
```

再執行 collector：

```powershell
uv run python -m collector.main
```

此模式會讀取專案根目錄的 `.env`。

或直接透過容器執行：

```powershell
docker compose up --build collector
```

此模式會讀取 `docker-compose.yml` 中指定的 `.env.docker`。

正式 collector 會完成以下工作：

1. 呼叫 API。
2. 驗證欄位與座標。
3. 保存 raw JSON。
4. 建立 `parking_status_raw` schema。
5. 將本次資料寫入 TimescaleDB。

## 十、程式執行流程

```text
讀取 .env
    ↓
建立 logging
    ↓
呼叫臺中市政府 API
    ↓
檢查 HTTP 狀態碼
    ↓
解析 JSON 或 ZIP 中的 JSON
    ↓
尋找停車格資料陣列
    ↓
辨識實際欄位名稱
    ↓
檢查座標與 status
    ↓
保存原始 JSON
    ↓
欄位標準化
    ↓
建立 schema 並寫入 TimescaleDB
```

## 十一、預期終端機輸出

成功時應看到類似內容：

```text
開始呼叫臺中市政府停車資料 API
HTTP 狀態碼：200
JSON 根節點型態：list
成功取得資料：N 筆
成功寫入資料庫：N 筆
```

實際欄位可能顯示：

```text
section_id   -> Section_ID
ps_id        -> PS_ID
ps_type      -> PS_type
latitude     -> Lat
longitude    -> Lng
status       -> status
```

## 十二、輸出資料

### 原始 JSON

路徑：

```text
data/raw/taichung_parking_YYYYMMDDTHHMMSSZ.json
```

此檔案保存 API 的原始 JSON 結構，不修改欄位名稱或資料內容。

### Log

路徑：

```text
logs/api_test.log
```

Log 會記錄：

* API 網址
* HTTP 狀態碼
* 回傳資料大小
* JSON 根節點型態
* 資料筆數
* 座標驗證結果
* status 驗證結果
* 輸出檔案位置
* 資料庫寫入筆數
* 錯誤與例外訊息

### TimescaleDB Table

正式 collector 會建立並寫入：

```text
parking_status_raw
```

主要欄位：

* `collected_at_utc`
* `section_id`
* `ps_id`
* `ps_type`
* `lat`
* `lng`
* `status`
* `county_code`
* `agency_codes`

## 十三、目前驗收標準

本階段完成前，需確認：

* [ ] `uv sync` 執行成功
* [ ] `.env` 已設定 API 網址與 DB 連線資訊
* [ ] API 回傳 HTTP 200
* [ ] JSON 可以正常解析
* [ ] 資料筆數大於 0
* [ ] 可以辨識 `Section_ID`
* [ ] 可以辨識 `PS_ID`
* [ ] 可以辨識 `PS_type`
* [ ] 可以辨識緯度欄位
* [ ] 可以辨識經度欄位
* [ ] 可以辨識 `status`
* [ ] 座標可以轉成數值
* [ ] `status` 可驗證為 0、1、2
* [ ] JSON 成功保存
* [ ] Log 成功產生
* [ ] `parking_status_raw` 成功建立
* [ ] 資料成功寫入 TimescaleDB
* [ ] 程式成功時結束碼為 0

下列功能仍未完成，不應誤判為已驗收：

* [ ] 逢甲大學周邊 1 公里篩選
* [ ] Haversine distance
* [ ] 每 10 分鐘自動蒐集
* [ ] Azure VM 長期部署

## 十四、常見錯誤

### 1. 找不到 uv

錯誤：

```text
uv is not recognized
```

先確認：

```powershell
uv --version
```

### 2. 找不到 `.env`

錯誤：

```text
找不到 TAICHUNG_PARKING_API_URL
```

確認專案根目錄存在：

```text
.env
```

並確認內容至少包括：

```env
TAICHUNG_PARKING_API_URL=https://實際API網址
DB_HOST=localhost
DB_NAME=parking_analysis
DB_USER=parking_user
DB_PASSWORD=你的密碼
```

### 3. HTTP 400 或 404

可能原因：

* API 資源網址已變更
* 資源識別碼失效
* 複製到資料集頁面網址，而不是 JSON API 網址

### 4. 無法連線資料庫

可能原因：

* TimescaleDB 尚未啟動
* `.env` 的 `DB_HOST`、`DB_PORT`、`DB_NAME`、`DB_USER`、`DB_PASSWORD` 錯誤

先確認容器是否啟動：

```powershell
docker compose ps
```

若只想先啟動資料庫：

```powershell
docker compose up -d timescaledb
```

### 5. API 連線逾時

若政府 API 回應較慢，可調高：

```env
REQUEST_READ_TIMEOUT=120
```

### 6. 回傳內容不是 JSON

可能原因：

* API 回傳維護頁面
* API 回傳 HTML 錯誤頁
* API 資源網址失效

### 7. 找不到座標欄位

若欄位真的變動，需同步更新：

* `collector/transform.py`
* `sql/schema.sql`

## 十五、Git 注意事項

應提交：

```text
pyproject.toml
uv.lock
.env.example
collector/api_test.py
collector/main.py
collector/db.py
collector/transform.py
sql/schema.sql
Dockerfile
docker-compose.yml
README.md
```

不應提交：

```text
.env
.venv/
data/
logs/
```

`uv.lock` 應保留在 Git 中，確保本機、Docker 與 Azure VM 使用相同的套件版本。

## 十六、下一階段

目前已拆分為：

```text
collector/
├── api_test.py
├── db.py
├── main.py
└── transform.py
```

下一步會依序加入：

1. 與逢甲大學主要入口的距離計算
2. 保留 1 公里內停車格
3. 每 10 分鐘自動蒐集
4. Azure VM 部署
5. Grafana 儀表板
6. Streamlit 成果展示頁面
