# 啟動指南（How to Run）

本文件說明如何從零開始把 **Web Novel Platform** 跑起來。

---

## 0. 前置需求

| 項目 | 版本 | 備註 |
|---|---|---|
| Python | 3.14.2 | 已在專案內建 `.venv`，通常不需另裝 |
| 作業系統 | Windows 11 | 指令以 PowerShell 為主 |

確認虛擬環境存在：

```powershell
cd "C:\Users\taklo\Downloads\2026 semA\cs3383\project 2026"
Test-Path .\.venv\Scripts\python.exe
```

應該輸出 `True`。若為 `False`，見文末「常見問題 Q1」。

---

## 1. 啟動步驟（三行搞定）

> ⚠️ **所有 `manage.py` 指令都必須在 `src/` 目錄下執行。**
> 程式碼已全部收進 `src/`，在專案根目錄執行會出現 `can't open file 'manage.py'`。

```powershell
cd "{your path}\project 2026\src"
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py runserver
```

看到這行就代表成功：

```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

打開瀏覽器：

| 頁面 | 網址 |
|---|---|
| 前台首頁 | <http://127.0.0.1:8000/> |
| 後台管理 | <http://127.0.0.1:8000/admin/> |

按 `Ctrl + C` 可停止伺服器。

---

## 2. 第一次執行：載入示範資料與翻譯

資料庫 `src/db.sqlite3` 已存在，但若是**全新環境**或想重置資料，執行：

```powershell
cd "C:\Users\taklo\Downloads\2026 semA\cs3383\project 2026\src"
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py seed_demo
```

`seed_demo` 是**可重複執行**的：已存在的資料不會重複建立。

接著編譯中文翻譯（`.mo` 不進版控，**新環境一定要做**，否則介面只有英文）：

```powershell
$env:Path += ";..\.venv\Scripts\gettext\bin"
..\.venv\Scripts\python.exe manage.py compilemessages
```

> gettext 工具位於 `.venv\Scripts\gettext\bin`，已加入使用者 PATH；若新開的終端機
> 仍找不到 `msgfmt`，就照上面先加一次 `$env:Path`。

### 示範帳號

| 帳號 | 密碼 | 角色 | 能做的事 |
|---|---|---|---|
| `admin` | `admin12345` | 超級管理員 | 進後台、下架違規內容 |
| `alice` | `demo12345` | 一般使用者 | 建立／編輯作品、留言、收藏、評分 |
| `bob` | `demo12345` | 一般使用者 | 同上 |

> 三組帳號完全依「人人皆可創作」設計：`alice` 與 `bob` 權限相同，都既是讀者也是作者。

---

## 3. 另一種寫法：先啟用虛擬環境

```powershell
cd "C:\Users\taklo\Downloads\2026 semA\cs3383\project 2026"
.\.venv\Scripts\Activate.ps1
cd src
python manage.py runserver
```

啟用後提示字元前面會出現 `(.venv)`，之後就不用每次都打完整路徑。

若 PowerShell 拒絕執行腳本（`running scripts is disabled`），改用：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

這只對當前視窗生效，不會改動系統設定。

---

## 4. 常用指令速查

以下指令都假設你已在 `src/` 目錄內。

| 目的 | 指令 |
|---|---|
| 啟動開發伺服器 | `python manage.py runserver` |
| 換 port（8000 被佔用） | `python manage.py runserver 8080` |
| 檢查設定有無錯誤 | `python manage.py check` |
| 建立／套用資料表 | `python manage.py makemigrations` → `python manage.py migrate` |
| 載入示範資料 | `python manage.py seed_demo` |
| 更新翻譯字串清單 | `python manage.py makemessages -l zh_Hant --ignore=".venv/*" --ignore="locale/*"` |
| 編譯翻譯（改過 `.po` 後必做） | `python manage.py compilemessages` |
| 執行測試 | `python manage.py test` |
| 建立管理員帳號 | `python manage.py createsuperuser` |
| 進入 Django shell | `python manage.py shell` |

---

## 5. 建議的試玩路線

確認伺服器跑起來後，可以照這個順序驗證主要功能：

1. **訪客**開首頁 → 不用登入就能看作品、讀章節（C4）。
2. 點 **Sign up** 註冊新帳號（A1）。
3. 開任一作品的 **Add to favorites**，再開 **My favorites** 確認（D1、D2）。
4. 在章節頁 **Post comment**，再對該留言 **Reply**（D3、D6）。
5. 進 **My novels → New novel** 建書 → **Publish** → **Add chapter**（E2、E5、E7）。
6. 用 `admin` 登入 `/admin/`，在 **Novels** 清單勾選作品，用 **Takedown selected novels** 動作測試下架（F2）。
7. 導覽列右側的語言下拉選單切換 **English / 繁體中文**（G1）：切到中文後，導覽列、
   分類（`Fantasy` → 奇幻）、按鈕、訊息全部變中文，但書名與章節正文仍是英文。

---

## 6. 常見問題

**Q1：`.venv` 不見了怎麼辦？**

重新建立並安裝套件：

```powershell
cd "C:\Users\taklo\Downloads\2026 semA\cs3383\project 2026"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install "Django==5.2.19" "Pillow==13.0.0"
```

**Q2：`can't open file 'manage.py'`**

