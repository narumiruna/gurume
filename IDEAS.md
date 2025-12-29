# Feature Ideas & Development Notes

This document tracks potential features, improvements, and implementation ideas for tabelog.

## 🎯 Planned Features

### High Priority

- [x] **MCP Server Integration** ✅ (Completed 2025-12-29)
  - Expose Tabelog search functionality as an MCP (Model Context Protocol) server
  - **Key features**:
    - Tool: `search_restaurants` - Search restaurants by area, keyword, cuisine type
    - Tool: `list_cuisines` - Get all supported cuisine types (for autocomplete/suggestions)
    - Tool: `get_area_suggestions` - Get area/station suggestions based on user query
    - Tool: `get_keyword_suggestions` - 🆕 Get keyword/cuisine/restaurant name suggestions
    - Input validation and error handling
    - Structured output in MCP-compatible format
  - **Design principles**:
    - ❌ **No AI parsing required**: Avoid using `parse_user_input()` to eliminate API key dependency
    - ✅ **Simple parameters**: area, keyword, cuisine (direct input, no LLM parsing)
    - ✅ **Zero configuration**: Works out-of-the-box without API keys
    - ✅ **Client-side parsing**: Let Claude/AI clients handle natural language, MCP server only handles structured queries
  - **Implementation**:
    - New file: `src/tabelog/server.py` (MCP server entry point)
    - Use existing `SearchRequest` for backend logic
    - Return results in Claude-friendly format (structured JSON)
    - Entry point: `tabelog` command (already defined in pyproject.toml)
  - **Example MCP tools**:
    ```python
    # Tool 1: search_restaurants
    @server.tool()
    async def search_restaurants(
        area: str | None = None,
        keyword: str | None = None,
        cuisine: str | None = None,
        sort: str = "ranking",
        limit: int = 20,
    ) -> list[dict]:
        """Search restaurants on Tabelog"""
        # Use SearchRequest directly, no LLM parsing
        ...

    # Tool 2: list_cuisines
    @server.tool()
    async def list_cuisines() -> list[dict]:
        """Get all supported cuisine types for autocomplete/suggestions

        Returns all 45+ cuisine types with their genre codes.
        Client can use this for autocomplete or let user select from list.

        Example return:
        [
          {"name": "すき焼き", "code": "RC0107"},
          {"name": "寿司", "code": "RC0201"},
          {"name": "ラーメン", "code": "RC0501"},
          ...
        ]
        """
        cuisines = get_all_genres()
        return [
            {"name": cuisine, "code": get_genre_code(cuisine)}
            for cuisine in cuisines
        ]

    # Tool 3: get_area_suggestions
    @server.tool()
    async def get_area_suggestions(query: str) -> list[dict]:
        """Get area/station suggestions based on user query

        Uses Tabelog's internal suggest API to provide relevant area/station options.

        Args:
            query: User's area search query (e.g., "東京", "渋谷")

        Returns:
            List of suggestions with display text and codes
        """
        return await get_area_suggestions_async(query)

    # Tool 4: get_keyword_suggestions (NEW!)
    @server.tool()
    async def get_keyword_suggestions(query: str) -> list[dict]:
        """Get keyword/cuisine/restaurant name suggestions

        Uses Tabelog's internal suggest API (same endpoint as area suggestions).
        Returns suggestions for:
        - Cuisine types (Genre2): すき焼き, 寿司, etc.
        - Restaurant names (Restaurant): 和田金, etc.
        - Keyword combinations (Genre2 DetailCondition): すき焼き ランチ, etc.

        Args:
            query: User's keyword search query (e.g., "すき", "寿司")

        Returns:
            List of suggestions with name and datatype
            Example: [
              {"name": "すき焼き", "datatype": "Genre2"},
              {"name": "すき焼き ランチ", "datatype": "Genre2 DetailCondition"},
              {"name": "すき焼きとやきとり 坊っちゃん", "datatype": "Restaurant"}
            ]
        """
        return await get_keyword_suggestions_async(query)
    ```
  - **Benefits**:
    - AI clients (Claude) can parse natural language themselves
    - No dependency on OpenAI API key
    - Simpler architecture (separation of concerns)
    - MCP server focuses on data retrieval, not NLP
    - **Cuisine suggestions**: Two complementary approaches:
      - `list_cuisines`: Static list of all 45+ cuisine types with codes (zero API calls)
      - `get_keyword_suggestions`: 🆕 Dynamic suggestions from Tabelog API (includes cuisines, restaurants, combinations)
    - **Keyword autocomplete**: Real-time suggestions as user types, including:
      - Cuisine types (すき焼き, 寿司)
      - Restaurant names (和田金)
      - Popular combinations (すき焼き ランチ)
  - **Usage example in Claude Desktop**:
    ```json
    {
      "mcpServers": {
        "tabelog": {
          "command": "uvx",
          "args": ["tabelog@latest"]
        }
      }
    }
    ```
  - **Workflow examples** (how Claude would use the tools):
    ```
    # Example 1: Using static cuisine list
    User: "Find sukiyaki restaurants in Mie"
    Claude:
    1. Calls list_cuisines() → Gets cuisine list, finds "すき焼き" (RC0107)
    2. Calls get_area_suggestions("三重") → Gets area options
    3. Calls search_restaurants(area="三重", cuisine="すき焼き", sort="ranking")
    4. Returns: 和田金, 金谷本店, etc. (すき焼き専門店 only)

    # Example 2: Using dynamic keyword suggestions (NEW!)
    User: "I want to eat suki... something in Tokyo"
    Claude:
    1. Calls get_keyword_suggestions("suki") → Gets ["すき焼き", "すき焼き ランチ", ...]
    2. Suggests options to user or picks most relevant: "すき焼き"
    3. Calls get_area_suggestions("Tokyo") → Gets ["東京都", "東京駅", ...]
    4. Calls search_restaurants(area="東京", keyword="すき焼き", sort="ranking")

    # Example 3: Direct search without suggestions
    User: "Show me ramen shops in Tokyo"
    Claude: Calls search_restaurants(area="東京", keyword="ラーメン", sort="ranking")

    # Example 4: Restaurant name search (NEW!)
    User: "Find 和田金 restaurant"
    Claude:
    1. Calls get_keyword_suggestions("和田金") → Finds restaurant name suggestions
    2. Calls search_restaurants(keyword="和田金")
    ```

