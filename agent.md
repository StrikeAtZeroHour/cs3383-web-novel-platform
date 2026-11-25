# Web Novel Platform

讀者與創作者雙端 Web 小說平台。讀者可瀏覽、閱讀、收藏、評論；創作者可發布作品、管理章節。

#
任務：使用ai agent 完成此項目

專案性質：prototype（以快速可運作、易於測試與撰寫報告為目標）

## 技术栈（方案 B：Django + SQLite）

- 前端：Django Templates + Bootstrap 5（CDN，無 build step）
- 后端：Python + Django 5.x
- 数据库：SQLite（`db.sqlite3`，零設定）
- 認證：Django 內建 `django.contrib.auth`（所有登入用戶皆可創作，不區分 reader / author）
- 國際化：Django i18n + gettext（中英雙語，導覽列語言下拉選單）
- 圖片上傳：Django `ImageField` + `MEDIA_ROOT`（本地儲存封面圖）
- 測試：Django 內建 `TestCase`（`python manage.py test`）
- 管理後台：Django Admin（可客製）
- AI Agent：opencode + DeepSeek API

### 選型理由

- 內建 ORM、認證、Admin、測試框架、i18n，幾乎不用自己造輪子
- 只需一套語言（Python），開發與測試成本低
- 50+ 測試案例可直接用 Django TestCase 撰寫，容易達標
- ORM Model 可直接對應 UML class diagram 與 ER diagram

## 權限模型

- **訪客**（未登入）：瀏覽、搜尋、閱讀章節
- **已登入用戶**：以上 + 發布作品、管理自己的作品、收藏、評論（只能修改/刪除自己的內容）
- **admin**（Django 內建 `is_staff` / `is_superuser`）：透過 Django Admin 管理全部內容

> 人人皆可創作（像 Pixiv / AO3），不設「作者申請」流程，不使用 role 欄位。

## 專案結構（實際）

程式碼全部在 `src/`（`manage.py`、`db.sqlite3` 也在其中），文件與虛擬環境在專案根目錄。

```
project 2026/
├── src/
│   ├── config/          # settings.py, urls.py, middleware.py
│   ├── accounts/        # 個人主頁、個人資料
│   ├── novels/          # Novel、Chapter、Category、seed_demo
│   ├── interaction/     # Favorite、Comment、Rating
│   ├── templates/       # 共用模板
│   └── static/          # 自訂 CSS / JS
├── locale/zh_Hant/      # i18n 翻譯檔（django.po / django.mo）
├── docs/diagrams/       # UML / ER / Sequence / Use Case
└── .venv/               # 虛擬環境（含 gettext 工具）
```

## 主要資料模型（實際，已含 v2 擴充）

- `User`（沿用 Django 內建，不需 role 欄位）
- `Profile`（user OneToOne: nickname, avatar, bio, **email_verified**）
- `Category`（name：只存英文標籤，顯示文字由 gettext `label` 提供）
- `Tag`（name；Novel M2M `tags`）
- `Volume`（novel FK, title, order）— 卷階層
- `Novel`(title, author FK, cover, summary, category FK, status[ongoing/completed], is_published[預設 False], **tags M2M, view_count, word_count**, created_at, updated_at)
- `Chapter`（novel FK, **volume FK(nullable)**, order, title, content, is_active, **is_draft, scheduled_at, view_count, word_count**, created_at, published_at；`save()` 自動計算字數）
- `Favorite`（user + novel，unique together）
- `Comment`（user, chapter FK, content, is_active, **is_spoiler, likes M2M(user)**, parent FK（**多層回覆**）, created_at）
- `Rating`（user + novel，unique together，score 1–5）
- `ReadingProgress`（user + novel unique，chapter FK, updated_at）— 閱讀進度
- `Notification`（recipient, kind[reply/new_chapter], message, url, is_read, created_at）
- `Follow`（follower + author，unique together）
- `Report`（reporter, novel/comment nullable, reason, status[open/resolved/rejected], created_at）
- `OutlineItem`（novel FK, title, body, order）— 寫作大綱

### 刪除策略（統一說明）

| 對象 | 做法 | 說明 |
|---|---|---|
| 作品 | **硬刪除** | `NovelService.delete_novel()`，FK CASCADE 連帶章節、留言、收藏、評分 |
| 章節 | **軟刪除** | `is_active=False`，保留 `order` 不重排 |
| 留言 | **軟刪除** | `is_active=False`，不觸發 CASCADE |
| 作品下架（admin） | `is_published=False` | `Novel` 沒有 `is_active`，用 `is_published` 控制曝光 |
| 章節／留言下架（admin） | `is_active=False` | F2 |

