# 最終報告素材對照（Final Report Marking Scheme）

本檔把 `Final_Report_Marking_Scheme.docx` 的八個評分項目對應到本專案的實際產出，方便撰寫報告時直接取用。

## 快速數字

- 需求：39 項（27 必須 + 9 應該 + 3 加分）**全部實作**，另含 v2 擴充
- 測試：**187 個**，`coverage --branch` **100%**（statements 1029 / branches 148，0 missed / 0 partial）
- 模型：13 個自訂表（+ Django 內建 `auth_user`）
- 端點：約 40 條（HTML + 1 組唯讀 JSON API）
- Bug Report：**12 份**（`docs/bug-reports/README.md`）
- 截圖：**42 張**（`docs/screenshots/`，7 頁 × 3 寬度 × 明暗）

## 評分項目對照

| 評分項（配分） | 本專案素材 | 位置 |
|---|---|---|
| **Summary and Requirements (10)** | 需求清單 39 項 A–G、範圍、設計決策 1–14 | `agent.md` |
| **Project Plan (10)** | 技術棧、範圍（In/Out）、技術限制、成功標準、v2 擴充表 | `agent.md`、`README.md` |
| **Analysis and Design (20)** | Use Case 圖、UML Class 圖、ER 圖、Sequence 圖 SD-1～SD-10 | `docs/diagrams/01–04` |
| **Implementation (20)** | 三 app 分層（views/service/forms/models）、`NovelService`、權限 Strategy、v2 模組；AI 與人類貢獻說明 | `src/accounts`、`src/novels`、`src/interaction` |
| **Test Cases (20)** | 187 測試（`manage.py test` / `pytest`）、100% 覆蓋率、`TEST_COVERAGE.md` 行為對照 | `src/*/tests.py`、`src/TEST_COVERAGE.md` |
| **Bug Report (10)** | 12 份含重現/期望/實際/根因/修正/驗證 | `docs/bug-reports/README.md` |
| **Weekly Activity (10)** | 需人工補每週記錄（模板見下） | 待填 |

## 建議報告章節 → 圖表/證據

- 系統架構：`docs/diagrams/02-class-diagram.md`（含 v2 類別）
- 資料庫設計：`docs/diagrams/03-er-diagram.md`（13 表、FK/索引/約束）
- 使用案例：`docs/diagrams/01-use-case.md`（核心 + v2 用例表）
- 動態行為：`docs/diagrams/04-sequence.md`（SD-1～SD-10）
- UI 設計：`README.md`「UI 設計系統」段 + `docs/screenshots/`
- 測試策略：`src/TEST_COVERAGE.md`、`src/.coveragerc`、`.github/workflows/test.yml`

## Weekly Activity 模板（待各組員補）

| 週次 | 完成事項 | 對應 commit/功能 | 組員 |
|---|---|---|---|
| W1 | 需求與設計、專案骨架 | Initial commit | — |
| W2 | v2 功能（進度/排行/標籤/卷/草稿/通知…） | `605c19c` | — |
| W3 | UI 重做 + 深色模式 | `4482ed9` | — |
| W4 | UI 審計修正、文件同步、截圖、Bug Reports | `c5017ce`… | — |

## 重新產生證據的指令

```powershell
# 測試 + 覆蓋率
cd src
..\.venv\Scripts\python.exe -m coverage run --branch --rcfile=.coveragerc manage.py test
..\.venv\Scripts\python.exe -m coverage report -m
# 截圖（需 puppeteer；腳本見 docs/screenshots 產生方式）
```
