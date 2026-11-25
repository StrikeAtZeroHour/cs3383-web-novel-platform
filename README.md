# Web Novel Platform — 專案說明

讀者／創作者雙端的網路小說平台（CS3383 課程專案），以 Django + SQLite 實作。

> **擴充功能（v2）**：閱讀進度續讀、瀏覽數統計、排行榜、最近更新、章節目錄、
> 標籤/狀態/字數篩選、卷階層、章節草稿與定時發布、字數統計、作者儀表板、
> 寫作大綱、留言按讚/劇透/多層回覆、追蹤作者、通知、Email 驗證、密碼重設、
> 違規檢舉、只讀 JSON API、CI、env 化設定。測試 187 個、覆蓋率 100%。

## 目錄結構

```
project 2026/
├── src/                    ← 所有程式碼都在這裡
│   ├── config/             專案設定（settings.py、urls.py）
│   ├── accounts/           使用者、個人資料、權限策略
│   ├── novels/             作品、章節、NovelService
│   ├── interaction/        收藏、留言、評分
│   ├── templates/          HTML 模板（Bootstrap 5）
│   ├── static/             CSS
│   ├── manage.py           Django 管理指令入口
│   └── db.sqlite3          資料庫（不進版控）
├── docs/diagrams/          UML / ER / Sequence 圖（Mermaid 原始碼 + PNG）
├── locale/zh_Hant/         i18n 翻譯檔（django.po / django.mo）
├── .venv/                  Python 虛擬環境
├── agent.md                需求清單與設計決策
├── ENVIRONMENT.md          環境版本紀錄
├── STARTUP.md              啟動指南（詳細）
└── README.md               本文件
```

## 快速開始

> 完整說明（含常見問題、試玩路線）見 **[`STARTUP.md`](STARTUP.md)**。

所有 `manage.py` 指令都必須在 `src/` 內執行。

```powershell
# 1. 建立並啟動虛擬環境（從專案根目錄；若已有 .venv 可跳過建立）
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安裝相依套件（執行 http 用 runtime；含 coverage/pytest 的開發工具用 requirements-dev）
pip install -r src\requirements.txt

# 3. 進入程式碼目錄
cd src

# 4. 建立資料表
python manage.py migrate

# 5. 載入示範資料
python manage.py seed_demo

# 6. 編譯中文翻譯（.mo 不進版控，新環境必做）
$env:Path += ";..\.venv\Scripts\gettext\bin"
python manage.py compilemessages

# 7. 啟動開發伺服器
python manage.py runserver
```

- 前台：<http://127.0.0.1:8000/>
- 後台：<http://127.0.0.1:8000/admin/>

### 示範帳號

| 帳號 | 密碼 | 角色 |
|---|---|---|
| `admin` | `admin12345` | 超級管理員（可下架內容） |
| `alice` | `demo12345` | 一般使用者 |
| `bob` | `demo12345` | 一般使用者 |

### 常用指令

```powershell
cd src
python manage.py check                     # 檢查設定
python manage.py makemigrations            # 產生 migration
python manage.py test                      # 執行測試（Django 內建 runner，92 測試）
python manage.py createsuperuser           # 建立管理員
```

### 測試與覆蓋率（VS Code）

共 92 個 test case（`accounts` / `interaction` / `novels`）。兩種執行方式：

```powershell
cd src
python manage.py test                      # 方式一：Django runner
python -m pytest                           # 方式二：pytest-django（VS Code Testing 面板用）
```

- 覆蓋率：`python -m coverage run --rcfile=.coveragerc manage.py test` 後 `python -m coverage report`
- VS Code：安裝推薦擴充 `littlefoxteam.vscode-python-test-adapter`，左側 **Testing** 面板即列出全部測試。
- 開發工具需安裝 `pip install -r src\requirements-dev.txt`。
- 測試行為對照表見 [`src/TEST_COVERAGE.md`](src/TEST_COVERAGE.md)。

### 翻譯（i18n）

介面文字（含分類名稱）全部由 gettext 翻譯，程式碼與資料庫都不寫中文：