> `on_delete=CASCADE` 只在真正呼叫 `obj.delete()` 時生效；日常「刪除」操作一律走軟刪除。

## 專案範圍（Scope）

### 目標（In Scope）

本專案是 **CS3383 課程專案**，定位為**可運作的 prototype**，目標是展示完整的軟體工程流程（需求 → 分析設計 → 實作 → 測試 → 缺陷管理），而非上線營運的產品。

| 面向 | 本專案涵蓋 |
|---|---|
| **使用者** | 訪客、已登入用戶、admin 三種身分；**人人皆可創作**，無作者申請流程 |
| **內容** | 單一平台內的長篇小說（文字），含封面圖；分類由 admin 預先建立 |
| **閱讀** | 瀏覽、搜尋、分類／標籤／狀態／字數篩選、排序、排行榜、最近更新、閱讀章節、上一章／下一章、章節目錄頁、**閱讀進度續讀**、瀏覽數統計 |
| **互動** | 收藏、章節留言（含**多層回覆、按讚、劇透標記**）、作品評分（1–5 星）、**追蹤作者、通知、違規檢舉** |
| **創作** | 新增／編輯／刪除作品、章節增刪改與排序、發布控制、**卷階層、章節草稿、定時發布、字數統計、作者儀表板、寫作大綱** |
| **管理** | Django Admin 管理全部資料、下架違規內容、**檢舉佇列** |
| **語系** | 中英雙語（Django i18n），介面文字翻譯，使用者內容不翻譯 |
| **整合** | **只讀 JSON API**（`/api/novels/`）、CI（GitHub Actions）、env 化設定、lockfile |
| **品質** | 自動化測試 **187 個、100% 覆蓋率**、Bug Report > 10 份 |

### v2 擴充（本次新增，原列於 Out of Scope 者已改為實作）

| 功能 | 實作方式 |
|---|---|
| 閱讀進度（C5） | `ReadingProgress`（每用戶每作品一筆），章節頁 upsert、詳情頁「Continue reading」 |
| 瀏覽數 / 字數（E8） | `Novel.view_count / word_count`、`Chapter.view_count / word_count`（CJK 逐字、Latin 逐詞） |
| 排行榜 / 最近更新 | `/rankings/`（最熱/最多瀏覽/最高評分/最多討論/最新）、`/recent/` |
| 標籤、狀態、字數篩選 | `Tag` M2M + `novel_list` 篩選參數 |
| 卷階層（C4） | `Volume` model + 建立端點；章節可掛卷 |
| 章節草稿 / 定時發布（C6） | `Chapter.is_draft`、`scheduled_at`；讀取時判斷（無排程器） |
| 章節目錄頁 | `/novels/<pk>/toc/`（依卷分組、錨點） |
| 寫作大綱 | `OutlineItem` + `/my/novels/<pk>/outline/` |
| 作者儀表板 | `/my/dashboard/`（收藏/評論/瀏覽/字數） |
| 多層留言 + 讚 + 劇透（D6） | `parent` 不限層數、`likes` M2M、`is_spoiler` |
| 追蹤作者 | `Follow` + follow/unfollow 端點 |
| 通知（C17） | `Notification` + 列表/標為已讀 |
| Email 驗證 / 密碼重設 | `Profile.email_verified` + verify 端點；Django `PasswordResetView` |
| 違規檢舉（F2） | `Report` model + 使用者檢舉表單 |
| 只讀 JSON API | `novels/api.py`（列表/詳情，metadata） |
| 工程 | `.github/workflows/test.yml`、`requirements.lock`、env 化 `SECRET_KEY/DEBUG/ALLOWED_HOSTS` |

### 不做的範圍（Out of Scope）

以下功能**明確排除**，報告中會以「未來工作（Future Work）」說明理由：

| 排除項目 | 理由 |
|---|---|
| **付費 / 訂閱 / 打賞** | 涉及金流與法規，與課程目標無關 |
| **即時通知**（WebSocket） | 需 ASGI / channel layer；目前通知為資料庫輪詢式（非即時推送） |
| **全文檢索引擎**（Elasticsearch） | SQLite `icontains` 已足夠展示搜尋功能 |
| **圖片裁切／壓縮／CDN** | 使用 `ImageField` 本地儲存即可（未加上傳大小/尺寸驗證） |
| **私訊 / 動態牆** | 追蹤作者已實作；私訊與動態牆仍不做 |
| **富文本編輯器** | 章節內容存純文字，安全且易測試 |
| **行動 App / 原生客戶端** | 以 Bootstrap 5 響應式網頁取代 |
| **多語系內容翻譯** | 只翻譯介面，不翻譯小說內容 |
| **資料匯出 / 匯入** | 仍無實作（未做 CSV/JSON 匯出） |
| **部署到雲端（含 HTTPS、備份）** | 只在本地 `runserver` 執行；已 env 化設定但未提供部署設定 |

