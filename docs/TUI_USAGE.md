# Tabelog TUI - User Guide

## Launch the TUI

Use one of the following commands to start the interactive TUI:

```bash
# With uv
uv run gurume tui

# Or directly with Python
python -m gurume.tui
```

## Interface Overview

The TUI is divided into four main areas:

### 1. Header

- Displays the application name and current status

### 2. Search Panel

**First row - Search inputs**

- **Area input**: Enter the area you want to search (for example: Tokyo, Osaka)
  - Tip: after entering an area name, press `F2` to view suggestion options
  - Supports automatic suggestions for prefectures, stations, and areas
- **Keyword input**: Enter a search keyword (for example: `寿司`, `ラーメン`)
  - Tip: press `F3` to open intelligent keyword suggestions (`New!`)
    - When the keyword is empty: shows the full list of 45+ cuisine categories
    - When the keyword has content: calls the API and shows dynamic suggestions such as cuisine types, restaurant names, and combined keywords
  - Tip: enter natural language and press `F4` to use AI parsing
  - Automatically detects cuisine names and converts them into precise filters

**Second row - Sort options**

- **Sort radio buttons**: select a sort option directly with arrow keys or the mouse
  - Rating ranking (default)
  - Review count
  - New openings
  - Standard

**Third row**

- **Search button**: click it or press `Enter` in an input box to run a search

### 3. Two-Column Layout

**Left side - Results Table**

- Displays the list of restaurant search results
- Columns include:
  - Restaurant name
  - Rating
  - Review count
  - Area
  - Genre

**Right side - Detail Panel**

- Displays detailed information for the selected restaurant
- Includes:
  - Restaurant name
  - Rating and review count
  - Save count
  - Area and station information
  - Cuisine genre
  - Lunch and dinner price ranges
  - Restaurant URL

### 4. Footer

- Displays the available keyboard shortcuts

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `q` | Quit the application |
| `s` | Focus the search input |
| `r` | Focus the results list |
| `d` | Focus the detail panel |
| `F2` | Show area suggestions (requires an area query first) |
| `F3` | Intelligent keyword suggestions (empty keyword: cuisine list; non-empty keyword: dynamic API suggestions) (`New!`) |
| `F4` | Parse natural language input with AI (requires natural language input first) |
| `↑` / `↓` | Move up or down in the results list or suggestion list |
| `Tab` | Switch between components |
| `Enter` | Run search in an input box / confirm a suggestion |
| `Esc` | Close the area suggestion or cuisine suggestion popup |

## Typical Workflow

### Basic flow

1. Start the TUI with `uv run gurume tui`
2. Enter an area in the Area input box, for example `東京`
3. Press `Tab` to move to the Keyword input box and enter a keyword, for example `寿司`
4. Press `Tab` to move to the sort options and choose a sort mode with the arrow keys. The default is Rating ranking.
5. Click the Search button or press `Enter` in an input box to run the search
6. Wait for the search to complete. Results will appear in the left-hand results list
7. Use `↑` / `↓` or click an item to select a restaurant
8. Detailed information is shown automatically in the right-hand detail panel
9. You can update the search conditions and search again at any time. The previous search is cancelled automatically
10. Press `q` to quit

### Using area suggestions (recommended)

1. Start the TUI with `uv run gurume tui`
2. Enter an area keyword in the Area input box, for example `東京` or `伊勢`
3. Press `F2` to open the area suggestion popup
4. Use `↑` / `↓` to choose a suggested area or station
5. Press `Enter` to confirm, or press `Esc` to cancel
6. The selected area is filled into the input box automatically
7. Continue entering keywords and run the search

**Why use area suggestions?**

- Ensures the area name is valid and reduces failed searches
- Automatically provides prefecture, major station, and area options
- Supports area filtering so the results stay in the selected region instead of falling back to nationwide results

### Using intelligent keyword suggestions (recommended, `New!`)

The `F3` key supports two modes and switches automatically based on the keyword input content.

**Mode 1: Empty keyword -> full cuisine category list**

1. Start the TUI with `uv run gurume tui`
2. Make sure the Keyword input box is empty
3. Press `F3` to open the cuisine category selector popup
4. Use `↑` / `↓` to browse 45+ cuisine types
5. Press `Enter` to confirm, or press `Esc` to cancel
6. The selected cuisine name is filled into the Keyword input box automatically
7. The system uses the cuisine category code for precise filtering

**Mode 2: Keyword has content -> dynamic API suggestions (`New!`)**

1. Enter a partial keyword in the Keyword input box, for example `すき`
2. Press `F3` to call the Tabelog API and fetch suggestions
3. The system shows related suggestions, including:
   - Cuisine types, for example `すき焼き`, `寿司`
   - Restaurant names, for example `和田金`
   - Combined keywords, for example `すき焼き ランチ`
4. Use `↑` / `↓` to select a suggestion
5. Press `Enter` to confirm
6. The selected content is filled into the Keyword input box automatically