### Medium Priority

### Low Priority / Future Considerations

- [x] **Caching and performance optimization** ✅ (2025-12-29)
  - ✅ Built-in response caching (cache.py module)
  - ✅ Configurable cache backend (MemoryCache and FileCache)
  - ✅ Integrated into RestaurantSearchRequest.search_sync() and .search() with 30-min TTL
  - ⏳ Rate limiting to avoid being blocked (future)
  - ⏳ Connection pooling for multiple requests (future)

- [x] **Retry and resilience mechanisms** ✅ (2025-12-29)
  - ✅ Auto-retry on transient failures (retry.py module)
  - ✅ Exponential backoff with jitter (tenacity library)
  - ✅ Max 3 attempts, 1-10 second wait range
  - ✅ Integrated into RestaurantSearchRequest.search_sync() and .search()
  - ⏳ Circuit breaker pattern (future)

- [ ] **Export and integration features**
  - Export to multiple formats: JSON, CSV, Excel, SQLite
  - Pandas DataFrame conversion
  - SQLAlchemy model integration
  - Google Sheets export

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
    - New module: `src/tabelog/tui.py` or separate `tabelog-tui` package
    - Async integration with `SearchRequest.do()` for non-blocking search
    - CLI entry point: `tabelog search-tui` or standalone `tabelog-tui` command
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
  - **New data models** (src/tabelog/detail.py or src/tabelog/models.py):
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
  - Configuration file support (.tabelogrc, environment variables)

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

## ✅ Completed

