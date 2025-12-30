# Feature Ideas & Development Notes

This document tracks potential features, improvements, and implementation ideas for gurume.

## 🎯 Planned Features

### Post-MCP Refactor (2025-12)

**Status**: After refactoring MCP server to FastMCP (v0.0.2 → v0.1.0)
- ✅ Migrated from low-level Server API to FastMCP
- ✅ Added Pydantic Output Schemas
- ✅ Implemented Tool Annotations
- ✅ Comprehensive error handling
- ✅ Tool naming with `tabelog_` prefix

**Current Test Coverage**: 52% (MCP server: 0%, suggest.py: 24%)

#### 🔴 High Priority (Immediate)

- [x] **✅ VERIFIED: JavaScript Rendering Impact** (Completed 2025-12-30)
  - **Initial Discovery**: Tabelog appeared to use client-side JS rendering (see Technical Considerations)
  - **Verification Results**: 🎉 **100% Success Rate** (14/14 test cases passed)
  - **Test Results Summary**:
    - Total tests: 14 (covering area-only, cuisine-only, area+cuisine, area+keyword)
    - Successful: 14/14 (100%)
    - Total restaurants found: 287
    - Average duration: 1.51s per test
    - **札幌+ハンバーグ (previously suspected JS-rendered)**: ✅ PASS (20 restaurants found)**
  - **Conclusion**:
    - ✅ Current httpx + BeautifulSoup approach works perfectly
    - ✅ No Playwright integration needed for core functionality
    - ✅ Tabelog uses progressive enhancement (server-side HTML + JS enhancements)
    - ✅ All major cities, cuisines, and search combinations work reliably
  - **Files Created**:
    - `scripts/verify_js_rendering.py`: Comprehensive verification script
    - `verification_results.json`: Detailed test results with timestamps
  - **Recommendation**: No immediate action needed. Current implementation is solid.
  - **Status**: ✅ RESOLVED - httpx implementation confirmed working

- [ ] **MCP Server Testing** ⭐ Most Important
  - Write tests for all 4 tools (`tabelog_search_restaurants`, `tabelog_list_cuisines`, `tabelog_get_area_suggestions`, `tabelog_get_keyword_suggestions`)
  - Test parameter validation and error handling
  - Test Pydantic schema outputs
  - Mock HTTP requests to avoid real network calls
  - **Goal**: Increase coverage from 0% to 80%+
  - **Estimated time**: 1-2 hours
  - **Priority**: Critical - just refactored, need stability

- [ ] **Create CHANGELOG.md**
  - Document v0.0.2 → v0.1.0 changes (MCP refactor)
  - Follow Keep a Changelog format
  - Include BREAKING CHANGES section (tool name changes)
  - **Estimated time**: 15-30 minutes

- [ ] **Improve low-coverage modules**
  - `suggest.py`: 24% → 80%+ (test area/keyword suggestion APIs)
  - `genre_mapping.py`: 45% → 90%+ (test all 45+ cuisine mappings)
  - `area_mapping.py`: 67% → 90%+ (test all 47 prefecture mappings)
  - **Goal**: Overall coverage 52% → 65%+
  - **Estimated time**: 1-1.5 hours

#### 🟡 Medium Priority (Short-term)

- [ ] **Version Release Preparation**
  - Complete MCP server tests
  - Update CHANGELOG.md
  - Decide: v0.1.0 (major refactor) or v0.0.3 (minor update)
  - Create GitHub Release with release notes
  - Test PyPI publish workflow

- [ ] **Enhanced MCP Error Messages**
  - Add fuzzy matching for cuisine suggestions
  - Example: "Unknown cuisine 'すきやき'. Did you mean: すき焼き, 焼き鳥, 焼肉?"
  - Implement using `difflib.get_close_matches()` or Levenshtein distance
  - More specific error context and next steps

- [ ] **MCP Server Usage Examples**
  - Create `examples/mcp_examples.md` with common patterns
  - Add code examples for complex workflows
  - Document error handling patterns
  - Include Claude Desktop integration examples
  - Multi-step search workflows (area suggest → search → refine)

- [ ] **MCP Server Documentation**
  - Add detailed tool descriptions in README
  - Parameter validation rules and constraints
  - Output schema documentation
  - Common use cases and anti-patterns

#### 🟢 Low Priority (Long-term)

