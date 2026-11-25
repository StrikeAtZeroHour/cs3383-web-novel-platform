# 技術棧與系統環境版本

> 記錄本專案（Web Novel Platform）使用的技術棧與實際測試過的版本。
> 檢查日期：2026-11-25
> 環境狀態：✅ 已安裝並通過煙霧測試

## 作業系統

| 項目 | 版本 |
|---|---|
| OS | Windows 11（Build 10.0.26200） |
| Shell | PowerShell |

## 核心技術棧

| 分類 | 技術 | 版本 | 用途 |
|---|---|---|---|
| 語言 | Python | **3.14.2** | 後端開發語言 |
| 後端框架 | Django | **5.2.19** | Web 框架（ORM / Auth / Admin / i18n / TestCase） |
| 資料庫 | SQLite | **3.50.4**（Python 內建） | 開發與展示用資料庫 |
| 圖片處理 | Pillow | **13.0.0** | `ImageField` 封面圖上傳 |
| 前端樣式 | Bootstrap | 5.x（CDN） | 響應式 UI，無 build step |
| 模板引擎 | Django Templates | 內建 | 伺服器端渲染 |
| 國際化 | Django i18n + GNU gettext | Django 內建 + gettext **1.0** | 中英雙語切換；`.po` ↔ `.mo` 編譯 |
| 測試框架 | Django `TestCase`（unittest） | 內建 | 自動化測試 > 50 個 |

## Python 套件（`.venv` 虛擬環境實際安裝）

```
asgiref==3.13.0
Django==5.2.19
pillow==13.0.0
pip==26.3
sqlparse==0.6.1
tzdata==2026.6
```

## 開發輔助工具（已存在於本機）

| 工具 | 版本 | 備註 |
|---|---|---|
| pip | 26.3（虛擬環境內） | 系統環境需用 `python -m pip` |
| Git | 2.52.0.windows.1 | 版本控制 |
| GNU gettext | **1.0**（mlocati static build，含 iconv 1.19） | `manage.py makemessages` / `compilemessages` |
| Node.js | v24.12.0 | **本專案不需要**，僅記錄 |
| VS Code | 已安裝 | 建議編輯器 |
| AI Agent | opencode + DeepSeek API | 開發輔助 |

## 國際化工具（gettext）

Django 的 `makemessages` / `compilemessages` 需要 **GNU gettext** 的
`xgettext`、`msgmerge`、`msgfmt` 執行檔，Windows 沒有內建，因此本專案自行安裝。

- 來源：<https://github.com/mlocati/gettext-iconv-windows/releases/tag/v1.0-v1.19>
  （`gettext1.0-iconv1.19-static-64.zip`，靜態連結、免安裝）
- SHA256：`2b999bc37b56fa052ff98578e9cb188152009f634e3a66aa8ff263a016e9c466`
  （已與官方 release 公布值比對一致）
- 安裝位置：`.venv\Scripts\gettext\`（執行檔在 `.venv\Scripts\gettext\bin\`）
- 已加入使用者 PATH；若在新終端機仍找不到指令，單次執行時加上：

```powershell
$env:Path += ";$PWD\.venv\Scripts\gettext\bin"
& msgfmt --version
```

注意：mlocati 封裝的執行檔直接放在 `gettext\bin\`（不是 `gettext\bin\bin\`）。

### i18n 工作流程

```powershell
cd src
$env:Path += ";..\.venv\Scripts\gettext\bin"

# 1. 掃描程式碼與模板中的 gettext/{% trans %} 字串，合併進既有翻譯檔
..\.venv\Scripts\python.exe manage.py makemessages -l zh_Hant `
    --ignore=".venv/*" --ignore="locale/*"

# 2. 編輯 ../locale/zh_Hant/LC_MESSAGES/django.po（填入 msgstr）

# 3. 編譯成 .mo（網站實際讀取的檔案）
..\.venv\Scripts\python.exe manage.py compilemessages

# 4. 檢查翻譯完整性（應顯示 "N translated messages"，無 untranslated）
..\.venv\Scripts\gettext\bin\msgfmt.exe --check --statistics `
    -o "$env:TEMP\check.mo" ..\locale\zh_Hant\LC_MESSAGES\django.po
```

- **locale 目錄必須命名為 `zh_Hant`**：Django 把語言代碼 `zh-hant` 以
  `to_locale()` 轉成 `zh_Hant` 再去尋找目錄；命名成 `zh-hant` 會被忽略。
- `makemessages` 會保留已填入的 `msgstr`，但會重排條目與更新行號。
- `.mo` 不納入版控（`.gitignore` 含 `*.mo`），換機器後需執行一次
  `compilemessages`。
- 已知限制：`makemessages` 在 Windows 上會把檔頭備註改成預設值，若不影響使用可忽略。

## 虛擬環境

- 位置：`project 2026/.venv`
- 啟用方式（PowerShell）：

```powershell
.\.venv\Scripts\Activate.ps1
```

- 不在虛擬環境內時，直接指定執行檔（**需先進入 `src/`**，所有程式碼都在那裡）：

```powershell
cd src
..\.venv\Scripts\python.exe manage.py runserver
```

> 專案採 `src/` 佈局：程式碼（`config/`、`accounts/`、`novels/`、`interaction/`、`templates/`、`static/`）與 `manage.py`、`db.sqlite3` 都放在 `src/` 底下；文件與 `.venv` 留在專案根目錄。

## 煙霧測試結果（2026-11-25）

| 測試項目 | 結果 |
|---|---|
| `django-admin startproject` 建立專案 | ✅ |
| `manage.py migrate`（所有內建 migration） | ✅ OK |
| `manage.py check` | ✅ no issues |
| 建立用戶 + 密碼雜湊驗證 | ✅ `pbkdf2_sha256`，驗證 True |
| SQLite 實際寫入／查詢 | ✅ |
| i18n 切換（zh-hant / en） | ✅ 分類顯示「奇幻」／`Fantasy`，全站介面翻譯 165 條 |
| 模板渲染 | ✅ |
| `runserver` + HTTP 請求（Admin 登入頁） | ✅ HTTP 200 |
| Pillow `ImageField` 相依 | ✅ 13.0.0 可用 |

## 備註

1. Python 3.14.2 為目前穩定版本，**Django 5.2 自 5.2.8 起官方支援 Python 3.14**（官方支援矩陣：3.10–3.14），本專案使用 5.2.19，屬正式支援組合，無相容性風險。
   - 參考：<https://docs.djangoproject.com/en/5.2/faq/install/>
2. SQLite 直接內建於 Python，無需額外安裝或設定伺服器。
3. Django 內建功能可直接對應報告所需：ORM → ER / class diagram、TestCase → 50+ 測試案例、Admin → 管理後台、i18n → 雙語 UI。
4. Bootstrap 5 透過 CDN 載入，不需 npm 或任何前端建置流程。
