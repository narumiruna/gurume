# Map search (experimental)

`gurume map-search` and MCP tool `tabelog_search_map_restaurants` use Tabelog's undocumented `GET /xml/rstmap` endpoint. They are separate from the existing area/ranking search and never run automatically after an HTTP 403.

## CLI

```bash
uv run gurume map-search \
  --min-lat 34.36048477324305 --max-lat 35.15027330463616 \
  --min-lon 135.85490885032183 --max-lon 137.25566568625933 \
  --cuisine 焼き鳥 --page 1 --limit 20 --output json
```

These example bounds cover a rectangle around northern/central Mie and include parts of neighboring prefectures. They are not Mie's administrative boundary.

Required options:

- `--min-lat`, `--max-lat`: southern/northern latitude, finite numbers between -90 and 90.
- `--min-lon`, `--max-lon`: western/eastern longitude, finite numbers between -180 and 180.
- Each minimum must be strictly less than its maximum. Antimeridian-crossing rectangles are not supported.
- Python and MCP callers must pass numeric bounds, not Boolean values. Integer coordinates are accepted.

Optional options:

- `--cuisine`, `-c`: only `焼き鳥` is currently verified and supported; default `焼き鳥`.
- `--page`: 1-based upstream page, default 1.
- `--limit`, `-n`: 1–20 displayed results from that page, default 20.
- `--output`, `-o`: `table`, `simple`, `json`, `json-envelope`, or `json-list`.

Sort is fixed to the upstream rating order. Each invocation fetches one page, with an upstream page size of 20, regardless of `limit`. There are no keyword, named-area, geocoding, reservation, or TUI options for this workflow.

## MCP

Call `tabelog_search_map_restaurants` with:

```json
{
  "min_lat": 34.36048477324305,
  "max_lat": 35.15027330463616,
  "min_lon": 135.85490885032183,
  "max_lon": 137.25566568625933,
  "cuisine": "焼き鳥",
  "page": 1,
  "limit": 20
}
```

MCP `page` and `limit` must be JSON integers. Boolean values, floats, and numeric strings are rejected before a request. Direct Python calls with a non-string `cuisine` return a non-retryable parameter error.

The MCP response and CLI `--output json` / `json-envelope` share the same schema:

- `status`: `success`, `no_results`, or `error`.
- `source`: `tabelog_map_xml`; `scope`: `geographic_rectangle`.
- `items`: restaurant names, URLs, scores, review counts, genres, IDs, coordinates, prefecture codes, station text, closed days, and raw `price_range1` / `price_range2` fields.
- `meta`: upstream rectangle total, current page, fixed page size, received/skipped marker counts, previous/next flags, and source URL/parameters.
- `applied_filters`: verified bounds, cuisine, page, and fixed ranking sort; omitted (`null`) on errors.
- `returned_count`, `limit`, `has_more`, `warnings`, and a structured `error` when applicable.

`json-list` returns only the map items. Diagnostics and warnings go to stderr for all JSON formats. The CLI exits 1 on a request/validation failure and 0 on a successful or empty result. Typer rejects invalid option ranges before running the command. For direct Python tool calls with an invalid `limit`, the error envelope uses `limit=20` rather than storing the rejected value in its typed field.

## Interpretation and limits

- Rectangle results may cross prefecture boundaries. Do not call these prefecture or national rankings, or infer an exact prefecture total from the map total.
- `has_next_page` is computed as `page * 20 < total_count`; optional upstream navigation labels are ignored. `has_prev_page` indicates a preceding page index (`page > 1`), not a guarantee of results there for an out-of-range request.
- `has_more` is true for a computed next page or local output truncation. If `limit < 20`, first re-fetch the same page with `limit=20` to see omitted items; increasing `page` skips them.
- The default table shows raw prefecture codes and coordinates instead of an unavailable named area; codes do not establish prefecture ranking completeness.
- Malformed, duplicate, outside-rectangle, or cuisine-mismatched markers are skipped with warnings, without changing the upstream total. Rectangle edges are inclusive. Each valid marker must include the verified `焼き鳥` genre label; missing labels and unverified aliases are not accepted. If every received marker is invalid, the request fails rather than reporting no results.
- Before marker validation or local truncation, raw marker count must equal `min(20, max(0, total_count - (page - 1) * 20))`. Partial pages are upstream failures, not incomplete successful results. Empty pages at or beyond the total are legitimate `no_results` responses and retain the upstream total.
- Restaurant IDs and numeric URL segments must use ASCII digits; noncanonical Unicode-digit markers are skipped rather than exposed as restaurant links.
- `price_range1` / `price_range2` retain upstream budget text; empty/dash placeholders become `null`. Meal-period meaning is unverified, so `lunch_price` and `dinner_price` remain `null`.
- Optional data remains `null` when missing. An upstream zero overall score is treated as no rating. Review count zero is preserved.
- Invalid/challenge XML is an upstream failure, not an empty search. HTTP 4xx errors are marked non-retryable under the existing retry policy; HTTP 5xx, connection failures, and timeouts are retryable in the error metadata. No automatic retries, cookie transfer, or challenge solving are performed.
- Access and schema stability are not guaranteed. Respect applicable site usage restrictions and use only permitted access.

Existing `gurume search`, detail tools, cuisine lists, and TUI behavior are unchanged. `list-cuisines` describes the existing search, not the experimental map command's limited cuisine support.
