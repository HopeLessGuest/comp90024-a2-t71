# inflation_api  Overview

All endpoints use HTTP GET. Base URL: `https://<gateway-domain-or-IP>/inflation`

---

**Endpoint**: `/inflation/rba`  
Access CPI and inflation metrics from Australia's central bank. Optional date filters:  
`start=YYYY-MM-DD` (inclusive start date) and `end=YYYY-MM-DD` (inclusive end date). Leave both empty to get full historical data.

---

**Endpoint**: `/inflation/reddit_posts**  
Search Reddit posts about inflation by creation time. Optional filters:  
`start=YYYY-MM-DD` (earliest post date) and `end=YYYY-MM-DD` (latest post date).

---

**Endpoint**: `/inflation/reddit_comments**  
Find Reddit comments about inflation by creation time. Optional filters:  
`start=YYYY-MM-DD` (earliest comment date) and `end=YYYY-MM-DD` (latest comment date).

---

### Key Specifications  
Dates use midnight time (e.g. 2023-01-15 becomes 2023-01-15T00:00:00Z). Single parameter usage:  
- Only `start` returns data from that date to present  
- Only `end` returns data from earliest record to that date  
All date ranges include full data from boundary dates.

# inflation_harvester Overview

`fc.py` – Main script for scraping Reddit posts and their comments (Fission entry point). It searches for posts with inflation-related keywords, retrieves the corresponding comments, and indexes both posts and comments into Elasticsearch.

`rba.py` – Pre-processes Reserve Bank of Australia (RBA) CPI data and uploads the cleaned dataset to Elasticsearch.

`reddit_get_comments.py` – Utility module that provides comment-fetching helpers, used internally by `fc.py`.