- **MCP (Model Context Protocol) Server** (2025-12-29)
  - ✓ Created `server.py` with full MCP server implementation
  - ✓ Implemented 4 tools:
    - `search_restaurants`: Search by area, keyword, cuisine with sorting and limits
    - `list_cuisines`: Get all 45+ cuisine types with genre codes
    - `get_area_suggestions`: Dynamic area/station suggestions from Tabelog API
    - `get_keyword_suggestions`: Dynamic keyword/cuisine/restaurant suggestions from Tabelog API
  - ✓ **Design achievements**:
    - ❌ No AI parsing dependency (no OpenAI API key required)
    - ✅ Zero configuration setup
    - ✅ Simple structured parameters
    - ✅ Client-side natural language handling
  - ✓ Uses MCP SDK's `@server.list_tools()` and `@server.call_tool()` decorators
  - ✓ stdio transport for communication with MCP clients
  - ✓ Entry point: `tabelog-mcp` command
  - ✓ All 4 tools tested and working
  - ✓ Documentation updated (README.md, CLAUDE.md, IDEAS.md)
  - ✓ Ready for use with Claude Desktop and other MCP clients

- **Command-line interface (CLI) with natural language query** (2025-12-29)
  - ✓ Created comprehensive CLI using Typer and Rich
  - ✓ Commands:
    - `tabelog search` - Search restaurants with multiple filters
    - `tabelog list-cuisines` - Display all supported cuisine types
    - `tabelog tui` - Launch interactive TUI
  - ✓ CLI options: -a/--area, -k/--keyword, -c/--cuisine, -q/--query, -s/--sort, -n/--limit, -o/--output
  - ✓ **Natural language query (-q/--query)**:
    - AI-powered parsing using `llm.parse_user_input()`
    - Multi-language support (Chinese, Japanese, English)
    - Auto-translation (e.g., "壽喜燒" → "すき焼き")
    - Example: `tabelog search -q "三重すきやき"`
  - ✓ **Auto-detection of cuisine types**: Automatically converts cuisine names to genre_code for precise filtering
  - ✓ **Three output formats**: table (Rich), json, simple text
  - ✓ **Graceful error handling**: Falls back when API key is missing
  - ✓ **Type-safe implementation**: Uses `Annotated[type, Option(...)]` pattern to satisfy ruff B008
  - ✓ Color-coded console output with Rich library
  - ✓ All 78 tests passing
  - ✓ All linting and type checks passing (ruff, ty)
  - ✓ Documentation updated (README.md, CLAUDE.md)
  - Entry point: `tabelog search` or `uv run tabelog search`

- **Area filtering and suggestion system** (2025-12-29)
  - ✓ Fixed critical bug: Tabelog's `/rst/rstsearch?sa=area` does NOT filter by area
  - ✓ Implemented path-based URL filtering (e.g., `/tokyo/rstLst/` instead of `/rst/rstsearch?sa=東京`)
  - ✓ Created `area_mapping.py` with mappings for all 47 prefectures
  - ✓ Added `get_area_slug()` function to convert area names to URL slugs
  - ✓ Updated `RestaurantSearchRequest.search()` to use area slug paths
  - ✓ Updated `SearchRequest.search()` to use area slug paths
  - ✓ Integrated Tabelog's internal suggest API (`/internal_api/suggest_form_words`)
  - ✓ Created `suggest.py` with `AreaSuggestion` dataclass and async/sync functions
  - ✓ Added `AreaSuggestModal` to TUI with F2 hotkey
  - ✓ Visual feedback for suggestion loading (🔍/✅/❌ icons)
  - ✓ Modal UI with OptionList for area/station selection
  - ✓ Prefecture-level filtering now works accurately (no more national results)
  - ✓ All code quality checks passing (ruff, ty)
  - ✓ Documentation updated (CLAUDE.md, README.md, TUI_USAGE.md)
  - Note: City/station-level filtering not supported (Tabelog limitation)

