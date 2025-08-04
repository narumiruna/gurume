# 測試套件

這個測試套件為 `tabelog` 套件提供了全面的測試覆蓋。

## 測試結構

### 測試檔案

- `test_models.py` - 測試 Pydantic 模型和驗證
- `test_restaurant.py` - 測試餐廳搜尋核心功能
- `test_search.py` - 測試進階搜尋功能
- `test_integration.py` - 整合測試
- `test_cli.py` - 測試 CLI 工具功能

### 測試配置

- `conftest.py` - 測試配置和 fixtures
- `pytest.ini` - pytest 配置
- `__init__.py` - 標記為 Python 套件

## 運行測試

### 全部測試

```bash
uv run pytest tests/ -v
```

### 特定測試檔案

```bash
uv run pytest tests/test_models.py -v
uv run pytest tests/test_restaurant.py -v
uv run pytest tests/test_search.py -v
uv run pytest tests/test_integration.py -v
uv run pytest tests/test_cli.py -v
```

### 測試覆蓋率

```bash
uv run pytest tests/ --cov=src/tabelog --cov-report=term-missing
```

### 測試標記

```bash
# 運行單元測試
uv run pytest -m unit

# 運行整合測試
uv run pytest -m integration

# 跳過慢速測試
uv run pytest -m "not slow"
```

## 測試類別

### 單元測試

#### TestRestaurant
- `test_restaurant_creation` - 測試創建餐廳物件
- `test_restaurant_minimal_creation` - 測試最小必要欄位

#### TestRestaurantSearchRequest
- `test_basic_search_request` - 測試基本搜尋請求
- `test_advanced_search_request` - 測試進階搜尋請求
- `test_whitespace_stripping` - 測試空白字符處理
- `test_date_validation` - 測試日期驗證
- `test_time_validation` - 測試時間驗證
- `test_build_params` - 測試參數構建

#### TestSearchRequest
- `test_search_request_creation` - 測試創建搜尋請求
- `test_parse_meta` - 測試元資料解析
- `test_create_restaurant_request` - 測試餐廳請求創建

#### TestQueryRestaurants
- `test_query_restaurants_basic` - 測試基本查詢函數
- `test_query_restaurants_caching` - 測試快取功能
- `test_query_restaurants_no_cache_different_params` - 測試不同參數不使用快取

### 功能測試

#### HTTP 請求測試
- `test_do_sync` - 測試同步搜尋
- `test_do_async` - 測試異步搜尋
- `test_do_sync_http_error` - 測試 HTTP 錯誤處理
- `test_do_async_http_error` - 測試異步 HTTP 錯誤處理

#### HTML 解析測試
- `test_parse_restaurants` - 測試餐廳資訊解析
- `test_parse_restaurants_empty` - 測試空結果解析
- `test_parse_restaurants_malformed` - 測試格式錯誤的 HTML

#### 多頁搜尋測試
- `test_do_sync_multiple_pages` - 測試多頁同步搜尋
- `test_do_async_multiple_pages` - 測試多頁異步搜尋

### 整合測試

#### TestIntegration
- `test_basic_search_integration` - 基本搜尋整合測試
- `test_advanced_search_integration` - 進階搜尋整合測試
- `test_multi_page_search_integration` - 多頁搜尋整合測試
- `test_async_search_integration` - 異步搜尋整合測試
- `test_error_handling_integration` - 錯誤處理整合測試
- `test_no_results_integration` - 無結果整合測試

### CLI 測試

#### TestCLIHelpers
- `test_format_date_today` - 測試今天日期格式化
- `test_format_date_tomorrow` - 測試明天日期格式化
- `test_format_date_specific` - 測試特定日期格式化

#### TestCLISearch
- `test_search_restaurants_success` - 測試成功搜尋
- `test_search_restaurants_no_results` - 測試無結果搜尋
- `test_search_restaurants_error` - 測試錯誤搜尋
- `test_search_restaurants_with_all_params` - 測試所有參數搜尋
- `test_invalid_price_range` - 測試無效價格範圍
- `test_invalid_sort_type` - 測試無效排序類型

#### TestCLIArguments
- `test_basic_args` - 測試基本命令列參數
- `test_full_args` - 測試完整命令列參數

## Mock 策略

### HTTP Mock
- 使用 `httpx.get` 和 `httpx.AsyncClient` 的 mock
- 模擬 HTTP 回應和錯誤

### HTML Mock
- 提供真實的 HTML 結構用於解析測試
- 包含各種邊界情況和錯誤情況

### 異步 Mock
- 使用 `AsyncMock` 正確模擬異步操作
- 確保 `__aenter__` 和 `__aexit__` 的正確行為

## 測試覆蓋率

目前測試覆蓋率：**94%**

### 覆蓋率分析
- `src/tabelog/__init__.py`: 100%
- `src/tabelog/restaurant.py`: 94%
- `src/tabelog/search.py`: 94%

未覆蓋的行主要是：
- 錯誤處理中的特殊情況
- 某些邊界條件
- 防禦性程式碼

## 最佳實踐

1. **分離關注點** - 每個測試檔案專注於特定功能
2. **使用 Fixtures** - 共享 mock 資料和設定
3. **完整的錯誤測試** - 測試所有錯誤情況
4. **異步測試** - 正確測試異步操作
5. **真實資料** - 使用真實的 HTML 結構進行測試
6. **快取測試** - 驗證快取行為
7. **整合測試** - 測試完整的工作流程