```powershell
cd src
$env:Path += ";..\.venv\Scripts\gettext\bin"     # gettext 工具（msgfmt / xgettext）
..\.venv\Scripts\python.exe manage.py makemessages -l zh_Hant --ignore=".venv/*" --ignore="locale/*"
# 編輯 ../locale/zh_Hant/LC_MESSAGES/django.po，填入 msgstr
..\.venv\Scripts\python.exe manage.py compilemessages   # 產生 django.mo
```

- 翻譯檔：`locale/zh_Hant/LC_MESSAGES/django.po`（**目錄必須是 `zh_Hant`**）。
- 分類名稱：資料庫只存英文（`Fantasy`），畫面用 `{{ category.label }}` 依介面語言
  顯示「奇幻」或 `Fantasy`。
- 作品內容（書名、章節、簡介、留言）是使用者資料，**不翻譯**。
- 語言切換：導覽列的選單寫入 `django_language` cookie；網站路徑不帶語言前綴。

## 技術棧

| 項目 | 版本 |
|---|---|
| Python | 3.14.2 |
| Django | 5.2.19 |
| SQLite | 內建於 Python |
| Pillow | 13.0.0 |
| gettext | GNU gettext 1.0（mlocati static build） |
| 前端 | Bootstrap 5（CDN） |
| i18n | Django i18n + gettext（en / zh-hant） |

詳細版本與相容性說明見 [`ENVIRONMENT.md`](ENVIRONMENT.md)。

## UI 設計系統

前端使用 **Bootstrap 5.3.3（CDN）+ 一份自訂樣式 `src/static/css/site.css`**，無 build step、無新依賴。

| 面向 | 做法 |
|---|---|
| 設計 token | `site.css` 的 CSS 變數：間距（`--space-*`）、字級（`--text-*`）、顏色角色（`--ink/--muted/--accent/--surface/--line`）、圓角、focus ring |
| 深色模式 | `<html data-theme="dark">`；偏好存 `localStorage['inkwell-theme']`，`<head>` 內 inline script 於繪製前套用**避免閃爍**；導覽列 ◐ 切換 |
| 閱讀器 | 工具列可調字級/行距/字體/主題（存 `localStorage['inkwell-reader']`）；頂部閱讀進度條；行高 1.75、欄寬 38rem（約 60–75 字） |
| 無障礙 | 正文對比 ≥ 4.5:1（深色 `--muted:#b6bcc4`）；留言讚/刪除等觸控目標 ≥ 44×44px；可見 `:focus-visible` outline（不移除） |
| 元件 | 卡片、狀態徽章（`status-ongoing/completed` token）、chips、排行榜獎牌、`surface-card` 表單、空狀態 |

深色模式的顏色與對比可在瀏覽器 DevTools 量測；閱讀偏好只存在瀏覽器端，不需要後端。

## 設計文件

| 文件 | 內容 |
|---|---|
| [`STARTUP.md`](STARTUP.md) | **如何啟動**、示範帳號、常見問題 |
| [`agent.md`](agent.md) | 39 項需求、專案範圍、設計決策 |
| [`docs/diagrams/01-use-case.md`](docs/diagrams/01-use-case.md) | Use Case 圖（26 個用例） |
| [`docs/diagrams/02-class-diagram.md`](docs/diagrams/02-class-diagram.md) | UML 類別圖 |
| [`docs/diagrams/03-er-diagram.md`](docs/diagrams/03-er-diagram.md) | ER 圖（含 v2 擴充表） |
| [`docs/diagrams/04-sequence.md`](docs/diagrams/04-sequence.md) | Sequence 圖（SD-1～SD-10） |

## 重要注意事項

- **`opencode.json` 含明文 API key**，已列入 `.gitignore`；上傳 GitHub 前請確認它沒有被追蹤。
- `db.sqlite3`、`media/`、`*.mo` 都不進版控。
- 文件（`*.md`、`docs/`）在專案根目錄，程式碼在 `src/`。