> 已從此表移除並實作：追蹤作者、多層留言、資料庫通知、章節草稿/定時發布、卷階層、閱讀進度、瀏覽數、字數、排行榜、檢舉。詳見「v2 擴充」。

### 技術限制（Constraints）

| 限制 | 內容 | 影響 |
|---|---|---|
| **資料庫** | SQLite 單檔，不支援高併發寫入 | 適合 demo，不適合正式上線；`CHECK` 約束僅為規格建議 |
| **伺服器** | Django 開發伺服器（`runserver`） | 非 production 等級，不處理 static files 的正式部署 |
| **Python 版本** | 3.14.2 | Django 5.2 **自 5.2.8 起官方支援 Python 3.14**（本專案用 5.2.19），無相容性風險 |
| **時間** | 課程時程內完成 | 功能以 39 項需求為上限，不追加 |
| **人力** | 小組作業 | 以 AI agent 輔助產生程式碼，需清楚標註 AI / 人類貢獻比例 |

### 成功標準（Definition of Done）

1. 39 項需求中，**27 項必須（✅）全部完成**；v2 擴充功能亦全部實作
2. 每個 app 皆有 `TestCase`，**實際 187 個測試、100% 覆蓋率**，全數通過
3. 三張核心 UML 圖 + 5 張 Sequence Diagram 完成並可渲染
4. 至少 **10 份**格式完整的 Bug Report（含重現步驟、期望／實際結果）
5. 中英雙語切換可用：導覽列切換後**全站介面**（含分類名稱）即時變中文／英文，資料庫與程式碼不含中文
6. 報告依 `Final_Report_Marking_Scheme.docx` 八個項目撰寫

---

## 需求清單（功能列表）

圖示：✅ 必須　🔵 應該　🟡 加分

### A. 帳號與權限（accounts）

| 編號 | 功能 | 說明 | 優先 |
|---|---|---|---|
| A1 | 註冊 | 用戶名、Email、密碼 | ✅ |
| A2 | 登入／登出 | 使用 Django 認證，導覽列顯示登入狀態 | ✅ |
| A3 | 個人主頁 | 暱稱、頭像、簡介 +「我的創作／我的收藏」分頁 | ✅ |
| A4 | 編輯個人資料 | 修改暱稱、頭像、簡介 | 🔵 |
| A5 | 修改密碼 | 使用 Django 內建 `PasswordChangeForm`（正確更新資料庫雜湊密碼） | 🔵 |
| A6 | 權限規則 | 訪客可閱讀；登入者可創作/收藏/評論；僅作者本人或 admin 可編輯/刪除自己的作品與評論 | ✅ |

### B. 作品瀏覽（讀者端）

| 編號 | 功能 | 說明 | 優先 |
|---|---|---|---|
| B1 | 首頁 | 最新更新、熱門收藏作品 | ✅ |
| B2 | 作品列表 | 分頁展示所有已發布作品 | ✅ |
| B3 | 搜尋 | 按書名／作者名搜索 | ✅ |
| B4 | 分類篩選 | 按 Category 過濾 | ✅ |
| B5 | 作品詳情頁 | 封面、簡介、作者、分類、狀態、章節列表、收藏數、評論數 | ✅ |
| B6 | 排序 | 最新、最多收藏、最多評論 | 🔵 |
| B7 | 作者主頁 | 展示某作者所有已發布作品 | 🔵 |

### C. 閱讀

| 編號 | 功能 | 說明 | 優先 |
|---|---|---|---|
| C1 | 章節閱讀頁 | 標題 + 正文 | ✅ |
| C2 | 上一章／下一章 | 章節導航 | ✅ |
| C3 | 章節目錄 | 從作品頁跳轉到任意章節 | ✅ |
| C4 | 免登入閱讀 | 訪客也能看章節 | ✅ |
| C5 | 閱讀進度記錄 | 記住上次讀到哪個章節（`ReadingProgress`，詳情頁續讀） | ✅ 已實作 |

### D. 互動（interaction）

| 編號 | 功能 | 說明 | 優先 |
|---|---|---|---|
| D1 | 收藏／取消收藏 | 登入後可收藏，同作品不得重複 | ✅ |
| D2 | 我的收藏 | 收藏列表（個人主頁分頁） | ✅ |
| D3 | 章節評論 | 在章節下發表評論 | ✅ |
| D4 | 刪除評論 | 評論作者本人或 admin 可刪 | ✅ |
| D5 | 評論分頁 | 按時間排序顯示 | 🔵 |
| D6 | 評論回覆 | 多層回覆（parent FK，不限層數） | 🔵 已實作 |
| D7 | 作品評分 | 每人對每部作品打 1–5 星，可修改 | 🔵 |