你不在 `src/` 目錄。先 `cd src` 再執行。

**Q3：`Port 8000 is already in use`**

換一個 port：

```powershell
python manage.py runserver 8080
```

或找出佔用者：

```powershell
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
```

**Q4：想完全重置資料庫**

```powershell
cd src
Remove-Item db.sqlite3
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py seed_demo
```

**Q5：介面切到中文後還是英文？**

翻譯已全部完成（`locale/zh_Hant/LC_MESSAGES/django.po`，165 條訊息），正常情況切換語言就會全部變中文。若仍是英文，依序檢查：

1. **`.mo` 是否已編譯**——`.po` 改過後一定要重新編譯：

   ```powershell
   cd src
   $env:Path += ";..\.venv\Scripts\gettext\bin"
   ..\.venv\Scripts\python.exe manage.py compilemessages
   ```

2. **目錄名稱必須是 `zh_Hant`**（底線、大寫 H）。Django 會把語言代碼 `zh-hant`
   轉成 locale 目錄 `zh_Hant`；若命名成 `zh-hant`，翻譯檔會被忽略。

3. **用導覽列的語言選單切換**（寫入 `django_language` cookie）。網站所有路徑都不帶
   語言前綴（`/`、`/novels/`），語言只由 cookie 決定，所以不要手動輸入 `/zh-hant/`。

4. **改過翻譯後要重新載入頁面**；若開發伺服器有快取，重啟 `runserver`。

需要新增或修改介面文字時：

```powershell
cd src
$env:Path += ";..\.venv\Scripts\gettext\bin"
..\.venv\Scripts\python.exe manage.py makemessages -l zh_Hant --ignore=".venv/*" --ignore="locale/*"
# 編輯 ../locale/zh_Hant/LC_MESSAGES/django.po，填入 msgstr
..\.venv\Scripts\python.exe manage.py compilemessages
```

分類名稱（奇幻、科幻……）同樣來自這份翻譯檔，資料庫只存英文（`Fantasy`）。
作品內容（書名、章節正文、簡介、留言）一律不翻譯。

---

## 7. 專案結構速覽

```
project 2026/
├── src/                ← 所有程式碼與 manage.py、db.sqlite3
│   ├── config/         settings.py、urls.py、middleware.py
│   ├── accounts/       使用者、Profile、權限策略
│   ├── novels/         作品、章節、NovelService、seed_demo
│   ├── interaction/    收藏、留言、評分
│   ├── templates/      HTML 模板
│   └── static/         CSS
├── docs/diagrams/      UML / ER / Sequence 圖
├── locale/zh_Hant/     i18n 翻譯檔（django.po / django.mo）
├── .venv/              Python 虛擬環境（含 gettext 工具）
├── agent.md            需求與設計決策
└── ENVIRONMENT.md      環境版本紀錄
```