- [ ] **CLI/TUI Testing**
  - `cli.py`: 0% → 60%+ (use `typer.testing.CliRunner`)
  - `tui.py`: 0% → 40%+ (use Textual testing utilities)
  - Note: Lower priority as these are UI components

- [ ] **Complete detail.py TODOs**
  - Parse more basic info from restaurant main page
  - Currently has 2 TODO comments
  - Not critical, can defer

- [ ] **Implement Easy IDEAS.md Features**
  - Concurrent multi-page scraping (`asyncio.gather()`)
  - Restaurant comparison tool
  - Export to CSV/JSON formats
  - Response compression (gzip/brotli)

- [ ] **Playwright Integration** (if JS rendering confirmed widespread)
  - Add `SearchBackend.PLAYWRIGHT` option
  - Implement browser automation for JS-rendered pages
  - Add hybrid mode with automatic fallback
  - Browser lifecycle management (headless mode, cleanup)
  - Performance optimization (browser reuse, connection pooling)
  - Dependencies: `playwright`, browser binaries (~100MB)
  - Impact: Slower but more reliable scraping

### Future Considerations

- [ ] **Enhanced testing**
  - Record/replay HTTP interactions (VCR.py)
  - HTML fixtures for offline testing
  - Performance benchmarks
  - Integration tests with real Tabelog (run manually)

- [ ] **Documentation improvements**
  - API reference docs (Sphinx or MkDocs)
  - Jupyter notebook examples
  - Video tutorials
  - Migration guide for API v2.0

- [ ] **Advanced Tabelog features**
  - Area-based browsing (not just search)
  - Restaurant rankings (top 100, etc.)
  - Map/location-based search
  - User profile scraping (reviewer info)
  - Restaurant comparison tool

- [ ] **Multi-platform support**
  - Support other restaurant sites (Gurunavi, Retty, Hot Pepper Gourmet)
  - Unified interface across platforms
  - Cross-platform comparison

## 💡 Ideas & Brainstorming

### Performance
- **Concurrent multi-page scraping**: Use `asyncio.gather()` to fetch multiple pages simultaneously
  ```python
  # Current: sequential page fetching
  for page in range(1, max_pages + 1):
      results = await fetch_page(page)

  # Proposed: parallel fetching
  tasks = [fetch_page(p) for p in range(1, max_pages + 1)]
  all_results = await asyncio.gather(*tasks)
  ```
- **Connection pooling**: Reuse HTTP connections across requests (httpx already supports this)
- **Streaming responses**: For large result sets, yield results as they're parsed
- **Selective parsing**: Only parse needed fields to reduce CPU time
- **Response compression**: Enable gzip/brotli compression in HTTP headers

### User Experience
- **Terminal UI (TUI) Application**: Build an interactive terminal interface for restaurant search
  - **Framework**: `textual` - Modern Python TUI framework with rich widgets
  - **Key features**:
    - Search bar with area/keyword input
    - Filterable results table (sort by rating, review count, price)
    - Detail view panel showing full restaurant info
    - Navigation: arrow keys, vim-style (j/k), tab switching
    - Pagination for large result sets
    - Export selected restaurants to JSON/CSV
  - **UI Layout ideas**:
    - Split view: search filters (left) + results list (right)
    - Bottom panel: restaurant detail view on selection
    - Top bar: current search criteria, total results count
    - Status bar: keyboard shortcuts help
  - **Restaurant detail navigation**:
    - Press Enter on selected restaurant to open detail view
    - Tab-based navigation: 基本情報 / 口コミ / メニュー / コース / 写真
    - Keyboard shortcuts: 1-5 or Tab/Shift+Tab to switch tabs
    - Scrollable content for long reviews/menus
    - Press 'b' or Esc to go back to search results
  - **Technical approach**:
    - New module: `src/gurume/tui.py` or separate `gurume-tui` package
    - Async integration with `SearchRequest.do()` for non-blocking search
    - CLI entry point: `gurume search-tui` or standalone `gurume-tui` command
    - Configuration: save/load favorite search queries
  - **Dependencies to add**:
    - `textual` - TUI framework
    - Optional: `rich` for enhanced terminal rendering (textual already includes it)

### Architecture