### E. 創作（所有登入用戶皆可使用）

| 編號 | 功能 | 說明 | 優先 |
|---|---|---|---|
| E1 | 我的作品 | 列表顯示自己的所有作品與狀態 | ✅ |
| E2 | 新建作品 | 書名、封面、簡介、分類、狀態（連載中／已完結）；`author` 由系統指定為登入者；建立後 `is_published=False` | ✅ |
| E3 | 編輯作品 | 修改上述欄位 | ✅ |
| E4 | 刪除作品 | 僅作者本人或 admin 可刪 | ✅ |
| E5 | 章節管理 | 新增／編輯／刪除章節 | ✅ |
| E6 | 章節排序 | 依 `order` 自動編排章節，可調整順序 | ✅ |
| E7 | 發布控制 | 作品建立後預設**不公開**，作者按下「發布」才出現在列表與搜尋結果；發布不要求有任何章節 | 🔵 |
| E8 | 作品統計 | 作者儀表板顯示收藏數、評論數、瀏覽數、字數 | 🟡 已實作 |

### F. 管理後台（admin）

| 編號 | 功能 | 說明 | 優先 |
|---|---|---|---|
| F1 | Django Admin | 管理 User / Novel / Chapter / Comment / Category / Rating | ✅ |
| F2 | 內容下架 | 隱藏違規內容：**作品**設 `is_published=False`；**章節／評論**設 `is_active=False` | 🟡 |

### G. 系統與非功能

| 編號 | 功能 | 說明 | 優先 |
|---|---|---|---|
| G1 | UI 與 i18n | Bootstrap 5 響應式；中英雙語，導覽列語言下拉選單（Django i18n + gettext，含分類名稱） | ✅ |
| G3 | 表單驗證 | Django Forms 驗證所有輸入 | ✅ |
| G4 | 自動化測試 | 每個 app 都有 TestCase，總數 > 50 | ✅ |
| G5 | 種子資料 | management command 灌入示範資料（用戶、作品、章節、評論） | 🔵 |

### 統計

- ✅ 必須：27 項
- 🔵 應該：9 項
- 🟡 加分：3 項
- 合計：**39 項功能**
- **全部 39 項已實作**；另加 v2 擴充（排行、標籤、卷、草稿、定時、字數、儀表板、大綱、多層留言/讚/劇透、追蹤、通知、檢舉、Email 驗證、重設、JSON API、CI、env 設定）

> 註：原 G2（自訂錯誤頁）已移除，編號保留空缺以維持追溯性；G4、G5 屬開發活動，不對應畫面功能。

## 設計決策記錄

1. **人人皆可創作**：不設角色區分與作者申請流程，權限規則為「已登入可創作，僅能改自己的內容」，與 Pixiv / AO3 一致。
2. **評論掛在章節**：與閱讀情境結合，作品頁顯示評論總數。
3. **保留評分（1–5 星）**：成本低，可增加測試案例。
4. **支援多層回覆**（v2 調整）：以 `parent` 自關聯 FK 實作，原本限制一層，v2 放寬為不限層數（模板遞迴顯示）。`CommentForm` 只驗證父留言存在與屬同一章節。
5. **中英雙語（gettext 實作）**：所有介面文字用 `{% trans %}` 或 `gettext` 標記；用戶內容（書名、正文、簡介、留言）不翻譯；英文為基底語言，中文缺翻譯時 fallback 回英文。
6. **修改密碼走 Django 內建表單**：資料庫存的是雜湊密碼，透過 `PasswordChangeForm` 由程式正確更新 `auth_user.password`。
7. **發布不要求有章節（E7）**：作品建立後為**未發布**（`is_published=False`），作者按「發布」後才公開。**「至少要有一章」不是平台規則**：因此不用「有沒有章節」阻擋發布。未發布或零章節的作品在詳情頁顯示「暫無章節」。
   - `Chapter.published_at` 記錄建立時間，`Novel.is_published` 是作品曝光開關；v2 另加 `Chapter.is_draft` / `scheduled_at` 控制單章可見性（草稿不對讀者顯示、定時在讀取時判斷是否到期），由 `ChapterQuerySet.visible()` 統一過濾。
