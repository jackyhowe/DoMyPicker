# Etsy Product Research Tool (etsy-picker)

A command-line product research tool for Etsy, built on the official Etsy API. Search by category, specific product, or shop; sort by popularity, reviews, rating, favorites, or an estimated browse/save score; and analyze listing titles, tags, and images to support practical product selection decisions. Outputs terminal tables or CSV files.

## Requirements



* Python 3.8+ (**zero third-party dependencies** — standard library only, no `pip install` needed)

* A free Etsy API key

## Getting an API key (about 3 minutes)



1. Go to [https://www.etsy.com/developers/register](https://www.etsy.com/developers/register) or [https://www.etsy.com/developers/](https://www.etsy.com/developers/), and sign in with your Etsy account.

2. Register an app (any Name, e.g. `etsy-picker`). After submitting, the page shows your API key (alphanumeric, \~20 characters).

3. Provide the key in one of three ways:

* Environment variable: `set ETSY_API_KEY=your-key` (PowerShell: `$env:ETSY_API_KEY="your-key"`)

* Command-line flag: `--api-key your-key`

* A file: `C:\Users\<your-username>\.etsy_picker\key` (containing the key on a single line)

> This tool uses public endpoints only (API key only, no OAuth flow).

## Usage



```
\# Search by keyword and sort (default: popularity score)

python etsy\_picker.py search --keywords "vintage ring" --sort hot --limit 30

\# Search within a category, sort by estimate score, export to CSV

python etsy\_picker.py search --keywords "jewelry" --taxonomy-id 6548 --sort estimate --csv out.csv

\# View a specific product (title/price/tags/image URLs/description)

python etsy\_picker.py listing --id 123456789

\# Analyze a shop's products (by ID or name)

python etsy\_picker.py shop --id 654321 --sort reviews --limit 50

python etsy\_picker.py shop --name "ShopNameHere" --sort rating

\# List/search the category tree to get a taxonomy-id

python etsy\_picker.py taxonomy --search jewelry

\# Keyword guidance: search products and get top title/tag keywords

python etsy\_picker.py analyze --keywords "gift for mom" --limit 40 --top 15
```

### Sort modes (--sort)



| Value           | Meaning              | Basis                                                                                                            |
| --------------- | -------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `hot` (default) | Popularity           | reviews x 2.5 + favorites x 0.5, **proxy metric**, not real sales                                                |
| `reviews`       | Most reviews         | listing-level review count; falls back to shop-level when unavailable on public endpoints                        |
| `rating`        | Best rated           | average rating (usually shop-level); unrated items sort last                                                     |
| `favorers`      | Most favorited       | num\_favorers descending                                                                                         |
| `estimate`      | Browse/save estimate | **heuristic score**: favorites x 1 + reviews x 3 + price-band bonus (\$5–50 range), for relative comparison only |

## Metrics, limitations, and honest disclosure

**Etsy does not publicly expose sales, view counts, or add-to-cart counts** — those are only visible in the seller dashboard. All "popularity / browse / add-to-cart" sorting in this tool is based on **proxy or estimated indicators** derived from public signals. They are useful for relative comparison and initial screening, but do not represent actual Etsy backend data.



* Reviews and ratings: public v3 endpoints usually do not return listing-level reviews; the tool automatically falls back to **shop-level** review\_count / rating and displays it as-is. Verify on the product page before making decisions.

* Images: the listing command returns image URLs for manual download/review; the tool does not scrape web pages.

* Rate limits: Etsy API has rate limits; the tool retries with backoff and throttles bulk shop lookups automatically.

* Compliance: this tool only uses the official API and public data. It does not scrape the Etsy website and does not touch seller dashboard data.

## File structure



```
etsy-picker/

├── etsy\_picker.py   # CLI entry point

├── etsy\_api.py      # API wrapper (urllib, retry with backoff, key config)

├── analysis.py      # sorting, scoring models, keyword/tag frequency analysis

├── report.py        # terminal tables + CSV export (formula-injection safe)

└── README.md
```