- **API Design Improvements**: Current API can be more developer-friendly and Pythonic

  **Current issues**:
  - Method names `do()` / `do_sync()` are not intuitive
  - Too many parameters in dataclass constructors (14+ parameters)
  - No fluent/builder pattern for constructing queries
  - Missing convenience factory methods
  - `SearchResponse` lacks filtering/sorting utilities
  - No custom exception types for better error handling
  - `query_restaurants()` has 14 parameters (hard to remember, error-prone)

  **Proposed improvements**:

  1. **Better method naming**:
     ```python
     # Current
     request.do()         # unclear
     request.do_sync()    # unclear

     # Proposed
     request.search()     # or execute() / run()
     request.search_sync()  # or execute_sync() / run_sync()
     ```

  2. **Builder pattern for fluent API**:
     ```python
     # Current
     request = RestaurantSearchRequest(
         area="東京",
         keyword="寿司",
         price_range=PriceRange.DINNER_5000_6000,
         has_private_room=True,
         card_accepted=True,
     )

     # Proposed (fluent)
     request = (
         RestaurantSearch()
         .in_area("東京")
         .with_keyword("寿司")
         .price_range(PriceRange.DINNER_5000_6000)
         .require_private_room()
         .accepts_cards()
     )
     # or chainable
     results = await RestaurantSearch().in_area("東京").with_keyword("寿司").search()
     ```

  3. **Factory methods for common use cases**:
     ```python
     # Quick searches
     Restaurant.search_in(area="東京", keyword="寿司")
     Restaurant.near_station(station="渋谷", distance="500m")
     Restaurant.by_genre(genre="イタリアン", area="六本木")

     # Filters
     results.with_rating(min=4.0)
     results.with_price_under(5000)
     results.top(10)  # top 10 results
     ```

  4. **Better SearchResponse methods**:
     ```python
     # Current: manually filter
     high_rated = [r for r in response.restaurants if r.rating and r.rating >= 4.0]

     # Proposed
     response.filter(min_rating=4.0)
     response.filter(lambda r: r.review_count and r.review_count > 100)
     response.sort_by("rating", reverse=True)
     response.top(10)
     response.to_json()
     response.to_csv("results.csv")
     response.to_dataframe()  # pandas DataFrame if available
     ```

  5. **Custom exceptions**:
     ```python
     class TabelogError(Exception): pass
     class RateLimitError(TabelogError): pass
     class ParseError(TabelogError): pass
     class InvalidParameterError(TabelogError): pass
     ```

  6. **Type aliases for clarity**:
     ```python
     type ReservationDate = str  # YYYYMMDD
     type ReservationTime = str  # HHMM
     type RestaurantURL = str
     ```

  7. **Async context manager support**:
     ```python
     async with TabelogClient() as client:
         results = await client.search(area="東京", keyword="寿司")
     ```

  8. **Better parameter validation**:
     ```python
     # Validate ranges
     if party_size and not (1 <= party_size <= 100):
         raise InvalidParameterError("party_size must be between 1 and 100")

     # Validate page
     if page < 1:
         raise InvalidParameterError("page must be >= 1")
     ```

  9. **Simplified quick search function**:
     ```python
     # Current: 14 parameters
     query_restaurants(area=..., keyword=..., ...)

     # Proposed: accept **kwargs or use builder
     search(area="東京", keyword="寿司", min_rating=4.0)
     # or
     quick_search("東京 寿司", filters={"min_rating": 4.0})
     ```

  10. **Result pagination helpers**:
      ```python
      # Iterator for all pages
      async for restaurant in search.iter_all_pages():
          print(restaurant.name)

      # Or
      response.next_page()
      response.prev_page()
      ```

