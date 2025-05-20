import os
import json
import logging
import redis
from flask import request, jsonify
from datetime import timedelta
from elasticsearch import Elasticsearch

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Redis Configuration ===
REDIS_HOST = "172.22.34.220"
REDIS_PORT = 6379
REDIS_DB = 0
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# === Constants ===
INDEX_NAME = "transportation_hospitalisation_injuries"
SCROLL_TIMEOUT = "2m"
AGE_FIELDS = [
    "age_0_7", "age_8_16", "age_17_25", "age_26_39",
    "age_40_64", "age_65_74", "age_75_plus"
]

def main():
    req = request
    gender = req.headers.get('X-Fission-Params-Gender')
    year = req.headers.get('X-Fission-Params-Year')  # Optional

    if not gender:
        return jsonify({'Status': 400, 'Message': 'Gender is required'}), 400

    cache_key = f"injuries:{gender}:{year or 'all'}"
    cached = redis_client.get(cache_key)
    if cached:
        return jsonify({'Status': 200, 'Data': json.loads(cached)})

    try:
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic:9200"],
            basic_auth=("elastic", "elastic"),
            verify_certs=False
        )

        must_clauses = [
            {"match": {"Gender.keyword": gender}}
        ]

        if year:
            try:
                must_clauses.append({"match": {"Year": int(year)}})
            except ValueError:
                return jsonify({'Status': 400, 'Message': 'Year must be an integer'}), 400

        search_body = {
            "_source": ["Gender", "Year", "Category", "total"] + AGE_FIELDS,
            "query": {
                "bool": {
                    "must": must_clauses
                }
            },
            "sort": [{"Year": "asc"}]
        }

        response = es.search(index=INDEX_NAME, body=search_body, scroll=SCROLL_TIMEOUT)
        hits = response.get("hits", {}).get("hits", [])
        scroll_id = response.get("_scroll_id")
        results = []

        while hits:
            for hit in hits:
                src = hit["_source"]
                entry = {
                    "Year": src.get("Year"),
                    "Gender": src.get("Gender"),
                    "Category": src.get("Category"),
                    "total": src.get("total")
                }
                for field in AGE_FIELDS:
                    entry[field] = src.get(field)
                results.append(entry)

            response = es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
            hits = response.get("hits", {}).get("hits", [])

        es.clear_scroll(scroll_id=scroll_id)
        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(results))
        return jsonify({'Status': 200, 'Data': results})

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({'Status': 500, 'Message': str(e)}), 500