**Why use intelligent keyword suggestions?**

- **Precise filtering**: only shows restaurants that match the selected cuisine type, such as dedicated `すき焼き` restaurants
- **Discovery**: browse all 45+ cuisine types when the keyword box is empty
- **Dynamic suggestions**: get real-time suggestions while typing, including cuisines, restaurants, and combinations
- **Fewer typos**: choosing from a list keeps names accurate
- **Automatic conversion**: the system converts cuisine names into Tabelog cuisine codes automatically, for example `すき焼き` -> `RC0107`

**Direct cuisine input also works**

- Enter a cuisine name directly in the Keyword input box, for example `すき焼き`, `寿司`, or `ラーメン`
- The system detects it automatically and converts it into a precise filter
- Auto-detection supports all 45+ cuisine categories

### Using AI natural language parsing

1. Start the TUI with `uv run gurume tui`
2. Enter natural language in the Keyword input box, for example `我想吃三重的壽喜燒`
3. Press `F4` to use AI parsing
4. The system parses the area and keyword automatically and fills the corresponding fields
5. **If an area value is present**: area suggestions are triggered automatically
6. **If a keyword value is present**: cuisine suggestions are triggered automatically
7. Confirm or adjust the fields, then run the search

**Benefits of AI parsing**

- Natural language input: describe what you want in your own words
- Automatic classification: AI separates the area and cuisine type for you
- Smart suggestions: related suggestion features are triggered automatically after parsing
- Faster search: fill multiple fields from a single input

## Example Searches

### Search for sushi in Tokyo (rating ranking)

- Area: `東京`
- Keyword: `寿司`
- Sort: `Rating ranking`

### Search for ramen in Osaka (review count)

- Area: `大阪`
- Keyword: `ラーメン`
- Sort: `Review count`

### Search for washoku in Kyoto (new openings)

- Area: `京都`
- Keyword: `和食`
- Sort: `New openings`

### Search for dedicated `すき焼き` restaurants in Mie (using cuisine categories)

- Method 1: use the `F3` selector
  1. Press `F3` to open the cuisine category selector
  2. Choose `すき焼き`
  3. Enter the area: `三重`
  4. Run the search
- Method 2: direct input
  1. Area: `三重`
  2. Keyword: `すき焼き` (the system detects it automatically and applies precise filtering)
  3. Run the search
- Method 3: AI parsing (fastest)
  1. Keyword: `三重的すき焼き`
  2. Press `F4` to use AI parsing
  3. The system fills the area and keyword automatically and triggers suggestion helpers
  4. Run the search
- Result: only dedicated `すき焼き` restaurants are shown, such as `和田金` and `牛銀本店`, instead of unrelated restaurant types

## Notes

- **Area filtering limitations**
  - Supported: all 47 prefectures
  - Not supported: exact city-, town-, village-, or station-level filtering
  - Recommendation: use area suggestions with `F2` and select a prefecture to ensure filtering works as expected
- Searches may take a few seconds, depending on network conditions
- Make sure you have a working internet connection
- Search results depend on Tabelog site availability
- A larger terminal window is recommended for the best experience. `80x24` is the suggested minimum
- Re-running a search cancels the previous one automatically to avoid concurrency issues
- All search results use Tabelog's native sorting, not client-side sorting

## Completed Features

**Core functionality**

- Basic search by area, keyword, and cuisine category
- Four sort modes: rating ranking, review count, new openings, and standard
- **Area suggestions (`F2`)**: intelligent area and station suggestions
- **Intelligent keyword suggestions (`F3`)** (`New!`)
  - Empty keyword -> full list of 45+ Japanese cuisine types
  - Non-empty keyword -> dynamic API suggestions for cuisines, restaurant names, and combined keywords
- **AI natural language parsing (`F4`)**: parse natural language input with AI
- **Automatic cuisine detection**: detect cuisine names and convert them into precise filters automatically
- **Area filtering**: accurate filtering for all 47 prefectures
- **Cuisine filtering**: precise filtering for dedicated restaurants using cuisine codes (`RC codes`)
- Two-column result display with list and detail panel
- Real-time result updates
- Keyboard navigation support

**User experience**

- Radio-button-style sort selection that is always visible
- Automatic cancellation of the previous search to avoid stuck concurrent requests
- **Popup-based area selector**: clear visual feedback with icons and loading states
- **Intelligent keyword suggestion popup** (`New!`)
  - Static cuisine list
  - Dynamic API suggestions for cuisines, restaurants, and combinations
- **Smart cuisine detection**: direct cuisine input automatically becomes a precise filter
- Clean dark theme
- Responsive layout

## Possible Future Additions

- Advanced filter options such as price range, reservation time, and party size
- Multi-page result browsing
- Review, menu, and course detail views
- Export support such as JSON or CSV
- Search history and favorites
- Custom keyboard shortcuts

## Reporting Issues

If you run into problems, please report them in GitHub Issues:
https://github.com/narumiruna/gurume/issues