- **Restaurant detail page scraping**: Extend scraping capabilities beyond search results
  - **Current limitation**: Only scrapes restaurant list pages, not individual restaurant pages
  - **New features needed**:
    - Scrape restaurant detail URL (already in `Restaurant.url`)
    - Parse multiple tab pages on Tabelog:
      - 基本情報 (basic info): hours, holidays, seating, payment methods, etc.
      - 口コミ (reviews): user reviews, ratings, visit dates, detailed comments
      - メニュー (menu): dish names, prices, photos
      - コース (courses): set menus, prices, course details
      - 写真 (photos): restaurant/food photos with captions
  - **New data models** (src/gurume/detail.py or src/gurume/models.py):
    ```python
    @dataclass
    class Review:
        reviewer: str
        rating: float
        visit_date: str | None
        title: str
        content: str
        helpful_count: int
        photos: list[str]

    @dataclass
    class MenuItem:
        name: str
        price: str | None
        description: str | None
        photo_url: str | None
        category: str | None  # appetizer, main, dessert, etc.

    @dataclass
    class Course:
        name: str
        price: str
        description: str
        items: list[str]  # course items

    @dataclass
    class RestaurantDetail:
        restaurant: Restaurant  # basic info from search
        business_hours: dict[str, str]  # weekday -> hours
        holidays: str | None
        seating: int | None
        payment_methods: list[str]
        reviews: list[Review]
        menu_items: list[MenuItem]
        courses: list[Course]
    ```
  - **API design**:
    - `RestaurantDetailRequest(restaurant_url: str)` - fetch detail page
    - Methods: `fetch_reviews()`, `fetch_menu()`, `fetch_courses()`, `fetch_all()`
    - Support pagination for reviews (Tabelog has many pages of reviews)
  - **URL patterns** (examples):
    - Base: `https://tabelog.com/tokyo/A1234/A567890/12345678/`
    - Reviews: `https://tabelog.com/tokyo/A1234/A567890/12345678/dtlrvwlst/`
    - Menu: `https://tabelog.com/tokyo/A1234/A567890/12345678/dtlmenu/`
    - Courses: `https://tabelog.com/tokyo/A1234/A567890/12345678/course/`

## 📝 Implementation Notes

### Technical Considerations

- **✅ RESOLVED: Tabelog JavaScript Rendering Investigation** (2025-12-30):

  **Initial Discovery** (2025-12-30 AM):
  Through Playwright network log analysis, Tabelog appeared to use client-side JavaScript rendering for restaurant lists.

  **Initial Evidence**:
  - Playwright network logs showed no XHR requests for complete restaurant list data
  - Only small APIs like `reserve_date_status_list`, `index` were visible
  - JavaScript appeared to be rendering the DOM dynamically

  **Verification Testing** (2025-12-30 PM):
  Created comprehensive verification script (`scripts/verify_js_rendering.py`) to test real Tabelog pages.

  **Test Results**: 🎉 **100% Success Rate**
  ```
  Total Tests:       14/14 passed
  Success Rate:      100%
  Total Restaurants: 287 found
  Avg Duration:      1.51s per test

  Test Coverage:
  - Area Only:      2/2 (100%) - Tokyo, Osaka
  - Cuisine Only:   2/2 (100%) - Sukiyaki, Ramen
  - Area+Cuisine:   7/7 (100%) - Tokyo+Sukiyaki, Osaka+Ramen, etc.
  - Area+Keyword:   3/3 (100%) - Tokyo+Sushi, Osaka+Yakiniku, Sapporo+Hamburg

  Critical Test:
  - 札幌+ハンバーグ (initially suspected JS-rendered): ✅ PASS (20 restaurants)
  ```

  **Actual Architecture** (Verified):
  Tabelog uses **Progressive Enhancement**:
  1. Server-side HTML includes complete restaurant list data (`.list-rst` elements)
  2. JavaScript enhances the experience with dynamic features (infinite scroll, filters, animations)
  3. Core data is accessible via httpx + BeautifulSoup without JavaScript execution

  **Why Initial Analysis Was Misleading**:
  - Playwright network logs only show *additional* XHR requests, not the initial HTML content
  - The absence of XHR for restaurant data meant it was *already in the HTML*, not that it was missing
  - JavaScript is used for *enhancements*, not for initial data loading

  **Conclusion**:
  - ✅ Current httpx + BeautifulSoup implementation is **completely reliable**
  - ✅ No Playwright integration needed for core restaurant search functionality
  - ✅ All major cities, cuisines, and search patterns work correctly
  - ✅ Fast performance (1.5s avg) with low resource usage

  **Playwright Use Cases** (Optional, Future):
  While not needed for basic search, Playwright could still be useful for:
  - Infinite scroll pagination (loading 100+ results beyond first page)
  - JavaScript-only features (interactive filters, dynamic sorting)
  - Screenshot-based features (restaurant photo galleries)
  - Anti-bot protection if Tabelog adds it in the future

  **Status**: ✅ RESOLVED - No action needed. Current implementation confirmed working.

