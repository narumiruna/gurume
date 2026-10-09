# Tabelog JavaScript investigation

## Outcome

The current ranking failure occurs at Cloudflare's managed challenge, before Tabelog's normal page is available. Running Tabelog's application bundle alone would not resolve this failure. No access workaround was implemented.

## Observed responses

A static probe using `curl_cffi 0.16.3` with Safari returned:

- Homepage: HTTP 200, with normal HTML and application script references.
- Mie yakitori ranking: HTTP 403, `cf-mitigated: challenge`, and a `Just a moment...` page.

The ranking response contains `window._cf_chl_opt`, `cType: 'managed'`, and a dynamically inserted `/cdn-cgi/challenge-platform/h/g/orchestrate/chl_page/v1` script. Its no-script message says `Enable JavaScript and cookies to continue`. These identify a Cloudflare managed challenge, not a Tabelog application error. They do not establish which detection signal triggered it or whether interactive verification will be required.

## Application scripts

The homepage references a Webpack-style `globalThis.TabelogWP` bundle, jQuery 3.4.1, jquery-ujs, Sentry initialization, Google advertising/tagging, and Adobe analytics.

The downloaded `commons.js` bundle was approximately 2 MB. Two homepage bundles were approximately 304 bytes and 14 KB. Static inspection found these behaviors:

### Search suggestions and submission

- Area suggestions use GET `/internal_api/suggest_form_words` with `sa`.
- Keyword suggestions use the same endpoint with `sk` and optional area context, coordinates, and multi-suggestion metadata.
- The HTML search form submits GET `/rst/rstsearch/`.
- Before submission, JavaScript adds `area_datatype`, `area_id`, `key_datatype`, `key_id`, and `sa_input`.

These fields may improve search normalization and are worth investigating separately from access failures. Their effect on search accuracy has not been tested. Their absence does not explain the observed challenge on a direct mapped cuisine ranking URL.

### Additional requests

- `/contents/index` loads homepage user information and timeline content.
- `/contents/reserve_date_status_list` supplies reservation status for existing restaurant IDs.
- `/internal_api/show_full_review_comment` expands review comments.
- `/internal_api/rst_search` appears in a restaurant-link search modal. Its POST request sends `sw`, `page`, `pcd`, `LstPrf`, and `LstAre`, and consumes `response.html`. It is not verified as a public cuisine ranking API or a substitute for Gurume search.
- CSRF helpers read `meta[name=csrf-token]` and attach `X-CSRF-Token` to applicable requests. This is distinct from Cloudflare verification.

No `turnstile` or `cf_chl` strings were found in the inspected application bundles. This limited negative result does not prove their absence from other scripts or runtime behavior.

## Limits and next checks

Only accessible homepage bundles and the ranking challenge HTML were inspected. The actual ranking page, its script references, and browser network traffic were unavailable. Chrome DevTools previously failed with `Target closed`.

1. Restore the browser connection and verify normal access on the same network.
2. If access is permitted, inspect search submission and ranking network traffic.
3. Confirm whether ranking data is present in the document response or fetched separately; current evidence does not settle this.
4. Evaluate browser-backed retrieval only after a successful browser check and review of site usage restrictions.

Challenge tokens were not persisted in repository documentation. Downloaded material was kept in temporary files; no unknown scripts were executed.

## Sources

- Homepage: https://tabelog.com/
- Ranking: https://tabelog.com/mie/rstLst/yakitori/?SrtT=rt
- Shared bundle: https://tblg.k-img.com/javascripts/assets/pepper/restaurant-pc/commons.js
- Homepage bootstrap: https://tblg.k-img.com/javascripts/assets/pepper/restaurant-pc/rst/top.js
- Homepage features: https://tblg.k-img.com/javascripts/assets/pepper/restaurant-pc/rst/rst/top.js

The live homepage used versioned query strings for these assets. Asset URLs and behavior are upstream-controlled and may change.
