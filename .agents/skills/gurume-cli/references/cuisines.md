# Supported Tabelog Cuisines

Pass the **Japanese name** (left column) to `gurume search --cuisine`. The genre code is informational only — the CLI accepts the name.

If a user's request doesn't map cleanly to one of these (e.g. "tonkotsu ramen", "omakase", "kaiseki", "yakitori bar"), use the closest cuisine here and put the rest into `--keyword`, or drop `--cuisine` entirely.

| Japanese name (use this) | English hint        | Code   |
| ------------------------ | ------------------- | ------ |
| うどん                   | Udon                | RC0601 |
| うなぎ                   | Unagi (eel)         | RC0701 |
| しゃぶしゃぶ             | Shabu-shabu         | RC0106 |
| すき焼き                 | Sukiyaki            | RC0107 |
| そば                     | Soba                | RC0602 |
| とんかつ                 | Tonkatsu            | RC0302 |
| もつ鍋                   | Motsunabe (offal hotpot) | RC1602 |
| イタリアン               | Italian             | RC1101 |
| カフェ                   | Café                | RC1901 |
| カレー                   | Curry               | RC1801 |
| スイーツ                 | Sweets / desserts   | RC2101 |
| ステーキ                 | Steak               | RC1201 |
| ハンバーガー             | Hamburger           | RC1203 |
| ハンバーグ               | Hamburg steak       | RC1202 |
| パン                     | Bakery / bread      | RC2001 |
| フレンチ                 | French              | RC1001 |
| ホルモン                 | Hormone (offal BBQ) | RC1502 |
| ラーメン                 | Ramen               | RC0501 |
| 中華料理                 | Chinese             | RC1401 |
| 天ぷら                   | Tempura             | RC0301 |
| 寿司                     | Sushi               | RC0201 |
| 居酒屋                   | Izakaya             | RC1701 |
| 日本料理                 | Japanese (kaiseki / washoku) | RC0801 |
| 洋食                     | Yōshoku (Western-style Japanese) | RC1301 |
| 海鮮                     | Seafood             | RC0901 |
| 焼き鳥                   | Yakitori            | RC0401 |
| 焼肉                     | Yakiniku (Japanese BBQ) | RC1501 |
| 鍋                       | Hotpot              | RC1601 |
| 餃子                     | Gyoza               | RC1402 |

## Common mapping hints

- "yakitori bar" → `焼き鳥`
- "BBQ in Japan" / "Korean BBQ in Tokyo" → `焼肉`
- "kaiseki" / "washoku" / "traditional Japanese" → `日本料理`
- "omakase sushi" → `寿司` + `--keyword おまかせ`
- "tonkotsu ramen" → `ラーメン` + `--keyword 豚骨`
- "izakaya" / "drinking spot with food" → `居酒屋`
- "dessert café" / "matcha sweets" → `スイーツ` or `カフェ`
