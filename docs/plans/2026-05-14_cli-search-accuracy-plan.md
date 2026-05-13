## Goal

讓 CLI 的 `gurume search` 在「地區 + 料理類別 / keyword」搜尋時，不只是不 crash，也能穩定回傳符合指定地區與料理條件的 Tabelog 餐廳結果。

成功條件：已知錯誤案例（`札幌 + カレー`、`名古屋 + うなぎ`、`神戸 + カフェ`）不再回傳跨縣市排名結果，且現有東京、大阪、京都、福岡、沖縄等搜尋仍正常。

## Context

Smoke test 顯示 CLI exit code 都是 0，但部分地區名稱無法轉成 Tabelog path slug，導致搜尋退回較寬鬆的 `/rst/rstsearch` 或只套用料理分類，結果可能跨地區：

- `札幌 + カレー` 回傳大阪、千葉店家。
- `名古屋 + うなぎ` 回傳金澤、東京店家。
- `神戸 + keyword カフェ` 回傳岐阜、福岡店家。

相關檔案：

- `src/gurume/area_mapping.py`：地區名稱到 Tabelog slug/path 的映射。
- `src/gurume/genre_mapping.py`：料理類別到 genre code / cuisine path segment 的映射。
- `src/gurume/restaurant.py`：`build_search_url_and_params()` 組 URL 與 query params。
- `src/gurume/cli.py`：`--cuisine` 與 keyword 自動料理偵測。
- `tests/test_area_mapping.py`、`tests/test_search.py`、`tests/test_restaurant.py`：應新增或調整測試。

## Non-Goals

- 不重寫整個搜尋架構。
- 不加入瀏覽器或 JS rendering 依賴。
- 不保證所有日本市區都能精準支援；先修復高頻城市與可驗證的 fallback 行為。

## Assumptions

- Tabelog 目前對「地區 + 料理」最可靠的形式仍是 path-based URL，例如 `/{area}/rstLst/{cuisine}/` 或更細城市 path。
- `sa=<area>` 與舊版 `LstG` 在部分頁面可能被忽略，不能單獨視為精準條件。
- 如果無法找到精準地區 path，CLI 應避免默默回傳明顯跨地區結果，至少要有可理解的警告或保守 fallback。

## Unknowns

- 札幌、名古屋、神戸在 Tabelog 上最適合使用 prefecture-level path、city/subarea path，還是 search endpoint query。
- `--keyword` 被自動偵測為 cuisine 時，是否應保留原 keyword 作為 `sk`，或改成純 cuisine path，以免造成 upstream 排序/過濾混淆。

## Plan

- [ ] 建立可重現問題的測試清單，記錄每個案例的實際 URL、params、前 3 筆結果地區與餐廳 URL；用 `uv run python` 小腳本或 pytest fixture 驗證並保存摘要到 issue/plan 註記。
- [ ] 調查 Tabelog 對 `札幌 カレー`、`名古屋 うなぎ`、`神戸 カフェ` 的正確 URL 形式，產出最小映射資料；用手動 `httpx` request 或 CLI debug 腳本確認前 3 筆 URL 屬於預期 prefecture/city。
- [ ] 擴充 `area_mapping.py`，把地區表示從單一 prefecture slug 升級為可描述 prefecture slug 與 city/subarea path 的結構，至少支援 `札幌`、`名古屋`、`神戸`；用 `uv run pytest tests/test_area_mapping.py` 驗證。
- [ ] 調整 `build_search_url_and_params()`，讓 area+cuisine 優先使用可驗證的 path-based URL；當 area 無法映射時，不要只用 `LstG` 產生看似成功但跨地區的結果；用新增單元測試驗證 URL 與 params。
- [ ] 檢查 `cli.py` 的 keyword 自動 cuisine 偵測策略，明確定義 `--keyword カフェ` 在有 area 時是否等同 cuisine filter；用 CLI 測試或單元測試固定預期行為。
- [ ] 新增「結果合理性」測試工具，對固定 smoke cases 檢查餐廳 URL path 包含預期 prefecture slug（如 `/hokkaido/`、`/aichi/`、`/hyogo/`），避免只檢查 exit code；用 mock HTML 單元測試覆蓋，真實網路測試作為手動 smoke script。
- [ ] 跑品質檢查：`uv run ruff check .`、`uv run ty check .`、`uv run pytest -v -s --cov=src tests`，修正回歸。
- [ ] 重新執行 CLI smoke test：全 29 種東京 cuisine、已知錯誤案例、多輸出格式 JSON/simple/table；保存命令摘要作為完成證據。

## Risks

- Tabelog URL 與 HTML 可能變動，過度依賴 live network 會讓測試不穩；核心測試應 mock URL building 與 parser 行為。
- 城市級 path mapping 可能不完整；若一次擴太多地區，維護成本會上升。
- 太嚴格的結果合理性檢查可能誤傷 Tabelog 合法的跨區推薦或廣告結果；檢查應聚焦餐廳 URL path，而不是顯示文字。

## Completion Checklist

- [ ] `札幌 + カレー`、`名古屋 + うなぎ`、`神戸 + カフェ` 的 CLI smoke test 前 3 筆結果 URL 均落在預期地區 path，並有命令輸出作為證據。
- [ ] `build_search_url_and_params()` 的 area+cuisine 與 unknown-area fallback 行為有單元測試覆蓋，並由 `uv run pytest` 驗證。
- [ ] `area_mapping.py` 的新增城市/地區映射有測試覆蓋，並由 `uv run pytest tests/test_area_mapping.py` 驗證。
- [ ] `uv run ruff check .`、`uv run ty check .`、`uv run pytest -v -s --cov=src tests` 全部通過。
- [ ] CLI 使用者面對無法精準映射的地區時，不會收到未警告的跨地區料理排名結果；由測試或明確輸出文案驗證。