- **Tabelog Suggest API** (discovered 2025-12-29):
  - **Endpoint**: `https://tabelog.com/internal_api/suggest_form_words`
  - **Parameters**:
    - `sa=query` - Area suggestions (search area)
    - `sk=query` - Keyword suggestions (search keyword)
  - **Response format**: JSON array of suggestions
    ```json
    [
      {
        "datatype": "Genre2" | "Restaurant" | "Genre2 DetailCondition" | "Area2" | "AddressMaster" | "RailroadStation",
        "name": "suggestion text",
        "id": 123,
        "id_in_datatype": 456,
        "lat": null | number,
        "lng": null | number,
        "related_info": ""
      }
    ]
    ```
  - **datatype values**:
    - `Genre2`: Cuisine type (すき焼き, 寿司)
    - `Restaurant`: Restaurant name (和田金)
    - `Genre2 DetailCondition`: Cuisine + condition (すき焼き ランチ)
    - `Area2`: Area name (東京, 大阪)
    - `AddressMaster`: Address
    - `RailroadStation`: Station name (渋谷駅)
  - **Current implementation**: `suggest.py` only supports area suggestions (`sa` parameter)
  - **Future enhancement**: Add keyword suggestion support (`sk` parameter) for dynamic autocomplete

- **Restaurant detail scraping challenges**:
  - Different restaurants may have different tab availability (not all have menu/course pages)
  - Need robust error handling for missing/malformed data
  - Review pagination can be extensive (100+ pages for popular restaurants)
  - Consider rate limiting to avoid being blocked by Tabelog
  - CSS selectors may differ between main page and detail pages
  - Some content may be behind login walls or require JavaScript rendering
  - Photos may be lazy-loaded or in different formats
- **TUI performance**:
  - Async/await critical for non-blocking UI during scraping
  - Cache detail page data to avoid re-scraping on navigation
  - Implement loading spinners/progress indicators during fetch
  - Consider background pre-fetching for selected restaurants in list

- **Production readiness**:
  - Add logging with different levels (DEBUG, INFO, WARNING, ERROR)
  - Metrics and monitoring hooks (request count, response time, error rate)
  - Health check endpoint for MCP server
  - Graceful degradation when Tabelog is down or changes HTML structure
  - Configuration file support (.gurumerc, environment variables)

- **Developer experience**:
  - Type stubs for better IDE autocomplete
  - Docstrings on all public methods (Google style)
  - Usage examples in docstrings
  - Pre-commit hooks for code quality
  - GitHub Actions for CI/CD
  - Auto-publish to PyPI on tag

- **Security considerations**:
  - Sanitize user input to prevent injection attacks
  - Validate URLs before scraping
  - Don't log sensitive information (API keys if added)
  - Respect robots.txt (add parser)
  - Add User-Agent rotation to avoid detection
  - HTTPS only (no HTTP fallback)

### Research Needed
- **Best practices for Python API design**:
  - Study popular scraping libraries: `requests`, `httpx`, `scrapy`, `beautifulsoup4`
  - Study data query libraries: `sqlalchemy`, `peewee`, `django ORM` for builder patterns
  - Study async libraries: `asyncio`, `aiohttp` for async context managers
  - Python API design guidelines: PEP 8, Google Python Style Guide
  - Examples of fluent APIs in Python: `pandas`, `sqlalchemy`, `httpx`

- **Tabelog website structure**:
  - Explore detail page HTML structure for reviews, menus, courses
  - Identify all possible CSS selectors and their fallbacks
  - Test pagination limits (max pages per search)
  - Check for API endpoints (GraphQL, REST) if any
  - Analyze JavaScript rendering requirements
  - Document URL patterns for different page types

- **Anti-scraping measures**:
  - Study Tabelog's rate limiting policies
  - Test different User-Agent strings
  - Check robots.txt compliance
  - Research if login is required for certain data
  - Investigate CAPTCHA triggers
  - Test IP blocking thresholds

- **Competitive analysis**:
  - How do other Tabelog scrapers handle these issues?
  - What features do similar libraries offer?
  - Check PyPI for existing Tabelog packages
  - Study API design of: `yelp-fusion`, `google-places`, `tripadvisor-api`

---
**Note**: This is a living document. Feel free to add, modify, or reorganize ideas as the project evolves.
