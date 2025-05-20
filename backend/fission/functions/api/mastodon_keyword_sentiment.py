import os
import json
import logging
import redis
from flask import request, jsonify
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
import re

# === NLP Prep ===
import nltk
nltk.download("stopwords")

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Redis Configuration ===
REDIS_HOST = "172.22.34.220"
REDIS_PORT = 6379
REDIS_DB = 0
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# === Constants ===
INDEX_NAME = "mastodon_cleaned"
SCROLL_TIMEOUT = "2m"

# === Australian Keyword Heuristics ===
AUSTRALIA_KEYWORDS = [
    "australia", "australian", "aussie",
    "melbourne", "sydney", "brisbane", "perth",
    "canberra", "adelaide", "hobart", "darwin",
    "nsw", "vic", "qld", "wa", "sa", "tas", "nt", "act"
]

def is_australian(doc):
    acct = (doc.get("account", {}).get("acct") or "").lower()
    note = (doc.get("account", {}).get("note") or "").lower()
    fields = doc.get("account", {}).get("fields") or []
    field_values = [f.get("value", "").lower() for f in fields if isinstance(f, dict)]
    tags_raw = doc.get("tags", [])
    tags = []
    for t in tags_raw:
        if isinstance(t, dict):
            tags.append(t.get("name", "").lower())
        elif isinstance(t, str):
            tags.append(t.lower())
    content = (doc.get("content") or "").lower()

    if any(domain in acct for domain in ['.au', 'aus.social', 'mastodon.au']):
        return True
    if any(k in note for k in AUSTRALIA_KEYWORDS):
        return True
    if any(k in content for k in AUSTRALIA_KEYWORDS):
        return True
    if any(k in tag for tag in tags for k in AUSTRALIA_KEYWORDS):
        return True
    if any(k in val for val in field_values for k in AUSTRALIA_KEYWORDS):
        return True
    return False

def main():
    req = request
    start_date = req.headers.get('X-Fission-Params-Startdate')
    end_date = req.headers.get('X-Fission-Params-Enddate')
    keywords_str = req.headers.get('X-Fission-Params-Keyword')

    if not all([start_date, end_date, keywords_str]):
        return jsonify({'Status': 400, 'Message': 'Start/end date and keyword(s) are required'}), 400

    keywords = [k.strip().lower() for k in keywords_str.split('_') if k.strip()]
    cache_key = f"mastodon:sentiment:{'-'.join(keywords)}:{start_date}:{end_date}"

    cached = redis_client.get(cache_key)
    if cached:
        return jsonify({'Status': 200, 'Data': json.loads(cached)})

    try:
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic:9200"],
            basic_auth=("elastic", "elastic"),
            verify_certs=False
        )
        logging.info("Elasticsearch client connected")

        # Construct keyword-based match query
        should_clauses = []
        for kw in keywords:
            should_clauses.append({"match_phrase": {"content": kw}})
            should_clauses.append({"match_phrase": {"tags.name": kw}})

        search_body = {
            "_source": [
                "createdAt",
                "content",
                "account.acct",
                "account.note",
                "account.fields",
                "tags",
                "sentiment"
            ],
            "query": {
                "bool": {
                    "must": {
                        "range": {
                            "createdAt": {
                                "gte": start_date,
                                "lte": end_date
                            }
                        }
                    },
                    "should": should_clauses,
                    "minimum_should_match": 1
                }
            },
            "sort": [{"createdAt": "asc"}]
        }

        response = es.search(index=INDEX_NAME, body=search_body, scroll=SCROLL_TIMEOUT)
        scroll_id = response.get("_scroll_id")
        hits = response.get("hits", {}).get("hits", [])

        total_sentiment = 0.0
        count = 0

        while hits:
            for hit in hits:
                doc = hit["_source"]
                if not is_australian(doc):
                    continue
                sentiment = doc.get("sentiment")
                if isinstance(sentiment, (int, float)):
                    total_sentiment += sentiment
                    count += 1

            response = es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
            hits = response.get("hits", {}).get("hits", [])

        es.clear_scroll(scroll_id=scroll_id)

        result = {
            "count": count,
            "sum_sentiment": total_sentiment,
            "avg_sentiment": total_sentiment / count if count > 0 else None
        }

        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(result))
        return jsonify({'Status': 200, 'Data': result})

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({'Status': 500, 'Message': str(e)}), 500