- **Terminal UI (TUI) for interactive restaurant search** (2025-12-28/29)
  - ✓ Created interactive terminal UI using Textual framework
  - ✓ Search panel with area and keyword input
  - ✓ RadioButton-based sorting selection (評分排名/評論數/新開幕/標準)
  - ✓ Two-column layout: Results table (left) + Detail panel (right)
  - ✓ Worker lifecycle management (auto-cancel previous search to prevent hanging)
  - ✓ Tabelog native API sorting (SortType passed to backend)
  - ✓ Results table (DataTable) displaying restaurant list
  - ✓ Detail panel showing selected restaurant information
  - ✓ **Advanced hotkeys**:
    - F2: Area suggestions (autocomplete with prefecture/station options)
    - F3: Cuisine type selection (45+ cuisine types in modal)
    - F4: AI natural language parsing (multi-language support)
    - q (quit), s (search), r (results), d (detail)
  - ✓ **Smart linking**: After AI parsing, auto-triggers area suggest (F2) or cuisine select (F3) based on parsed values
  - ✓ **Genre code filtering**: Automatically converts cuisine names to genre_code for precise filtering
  - ✓ Async search integration for non-blocking UI
  - ✓ CLI command: `tabelog tui`
  - ✓ Clean and responsive dark theme with simplified styling
  - ✓ Auto-height search panel to prevent clipping
  - ✓ All 78 tests passing
  - ✓ Type checking passing
  - ✓ Documentation updated (TUI_USAGE.md, README.md, CLAUDE.md)
  - Note: Advanced features like tab-based detail navigation, export, and filtering can be added later

- **Restaurant detail page scraping** (2025-12-28)
  - ✓ Created comprehensive scraping for restaurant detail pages
  - ✓ New dataclasses: `RestaurantDetail`, `Review`, `MenuItem`, `Course`
  - ✓ Support for scraping multiple tabs: 口コミ (reviews), メニュー (menu), コース (courses)
  - ✓ `RestaurantDetailRequest` class with sync/async support
  - ✓ Pagination support for reviews (configurable max_review_pages)
  - ✓ Selective fetching (can choose which tabs to scrape)
  - ✓ Robust HTML parsing with BeautifulSoup
  - ✓ Full test coverage (20 new tests)
  - ✓ All 78 tests passing
  - ✓ Type checking passing
  - Note: 写真 (photos) tab not implemented (excluded from requirements)

- **Core API improvements for better developer experience** (2025-12-28)
  - ✓ Created custom exception classes (TabelogError, ParseError, InvalidParameterError, NetworkError, RateLimitError)
  - ✓ Added type aliases (ReservationDate, ReservationTime, RestaurantURL)
  - ✓ Renamed methods: do()/do_sync() → search()/search_sync() (keeping old names for backward compatibility)
  - ✓ Improved parameter validation with better error messages
  - ✓ Added useful methods to SearchResponse:
    - filter() - filter restaurants by rating, review count, or custom condition
    - sort_by() - sort by any field
    - top() - get top N results
    - to_json() - export to JSON string
    - to_dict() - convert to dictionary
  - ✓ Updated all tests to use new API
  - ✓ Updated examples to use new API
  - ✓ All 58 tests passing
  - ✓ Code quality checks passing (ruff, type hints)

- **Package renamed from `tabelogmcp` to `tabelog`** (2025-12-28)
  - Updated package name in pyproject.toml
  - Renamed src/tabelogmcp/ → src/tabelog/
  - Updated all imports in tests and examples
  - Updated CLAUDE.md and IDEAS.md references
  - Created basic CLI entry point (tabelog.cli:main)
  - All tests passing ✓

- **HTML parsing improvements for Tabelog format changes** (2025-12-29)
  - ✓ Updated restaurant.py to handle new Tabelog HTML structure
  - ✓ Fixed area/genre parsing for format: `<div class="list-rst__area-genre"> [縣] 市區 / 類型</div>`
  - ✓ Removed test-specific hacks (auto-generated station/distance/genres)
  - ✓ Maintained backward compatibility with multiple HTML formats
  - ✓ Updated all test fixtures and assertions
  - ✓ All 78 tests passing
  - ✓ Code quality checks passing (ruff, ty)
  - ✓ Test coverage: 71% overall, 87-94% on core modules

---
**Note**: This is a living document. Feel free to add, modify, or reorganize ideas as the project evolves.
