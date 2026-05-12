---
name: gurume-cli
description: Use the `gurume` CLI to search Japanese restaurants on Tabelog. Trigger this whenever the user wants to find, recommend, or research restaurants/eateries in Japan — by area (Tokyo, Osaka, Kyoto, 三重, etc.), by cuisine (ramen, sushi, yakiniku, izakaya...), or with a vague request like "where should I eat in Shibuya" or "any good unagi spots near Tokyo Station". Use this even when the user does not explicitly mention Tabelog or the `gurume` tool, as long as the intent is finding Japanese restaurants.
---

# gurume CLI

`gurume` is a CLI wrapper around Tabelog (Japan's largest restaurant review site). Use it instead of guessing restaurants from memory or scraping the web — its data is current and structured.

## When to use

Trigger this skill whenever the user wants to find restaurants in Japan. Typical signals:

- Mentions a Japanese place name (Tokyo, 大阪, Shibuya, 三重, 京都駅, ...)
- Mentions Japanese cuisines (ramen, sushi, unagi, yakiniku, izakaya, 寿司, ラーメン, ...)
- Asks for restaurant recommendations / "where to eat" in Japan
- Plans a trip to Japan and asks about food

Do **not** trigger for: non-Japan restaurants, recipes, food delivery apps, or general food trivia.

## Workflow

### 1. Resolve the cuisine (if any)

If the user mentions a specific cuisine, map it to one of Tabelog's supported cuisine names. The full list is in `references/cuisines.md` — read that file when you need the mapping. Cuisine names **must be passed in Japanese** (e.g. `ラーメン`, not `ramen`).

If the user's request doesn't fit the fixed list (e.g. "tonkotsu ramen", "omakase sushi"), drop `--cuisine` and put the extra detail into `--keyword` instead. Cuisine + keyword can be combined.

### 2. Resolve the area

Pass the area in Japanese where possible (`東京`, `大阪`, `渋谷`, `京都`, `三重`). Romaji sometimes works, but Japanese is more reliable. Use the most specific area the user gave you — `渋谷` returns better results than `東京` if the user said "Shibuya".

### 3. Run the search

Default invocation — always use JSON output so you can parse it cleanly:

```bash
gurume search --area <area> [--cuisine <jp-cuisine>] [--keyword <jp-keyword>] \
              --sort ranking --limit 10 --output json
```

Flag guidance:

- `--sort ranking` (default): good general "best of" results. Use `review-count` when the user wants popular/famous places, `new-open` for newly opened spots.
- `--limit`: 10 is plenty for a conversational reply. Bump to 20+ only if the user asks for a long list.
- `--output json`: always use this — `table` is decorative and harder to read programmatically.

### 4. Present results

After running, parse the JSON and summarize for the user. For each restaurant include:

- Name (keep the Japanese name; add a romaji/English hint only if it helps)
- Cuisine / area
- Rating and review count if present
- A one-line note (price range, station, what stands out)
- The Tabelog URL so they can click through

Then ask if they want to narrow down (different area, cheaper, dinner only, etc.).

## Examples

**User:** "Looking for good ramen in Tokyo, ideally tonkotsu."

```bash
gurume search --area 東京 --cuisine ラーメン --keyword 豚骨 --sort ranking --limit 10 --output json
```

**User:** "Any famous sushi places in Osaka?"

```bash
gurume search --area 大阪 --cuisine 寿司 --sort review-count --limit 10 --output json
```

**User:** "Where should I eat dinner near Kyoto Station?" (no specific cuisine)

```bash
gurume search --area 京都駅 --sort ranking --limit 10 --output json
```

**User:** "I want sukiyaki in Mie prefecture."

```bash
gurume search --area 三重 --cuisine すき焼き --sort ranking --limit 10 --output json
```

## Other commands (rarely needed)

- `gurume list-cuisines` — print the supported cuisine list. You usually don't need to run this because `references/cuisines.md` already has it cached; only re-run if the user suspects the list is outdated.
- `gurume tui` / `gurume mcp` — interactive TUI and MCP server. Don't invoke these from this skill; they're for the user to run themselves.

## Notes & gotchas

- Tabelog HTML is the upstream source, so results occasionally contain odd encoding or missing fields. Handle missing keys gracefully when summarizing.
- The CLI hits the network — if it fails, surface the error to the user rather than fabricating restaurants.
- Reply to the user in the same language they used (often Traditional Chinese, Japanese, or English).
