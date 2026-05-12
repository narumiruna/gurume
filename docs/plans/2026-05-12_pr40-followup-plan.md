# PR #40 Follow-up Plan

## Goal

先合併 PR #40（genre filtering / magazine 過濾 / suggest API 錯誤處理），再以一個 follow-up PR 解決 review 中提出的四項問題：TUI regression、URL build 邏輯重複、`/A` 過濾過寬、缺少對應測試。完成標準：PR #40 merged 到 `main`；follow-up PR merged 且 CI 全綠。

## Context

PR #40 review 摘要（詳見對話）：

1. **TUI regression（高優先）**：`suggest.py` 新增 `TabelogSuggestUnavailableError(RuntimeError)`，但 `tui.py:633`（地區建議）與 `tui.py:749`（關鍵字建議）沒有 try/except，原本回傳 `[]` 顯示「找不到建議」的路徑，現在會讓 worker 拋例外。
2. **URL build 三處重複且不一致**：`search.py::_build_url_and_params`、`restaurant.py::search_sync`、`restaurant.py::search`（async）三處 if/elif 區塊邏輯應抽 helper 或至少統一（`params.pop("sa")` 與 url 重設在三處行為不同）。
3. **magazine 過濾 `"/A" in url` 過寬**：可能誤判 `/About`、`/Ad...` 等路徑，建議改成 `re.search(r"/A\d+/A\d+/\d+", url)` 之類嚴格判斷。
4. **缺測試**：`LstG` URL building、magazine 過濾、`suggest_empty` raises、`Prefecture` datatype parse —— AGENTS.md 規範要求變更 search/parsing/MCP 邏輯時補測試。

目前分支：`AndreasThinks/main`（PR #40 checkout 出來的 fork 分支）。

## Non-Goals

- 不在 follow-up PR 重寫整個 search/restaurant 模組架構；只做最小一致化。
- 不修改 PR #40 已合併的對外 API 介面（`TabelogSuggestUnavailableError` 名稱、`SuggestionDatatype` 等保留）。

## Plan

### Phase 1：Merge PR #40

- [x] 切回 `main` 並確認本地乾淨：`git checkout main && git status` 顯示 clean working tree。
- [x] 在 GitHub 上 merge PR #40（squash 或 merge commit 視 repo 慣例）；驗證：`gh pr view 40 --json state -q .state` 回傳 `MERGED`。
- [x] 本地同步 main：`git checkout main && git pull --ff-only`，驗證 `git log -1 --oneline` 含 PR #40 的 squash/merge commit。

### Phase 2：開 follow-up 分支

- [x] 從最新 main 開分支 `fix/pr40-followup`：`git checkout -b fix/pr40-followup`；驗證 `git branch --show-current` 為該分支名。

### Phase 3：TUI regression 修復（最高優先）

- [x] 在 `src/gurume/tui.py:633` 附近以 `try/except TabelogSuggestUnavailableError` 包住 `await get_area_suggestions_async(query)`，例外時呼叫 `detail_content.update(...)` 顯示 `TabelogSuggestUnavailableError.HELP` 訊息；驗證：手動 `uv run gurume tui` + 模擬 `{"suggest_empty": true}` 不會崩潰（可暫時 monkeypatch 測試）。
- [x] 同樣處理 `src/gurume/tui.py:749` 的 `get_keyword_suggestions_async` 呼叫。
- [x] 在 `tests/test_suggest.py` 加 unit test：mock httpx 回傳 `{"suggest_empty": true}` 時，`get_area_suggestions` 與 `get_keyword_suggestions`（及 async 版本）都 raise `TabelogSuggestUnavailableError`；驗證 `uv run pytest tests/test_suggest.py -v` 通過。

### Phase 4：URL build 邏輯統一

