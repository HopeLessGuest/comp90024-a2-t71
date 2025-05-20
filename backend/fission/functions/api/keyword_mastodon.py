import os
import json
import logging
import redis
import re
import nltk
from bs4 import BeautifulSoup
from flask import request, jsonify
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from collections import Counter
from typing import Optional

# === Initial Setup ===
nltk.download("punkt")
nltk.download("stopwords")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Redis Configuration ===
REDIS_HOST = "172.22.34.220"
REDIS_PORT = 6379
REDIS_DB = 0
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# === Constants ===
INDEX_NAME = "mastodon_cleaned"
SCROLL_TIMEOUT = "2m"

# === Stopwords and Filter Keywords ===
AUSTRALIA_KEYWORDS = [
    "australia", "australian", "aussie",
    "melbourne", "sydney", "brisbane", "perth",
    "canberra", "adelaide", "hobart", "darwin",
    "nsw", "vic", "qld", "wa", "sa", "tas", "nt", "act"
]

STOPWORDS = set(stopwords.words("english")) | {
    "oh", "well", "yeah", "yep", "uh", "um", "hmm", "also", "really", "like",
    "think", "know", "want", "see", "say", "said", "one", "get", "got", "go",
    "going", "would", "could", "even", "im", "dont", "cant", "didnt", "hes",
    "youre", "thats", "man", "woman", "someone", "thing", "things", "way", "bit",
    "actually", "make", "made", "put", "still", "much", "back", "right", "us",
    'de', 'la', 'der', 'que', 'en', 'el', 'es', 'die', 'das', 'na', 'e', 'might',
    'theres', 'heres', 'trying', 'every', 'many', 'take', 'since'
}

# === Helper Functions ===
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

def clean_and_tokenize(text):
    text = BeautifulSoup(text, 'html.parser').get_text()
    text = re.sub(r"[^\w\s]", "", text.lower())
    tokens = word_tokenize(text)
    return [t for t in tokens if t.isalpha() and t not in STOPWORDS]

def extract_keywords_from_results(results, top_k=100):
    all_tokens = []
    for doc in results:
        if is_australian(doc) and doc.get("content"):
            all_tokens.extend(clean_and_tokenize(doc["content"]))
    freq = Counter(all_tokens)
    return dict(freq.most_common(top_k))

# === Flask Handler ===
def main():
    logging.info('Elasticsearch API - Mastodon Keyword Cloud')

    req = request
    start_date: Optional[str] = req.headers.get('X-Fission-Params-Startdate')
    end_date: Optional[str] = req.headers.get('X-Fission-Params-Enddate')

    logging.info(f"Received Headers: Start Date: {start_date}, End Date: {end_date}")

    if not (start_date and end_date):
        logging.error("Missing start date or end date in headers.")
        return jsonify({'Status': 400, 'Message': 'Start date and end date are required.'}), 400

    start_datetime = f"{start_date}T00:00:00"
    end_datetime = f"{end_date}T00:00:00"
    cache_key = f"mastodon:keywords:{start_datetime}:{end_datetime}"

    cached_data = redis_client.get(cache_key)
    if cached_data:
        logging.info("Returning cached data from Redis")
        return jsonify({'Status': 200, 'Data': json.loads(cached_data)})

    try:
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic:9200"],
            basic_auth=("elastic", "elastic"),
            verify_certs=False
        )
        logging.info("Elasticsearch client connected")

        search_body = {
            "_source": [
                "createdAt",
                "content",
                "account.acct",
                "account.note",
                "account.fields",
                "tags"
            ],
            "query": {
                "range": {
                    "createdAt": {
                        "gte": start_datetime,
                        "lte": end_datetime
                    }
                }
            },
            "sort": [{"createdAt": "asc"}]
        }


        response = es.search(index=INDEX_NAME, body=search_body, scroll=SCROLL_TIMEOUT)
        hits = response.get("hits", {}).get("hits", [])
        scroll_id = response.get("_scroll_id")
        results = []

        while hits:
            for hit in hits:
                doc = hit["_source"]
                results.append(doc)

            response = es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
            hits = response.get("hits", {}).get("hits", [])

        es.clear_scroll(scroll_id=scroll_id)

        keywords = extract_keywords_from_results(results)

        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps({"keywords": keywords}))

        logging.info(f"Returned {len(keywords)} top keywords.")
        return jsonify({'Status': 200, 'Data': {"keywords": keywords}})

    except Exception as e:
        logging.error(f'Error at Elasticsearch API: {str(e)}')
        return jsonify({'Status': 500, 'Message': str(e)}), 500
