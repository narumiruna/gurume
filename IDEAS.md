# Feature Ideas & Development Notes

This document tracks potential features, improvements, and implementation ideas for gurume.

## 🎯 Planned Features

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
