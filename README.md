# parking_analysis

逢甲商圈周邊路邊停車壓力分析專題的資料蒐集程式。

目前專案處於第一階段，目標是呼叫臺中市政府資料開放平臺的「臺中市路邊剩餘車位」API，確認 JSON 結構、實際欄位名稱、資料筆數、座標格式及車格狀態，並保存每次擷取的原始資料。

## 一、目前階段

目前只完成下列工作：

1. 呼叫臺中市政府停車資料 API。
2. 檢查 HTTP 狀態碼。
3. 設定連線與讀取逾時。
4. 解析 JSON。
5. 辨識實際欄位名稱。
6. 檢查座標格式。
7. 驗證 `status` 是否為 `0`、`1` 或 `2`。
8. 加入資料擷取時間。
9. 保存原始 JSON 與 CSV。
10. 記錄程式執行日誌。

目前尚未加入：

* 逢甲大學周邊 1 公里篩選
* Haversine distance
* PostgreSQL
* TimescaleDB
* 每 10 分鐘排程
* Docker
* Azure VM
* Grafana
* Streamlit

上述功能會在 API 欄位確認後逐步加入。

## 二、資料來源

資料集名稱：

```text
臺中市路邊剩餘車位
```

資料集頁面：

```text
https://opendata.taichung.gov.tw/search/1fd63eca-063d-4e4e-9443-1d66bf3f2051
```

請從資料集頁面開啟 JSON 資源，並將實際 API 網址填入 `.env`。

預期主要欄位包括：

| 欄位               | 說明    |
| ---------------- | ----- |
| `Section_ID`     | 路段編號  |
| `PS_ID`          | 停車格編號 |
| `PS_type`        | 停車格類型 |
| `PS_Lat` 或 `Lat` | 緯度    |
| `PS_Lng` 或 `Lng` | 經度    |
| `status`         | 停車格狀態 |

`status` 定義：

| status | 說明       |
| -----: | -------- |
|      0 | 車格沒有車    |
|      1 | 車格有車     |
|      2 | 感測器異常或故障 |

實際欄位名稱必須以 API 執行當下的 JSON 回傳結果為準。

## 三、開發環境

本專案使用：

* Python 3.12
* uv
* requests
* python-dotenv
* pandas

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
```

若 `uv init` 自動建立了根目錄的 `main.py`，可將其移除：

```powershell
Remove-Item main.py
```

加入專案套件：

```powershell
uv add requests python-dotenv pandas
```

`uv` 會自動建立：

```text
.venv/
pyproject.toml
uv.lock
```

本專案不需要手動執行 `pip install`，也不需要自行建立 `requirements.txt`。

## 五、專案結構

程式第一次執行前：

```text
parking_analysis/
├── collector/
│   └── api_test.py
├── .env
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
└── README.md
```

`data/` 與 `logs/` 不需要手動建立。

程式執行後會自動建立：

```text
parking_analysis/
├── collector/
│   └── api_test.py
├── data/
│   └── raw/
│       ├── taichung_parking_YYYYMMDDTHHMMSSZ.json
│       └── taichung_parking_YYYYMMDDTHHMMSSZ.csv
├── logs/
│   └── api_test.log
├── .env
├── .env.example
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
└── README.md
```

其中：

* `logs/` 在程式啟動時建立。
* `data/raw/` 只有在 API 成功回傳並完成解析後才會建立。
* API 執行失敗時，不會產生假的 JSON 或 CSV。

## 六、環境變數設定

建立 `.env.example`：

```env
TAICHUNG_PARKING_API_URL=請填入臺中市政府資料集的JSON_API網址

REQUEST_CONNECT_TIMEOUT=10
REQUEST_READ_TIMEOUT=60
```

複製成 `.env`：

```powershell
Copy-Item .env.example .env
```

接著編輯 `.env`：

```env
TAICHUNG_PARKING_API_URL= https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=1744bc00-cd16-48f3-9632-309f364662bb

REQUEST_CONNECT_TIMEOUT=10
REQUEST_READ_TIMEOUT=60
```

環境變數說明：

| 變數                         | 說明                |
| -------------------------- | ----------------- |
| `TAICHUNG_PARKING_API_URL` | 臺中市政府 JSON API 網址 |
| `REQUEST_CONNECT_TIMEOUT`  | 建立連線的逾時秒數         |
| `REQUEST_READ_TIMEOUT`     | 等待 API 回應內容的逾時秒數  |

`.env` 不應提交到 Git。

## 七、安裝相依套件

若專案是從 Git clone 下來，執行：

```powershell
uv sync
```

`uv sync` 會依照 `pyproject.toml` 與 `uv.lock` 建立環境並安裝相同版本的套件。

## 八、執行 API 擷取程式

確認目前位於專案根目錄：

```text
parking_analysis/
```

執行：

```powershell
uv run python collector\api_test.py
```

不需要手動啟用 `.venv`。

查看程式結束碼：

```powershell
echo $LASTEXITCODE
```

成功時應為：

```text
0
```

失敗時應為非 `0`。

## 九、程式執行流程

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
顯示資料範例
    ↓
保存原始 JSON
    ↓
加入 collected_at_utc 並保存 CSV
```

