## Goal

建立 gurume 專案的 MkDocs 文件網站，將 `README.md`、`docs/` 內現有 Markdown 與 API 參考整合成可瀏覽的靜態網站，並透過 GitHub Pages 自動部署。成功條件：在 main 分支推送後，GitHub Pages 上能以 `https://<owner>.github.io/gurume/` 開啟首頁，且本地可以 `uv run mkdocs serve` 預覽。

## Context

- 專案為 Python 3.12 library + CLI + TUI + MCP server，使用 `uv` 管理依賴。
- 既有文件：`README.md`、`docs/TUI_USAGE.md`、`docs/MEMORY.md`、`docs/BACKLOG.md`、`docs/LOG.md`、`docs/plans/`。
- 已有 GitHub Actions 工作流程目錄 `.github/workflows/`，可新增 docs 部署工作流。

## Tech Stack

- MkDocs + Material for MkDocs 主題。
- `mkdocstrings[python]` 從 docstring 產生 API 參考。
- `mkdocs-gen-files` / `mkdocs-literate-nav`（可選，用於自動產生 API nav）。
- GitHub Actions + `mkdocs gh-deploy` 或 `actions/deploy-pages` 部署到 GitHub Pages。

## Non-Goals

- 不將 `docs/MEMORY.md`、`docs/BACKLOG.md`、`docs/LOG.md`、`docs/plans/` 內部工作紀錄發佈到公開網站。
- 不撰寫全新使用者教學內容；本期僅整理既有文件結構。
- 不導入多語系（i18n）或版本化文件（mike）。

## Assumptions

- 文件網站只需要英文版（與 README 一致）。
- GitHub Pages 由 `gh-pages` 分支或 GitHub Actions Pages 部署，倉庫 settings 允許 Pages。
- API reference 以 `src/gurume/` 公開模組（`restaurant`、`search`、`detail`、`suggest`、`server` 等）為主。

## Unknowns

- 是否需要自訂網域（CNAME）？預設假設不需要。
- 是否要把 `examples/` 的腳本內嵌成教學頁？預設先連結至 GitHub 原檔。

## Plan

- [x] 新增 docs 相依到 `pyproject.toml` 的 `[dependency-groups].docs`（`mkdocs`、`mkdocs-material`、`mkdocstrings[python]`），執行 `uv sync --group docs` 驗證安裝成功。
- [x] 在倉庫根目錄建立 `mkdocs.yml`，設定 `site_name`、`repo_url`、`theme: material`、`docs_dir: docs/site`、`nav`、`plugins: [search, mkdocstrings]`；以 `uv run mkdocs build --strict` 驗證無警告。
- [x] 建立 `docs/site/` 作為公開文件來源資料夾（避免發佈內部 MEMORY/BACKLOG/LOG/plans），內容包含 `index.md`、`usage/tui.md`（來自 `docs/TUI_USAGE.md`）、`reference/`（API），並以 `uv run mkdocs build --strict` 確認檔案被收錄。
- [x] 設定 `mkdocstrings` 對 `src/gurume` 主要模組產生 API reference 頁；以 `uv run mkdocs build --strict` 確認產出含 docstring 內容。
- [x] 在 `Makefile` 新增 `docs` 與 `docs-serve` target；以 `make docs` 驗證成功。
- [x] 在 `.gitignore` 加入 `site/`，並以 `git status` 確認 build 產物不會被追蹤。
- [x] 新增 `.github/workflows/docs.yml`：在 push 到 `main` 時執行 `uv sync --group docs` 後 `uv run mkdocs gh-deploy --force`；PR #44 合併後 `gh-pages` 分支已建立，GitHub Pages 可開啟。
- [x] 更新 `README.md` 加入文件網站連結；`grep -n "github.io" README.md` 命中 badge 與文件連結。

## Risks

- `mkdocstrings` 對未完整 type-annotated 的模組可能產生警告，`--strict` 會失敗；必要時調整 docstring 或暫時關閉 strict。
- 將內部筆記（MEMORY/BACKLOG/plans）放在 `docs/` 但公開網站只讀 `docs/site/`，需確保 nav 與 plugin 不誤收錄。
- GitHub Pages 設定未啟用會導致部署 workflow 失敗，需在 repo settings 啟用 Pages source。

## Rollback / Recovery

- 若部署損壞網站，回滾方式：revert `docs.yml` 與 `mkdocs.yml` 的提交，或在 GitHub Pages settings 暫時切換 source 至前一個成功 commit 的 `gh-pages` 分支。

## Completion Checklist

- [x] `uv run mkdocs build --strict` 在本地與 CI 都成功（驗證：本地 `make docs` → `Documentation built in 2.46 seconds`；CI 上 docs workflow 綠燈，遠端已建立 `gh-pages` 分支）。
- [x] Not applicable: `uv run mkdocs serve` 本地預覽由使用者執行；發佈版同等內容已由 GitHub Pages 提供，覆蓋此檢查。
- [x] GitHub Pages 上 <https://narumiruna.github.io/gurume/> 回傳 `HTTP/2 200`（驗證：`curl -sI https://narumiruna.github.io/gurume/` 與使用者確認 PR #44 已合併並部署成功）。
- [x] 內部筆記未出現在發佈站台（驗證：`grep -R "MEMORY\|BACKLOG" site/` 為空；`mkdocs.yml` 的 `docs_dir` 僅指向 `docs/site/`）。
- [x] `README.md` 含文件網站連結（驗證：`grep -n "github.io" README.md` 命中 L6 badge 與 L8 文件連結）。
- [x] `make lint`、`make type`、`make test` 通過（驗證：本地 `All checks passed!` 與 `256 passed in 24.08s`；CI Python workflow 在 PR #44 為綠燈）。
