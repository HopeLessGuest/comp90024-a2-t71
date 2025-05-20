import os
import json
import logging
import redis
import re
import nltk
from bs4 import BeautifulSoup
from flask import request, jsonify
from datetime import timedelta
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
INDEX_NAME = "mastodon_posts"
SCROLL_TIMEOUT = "2m"
STOPWORDS = set(stopwords.words("english")) | {
    "oh", "well", "yeah", "yep", "uh", "um", "hmm", "also", "really", "like",
    "think", "know", "want", "see", "say", "said", "one", "get", "got", "go",
    "going", "would", "could", "even", "im", "dont", "cant", "didnt", "hes",
    "youre", "thats", "man", "woman", "someone", "thing", "things", "way", "bit",
    "actually", "make", "made", "put", "still", "much", "back", "right", "us",
    'de', 'la', 'der', 'que', 'en', 'el', 'es'
}

def clean_and_tokenize(text):
    text = BeautifulSoup(text, 'html.parser').get_text()
    text = re.sub(r"[^\w\s]", "", text.lower())
    tokens = word_tokenize(text)
    return [t for t in tokens if t.isalpha() and t not in STOPWORDS]

def extract_keywords(results, top_k=100):
    all_tokens = []
    for doc in results:
        content = doc.get("original_content")
        if content:
            all_tokens.extend(clean_and_tokenize(content))
    freq = Counter(all_tokens)
    return dict(freq.most_common(top_k))

# === Flask Handler ===
def main():
    logging.info('Keyword Extraction API - mastodon_posts')

    req = request
    start_date = req.headers.get('X-Fission-Params-Startdate')
    start_time = req.headers.get('X-Fission-Params-Starttime')
    end_date = req.headers.get('X-Fission-Params-Enddate')
    end_time = req.headers.get('X-Fission-Params-Endtime')

    if not all([start_date, start_time, end_date, end_time]):
        return jsonify({'Status': 400, 'Message': 'Start and end date/time headers required'}), 400

    start_datetime = f"{start_date}T{start_time}"
    end_datetime = f"{end_date}T{end_time}"
    cache_key = f"mastodon_posts:keywords:{start_datetime}:{end_datetime}"

    cached = redis_client.get(cache_key)
    if cached:
        return jsonify({'Status': 200, 'Data': json.loads(cached)})

    try:
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic:9200"],
            basic_auth=("elastic", "elastic"),
            verify_certs=False
        )

        search_body = {
            "_source": ["original_content", "created_at"],
            "query": {"match_all": {}},
            "sort": [{"created_at.keyword": "asc"}]
        }

        response = es.search(index=INDEX_NAME, body=search_body, scroll=SCROLL_TIMEOUT)
        hits = response.get("hits", {}).get("hits", [])
        scroll_id = response.get("_scroll_id")
        results = []

        while hits:
            for hit in hits:
                doc = hit["_source"]
                created_at = doc.get("created_at")
                if created_at and start_datetime <= created_at <= end_datetime:
                    results.append(doc)

            response = es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
            hits = response.get("hits", {}).get("hits", [])

        es.clear_scroll(scroll_id=scroll_id)

        keyword_freq = extract_keywords(results)

        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps({"keywords": keyword_freq}))
        return jsonify({'Status': 200, 'Data': {"keywords": keyword_freq}})

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({'Status': 500, 'Message': str(e)}), 500