## 十、預期終端機輸出

成功時應看到類似內容：

```text
開始呼叫臺中市政府停車資料 API
HTTP 狀態碼：200
Content-Type：application/json
JSON 根節點型態：list
成功取得資料：N 筆
```

接著會列出實際欄位：

```text
辨識到的實際欄位：

section_id   -> Section_ID
ps_id        -> PS_ID
ps_type      -> PS_type
latitude     -> PS_Lat
longitude    -> PS_Lng
status       -> status
```

實際座標欄位也可能是：

```text
latitude     -> Lat
longitude    -> Lng
```

程式還會顯示：

```text
欄位名稱
出現筆數
非空值筆數
Python 型態
範例值
```

以及：

```text
有效座標：N / N
status 為 0、1、2：N / N
本次回應中重複的 PS_ID：N 筆
```

## 十一、輸出資料

### 原始 JSON

路徑：

```text
data/raw/taichung_parking_YYYYMMDDTHHMMSSZ.json
```

此檔案保存 API 的原始 JSON 結構，不修改欄位名稱或資料內容。

### CSV

路徑：

```text
data/raw/taichung_parking_YYYYMMDDTHHMMSSZ.csv
```

CSV 會在第一欄加入：

```text
collected_at_utc
```

此時間使用 UTC，範例如下：

```text
2026-06-16T10:30:00+00:00
```

後續顯示給使用者時，再轉換成臺灣時區 `Asia/Taipei`。

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
* 錯誤與例外訊息

## 十二、目前驗收標準

第一階段完成前，需確認：

* [ ] `uv sync` 執行成功
* [ ] `.env` 已設定 API 網址
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
* [ ] CSV 成功保存
* [ ] Log 成功產生
* [ ] 程式成功時結束碼為 0

資料筆數可能隨政府資料更新而改變，不應將某個固定筆數當成唯一成功標準。

## 十三、常見錯誤

### 1. 找不到 uv

錯誤：

```text
uv is not recognized
```

先確認：

```powershell
uv --version
```

若尚未安裝 uv，需先完成 uv 安裝，再重新開啟 PowerShell。

### 2. 找不到 `.env`

錯誤：

```text
找不到 TAICHUNG_PARKING_API_URL
```

確認專案根目錄存在：

```text
.env
```

並確認內容包括：

```env
TAICHUNG_PARKING_API_URL=https://實際API網址
```

### 3. HTTP 400 或 404

可能原因：

* API 資源網址已變更
* 資源識別碼失效
* 複製到資料集頁面網址，而不是 JSON API 網址

處理方式：

1. 開啟官方資料集頁面。
2. 找到 JSON 資源。
3. 複製新的 API 網址。
4. 更新 `.env`。
5. 重新執行程式。

```powershell
uv run python collector\api_test.py
```

### 4. API 連線逾時

錯誤可能包括：

```text
ConnectTimeout
ReadTimeout
```

先確認本機網路正常，再重新執行。

若政府 API 回應較慢，可調高：

```env
REQUEST_READ_TIMEOUT=120
```

不建議移除 timeout，否則程式可能長時間卡住。

### 5. 回傳內容不是 JSON

錯誤：

```text
API 回傳內容不是有效 JSON
```

可能原因：

* API 回傳維護頁面
* API 回傳 HTML 錯誤頁
* API 資源網址失效
* 政府資料平臺暫時異常

程式會顯示回傳內容前 500 字，供排查使用。

### 6. 找不到座標欄位

可能顯示：

```text
latitude -> 找不到
longitude -> 找不到
```

先查看程式列出的完整欄位名稱，確認 API 是否更改欄位。

座標可能使用：

```text
PS_Lat
PS_Lng
```

或：

```text
Lat
Lng
```

在確認實際欄位前，不應直接建立正式資料庫 Schema。

## 十四、Git 注意事項

`.gitignore` 建議內容：

```gitignore
.venv/
.env

__pycache__/
*.py[cod]

data/
logs/

.vscode/
.idea/
.DS_Store
Thumbs.db
```

應提交：

```text
pyproject.toml
uv.lock
.env.example
collector/api_test.py
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

## 十五、下一階段

API 擷取測試成功後，下一階段會將目前的單一測試程式拆分為：

```text
collector/
├── main.py
├── api_client.py
├── cleaner.py
├── geo.py
└── logger.py
```

後續流程：

```text
API 資料
    ↓
欄位標準化
    ↓
座標轉換
    ↓
status 驗證
    ↓
加入 collected_at
    ↓
計算與逢甲大學主要入口的距離
    ↓
保留 1 公里內停車格
    ↓
寫入 PostgreSQL 與 TimescaleDB
```

確認本機流程成功後，才會依序加入：

1. Collector Docker Container
2. TimescaleDB Container
3. Docker Compose
4. 每 10 分鐘自動蒐集
5. Azure VM 部署
6. Grafana 儀表板
7. Streamlit 成果展示頁面
