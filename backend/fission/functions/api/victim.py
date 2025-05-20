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
INDEX_NAME = "crime_victim_selected_year_state" 
SCROLL_TIMEOUT = "2m"

# All year keys from 1993 to 2023
YEAR_FIELDS = [str(year) for year in range(1993, 2024)]

def main():
    req = request
    state = req.headers.get('X-Fission-Params-State')
    method = req.headers.get('X-Fission-Params-Method')

    if not all([state, method]):
        return jsonify({'Status': 400, 'Message': 'Both state and method are required'}), 400

    cache_key = f"offence:{state}:{method}"
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
            "_source": ["Offence", "method", "state"] + YEAR_FIELDS,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"state.keyword": state}},
                        {"match": {"method.keyword": method}}
                    ]
                }
            },
            "sort": [{"Offence.keyword": "asc"}]
        }

        response = es.search(index=INDEX_NAME, body=search_body, scroll=SCROLL_TIMEOUT)
        hits = response.get("hits", {}).get("hits", [])
        scroll_id = response.get("_scroll_id")
        results = []

        while hits:
            for hit in hits:
                src = hit["_source"]
                entry = {"Offence": src.get("Offence")}
                for year in YEAR_FIELDS:
                    entry[year] = src.get(year)
                results.append(entry)

            response = es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
            hits = response.get("hits", {}).get("hits", [])

        es.clear_scroll(scroll_id=scroll_id)
        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(results))
        return jsonify({'Status': 200, 'Data': results})

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({'Status': 500, 'Message': str(e)}), 500