- [x] 在 `src/gurume/search.py`（或新檔 `_url_builder.py`）抽出 `build_search_url_and_params(area_slug, genre_code, params) -> tuple[str, dict]` helper，三個分支統一處理 url 與 `params.pop("sa")`、`params["LstG"]`。
- [x] 將 `search.py::_build_url_and_params` 改為呼叫 helper；驗證 `uv run pytest tests/test_search.py -v` 通過。
- [x] 將 `restaurant.py::search_sync` 與 `restaurant.py::search` 也改為呼叫同一 helper；驗證 `uv run pytest tests/test_restaurant.py -v` 通過。
- [x] 新增 `tests/test_search.py` 中對 helper 的單元測試：覆蓋 `(area, genre)`、`(area, no genre)`、`(no area, genre)`、`(no area, no genre)` 四種組合，鎖住 `LstG` 在 query string 而非 URL path；驗證 `uv run pytest tests/test_search.py::test_build_search_url_and_params -v` 通過。

### Phase 5：magazine 過濾收緊

- [x] 在 `src/gurume/restaurant.py` 將 `"/A" in str(fallback.get("href", ""))` 換成模組層級 `re.compile(r"/A\d+/A\d+/\d+")` 的 `search()` 判斷；保留現有 `"magazine.tabelog.com" in url` 黑名單。
- [x] 在 `tests/test_restaurant.py` 加 parsing test：餵入含 `magazine.tabelog.com` 連結與含 `/About` 之類路徑的 fixture，斷言 `_parse_basic_info` 回傳 `(None, "")`；餵入正常 `/tokyo/A1301/A130101/13xxxxx/` 連結時回傳實際 name/url。驗證 `uv run pytest tests/test_restaurant.py -v` 通過。

### Phase 6：補 `Prefecture` datatype 測試

- [x] 在 `tests/test_suggest.py` 加 test：mock 回傳含 `"datatype": "Prefecture"` 的 item，斷言不會 raise 並正確 parse 為對應 suggestion 物件；驗證 `uv run pytest tests/test_suggest.py -v` 通過。

### Phase 7：品質閘門 + 開 PR

- [x] 跑完整品質檢查：`make lint && make type && make test` 全部通過。
- [x] 在 `docs/LOG.md` 末尾追加一行：`YYYY-MM-DD | fix(search): pr40 followup (...)`。
- [x] 推 branch 並開 PR：`git push -u origin fix/pr40-followup && gh pr create`；PR 描述列出四項 review 點與對應修復；驗證 `gh pr view --json state -q .state` 為 `OPEN` 且 CI 綠燈。

## Risks

- **PR #40 merge 後其他分支 rebase 衝突**：follow-up 動到 `restaurant.py`/`search.py`/`suggest.py` 同樣熱區。緩解：先 merge PR #40，再從 latest main 開分支。
- **URL helper 抽離可能改變既有行為**：三處邏輯目前微妙不同（`pop("sa")` 與 url 重設）。緩解：先用測試鎖住 PR #40 現行行為，再重構。

## Completion Checklist

- [x] PR #40 在 GitHub 上狀態為 MERGED，驗證 `gh pr view 40 --json state -q .state` 輸出 `MERGED`。
- [ ] Follow-up PR 已開且 CI 全綠，驗證 `gh pr view <new-pr> --json state,statusCheckRollup` 顯示 OPEN + 所有 check SUCCESS。
- [x] TUI 不會在 suggest API 回 `suggest_empty` 時崩潰，驗證 `tests/test_suggest.py` 對應 unit test 通過、且 TUI 兩處呼叫點都有 try/except `TabelogSuggestUnavailableError`（`rg "TabelogSuggestUnavailableError" src/gurume/tui.py` 顯示兩處 match）。
- [x] URL build 邏輯只剩單一 helper，驗證 `rg "LstG" src/gurume/` 只出現在 helper 與測試檔；`uv run pytest tests/test_search.py tests/test_restaurant.py -v` 通過。
- [x] magazine 過濾使用 regex，驗證 `tests/test_restaurant.py` 對應 fixture 測試通過。
- [x] `Prefecture` datatype 有測試覆蓋，驗證 `uv run pytest tests/test_suggest.py -k Prefecture -v` 通過。
- [x] `make lint && make type && make test` 全部通過。
- [x] `docs/LOG.md` 末尾已追加一行 follow-up 紀錄，驗證 `tail -1 docs/LOG.md`。