8. **分類名稱用 gettext 翻譯，不設 `name_en` 欄位**（決議於 i18n 實作階段，取代原「`name` 存中文 + `name_en` 存英文」的設計）：
   - **問題**：原設計把中文寫進資料庫（`name='奇幻'`）與 `seed_demo`，違反「程式碼與初始化資料不寫中文」與「所有介面文字走 gettext」的原則，且同一件事有兩份真相（DB 與 `.po`）。
   - **決議**：`Category` 只保留一個 `name` 欄位，存**英文標籤**（`Fantasy`、`Science Fiction`…）；`name_en` 欄位移除（migration `0002_remove_category_name_en`）。中文由 `locale/zh_Hant/LC_MESSAGES/django.po` 提供，`seed_demo` 的分類名稱以 `_()` 標記。
   - **顯示方式**：`Category.label` 屬性 = `gettext(name)`，`__str__()` 回傳 `label`；模板用 `{{ category.label }}`，表單下拉選單因 `__str__` 而自動翻譯。
   - **評估過但不採用**：
     - `{% trans category.name %}`：Django 的 `trans` 對變數不保證翻譯（`.mo` 查表只對字面常數字串可靠）。
     - `{% blocktrans %}`：會讓資料庫內容進入翻譯檔，等於把資料誤當介面文字。
     - 直接讓 `{{ category.name }}` 自動翻譯：純變數輸出不做 gettext 查表（已實測），只有表單的 `__str__` 會轉。
   - **作品內容保持英文**：書名、章節、簡介、留言屬使用者資料，一律不翻譯，也不進 `.po`。
9. **locale 目錄為 `zh_Hant`，網站路徑不帶語言前綴**：
   - Django 以 `to_locale('zh-hant')` → `zh_Hant` 尋找翻譯目錄，目錄若命名成 `zh-hant` 會被**完全忽略**（makemessages 產生的預設名稱正是 `zh_Hant`）。
   - 原 `i18n_patterns(prefix_default_language=False)` 在切到中文後會 404：`LocalePrefixPattern` 以**當前語言**計算前綴，中文時期待 `zh-hant/`，而站內連結都是 `/novels/`。因此 `urls.py` 改回一般 `path()`，語言只由 `django_language` cookie（導覽列切換）決定。
   - Django 內建 `LocaleMiddleware` 在無語言前綴的路徑會強制回 `LANGUAGE_CODE`，故新增 `config/middleware.py::LocaleMiddleware`（繼承內建類、改用 cookie / `Accept-Language` 決定語言），設定 `Content-Language` 與 `Vary`。
10. **gettext 工具以 mlocati static build 安裝**：Windows 無內建 `xgettext`/`msgfmt`，安裝 GNU gettext 1.0（SHA256 已核對）至 `.venv/Scripts/gettext/` 並加入 PATH；`.mo` 不進版控，需執行 `compilemessages`。流程見 `ENVIRONMENT.md`。
11. **定時發布無排程器（v2）**：`Chapter.scheduled_at` 只做「讀取時判斷」（`visible()` 過濾 `scheduled_at > now`），不引入 Celery / cron，維持同步 stack；到期與否在每次查詢即時計算。
12. **環境變數化設定（v2）**：`SECRET_KEY / DEBUG / ALLOWED_HOSTS` 由環境變數讀取；`DEBUG=False` 且無 `DJANGO_SECRET_KEY` 時啟動直接 `ImproperlyConfigured`，避免誤用開發金鑰上線。開發以 `.env`（`.env.example` 為範本）提供。測試工具（coverage / pytest / pytest-django）置於 `requirements-dev.txt`，執行期相依鎖在 `requirements.lock`。
13. **測試策略（v2）**：Django `TestCase` 為主要 runner（`manage.py test`）；VS Code Testing 面板改用 `pytest + pytest-django`（官方建議的 Django 路徑），兩者皆可跑同一批 187 測試。覆蓋率以 `coverage --branch` 量測，維持 statements/branches 100%。

## 報告對應（Final_Report_Marking_Scheme.docx）

- Summary and Requirements（10）：本文件的需求清單
- Project Plan（10）：範圍、估時、限制條件
- Analysis and Design（20）：use case diagram + UML class diagram + ER diagram
- Implementation（20）：需清楚標註 AI 生成 vs. 人類修改的程式碼
- Test Cases（20）：> 50 個測試案例與測試策略
- Bug Report（10）：> 10 份詳細 bug 報告
- Weekly Activity（10）：每週活動記錄與組員分工

## 後續步驟

1. 畫 use case diagram + UML class diagram + ER diagram
2. 建立 Django 專案骨架與 models.py
3. 依需求清單逐項實作
4. 撰寫測試（目標 > 50）
5. 收集 bug 報告與週報
