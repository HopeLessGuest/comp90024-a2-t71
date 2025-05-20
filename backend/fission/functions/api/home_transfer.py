import os
import json
import logging
import redis
from flask import request, jsonify
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Redis Configuration ===
REDIS_HOST = "172.22.34.220"
REDIS_PORT = 6379
REDIS_DB = 0
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# === Constants ===
INDEX_NAME = "residential_transfer"
SCROLL_TIMEOUT = "2m"

def build_date_filter(start_year, start_month, end_year, end_month):
    start_year, end_year = int(start_year), int(end_year)
    start_month, end_month = int(start_month), int(end_month)
    return {
        "bool": {
            "should": [
                {
                    "bool": {
                        "must": [
                            {"range": {"Year": {"gte": start_year}}},
                            {"range": {"Month": {"gte": start_month}}}
                        ]
                    }
                },
                {
                    "bool": {
                        "must": [
                            {"range": {"Year": {"gt": start_year}}},
                            {"range": {"Year": {"lt": end_year}}}
                        ]
                    }
                },
                {
                    "bool": {
                        "must": [
                            {"range": {"Year": {"lte": end_year}}},
                            {"range": {"Month": {"lte": end_month}}}
                        ]
                    }
                }
            ],
            "minimum_should_match": 2
        }
    }

def main():
    req = request
    start_year = req.headers.get('X-Fission-Params-StartYear')
    start_month = req.headers.get('X-Fission-Params-StartMonth')
    end_year = req.headers.get('X-Fission-Params-EndYear')
    end_month = req.headers.get('X-Fission-Params-EndMonth')

    if not all([start_year, start_month, end_year, end_month]):
        return jsonify({'Status': 400, 'Message': 'Start/end year and month are required'}), 400

    cache_key = f"residential:{start_year}-{start_month}:{end_year}-{end_month}"
    cached = redis_client.get(cache_key)
    if cached:
        return jsonify({'Status': 200, 'Data': json.loads(cached)})

    try:
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic:9200"],
            basic_auth=("elastic", "elastic"),
            verify_certs=False
        )

        query_filter = build_date_filter(start_year, start_month, end_year, end_month)

        search_body = {
            "_source": [
                "Year", "Month", "Region",
                "Median_Att_Dwell", "Median_Est_House",
                "Num_Att_Dwell", "Num_Est_House"
            ],
            "query": query_filter,
            "sort": [{"Year": "asc"}, {"Month": "asc"}]
        }
        response = es.search(index=INDEX_NAME, body=search_body, scroll=SCROLL_TIMEOUT)
        hits = response.get("hits", {}).get("hits", [])
        scroll_id = response.get("_scroll_id")
        results = []

        while hits:
            for hit in hits:
                src = hit["_source"]
                results.append({
                    "Year": src.get("Year"),
                    "Month": src.get("Month"),
                    "Region": src.get("Region"),
                    "Median_Att_Dwell": src.get("Median_Att_Dwell"),
                    "Median_Est_House": src.get("Median_Est_House"),
                    "Num_Att_Dwell": src.get("Num_Att_Dwell"),
                    "Num_Est_House": src.get("Num_Est_House")
                })

            response = es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
            hits = response.get("hits", {}).get("hits", [])

        es.clear_scroll(scroll_id=scroll_id)

        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(results))
        return jsonify({'Status': 200, 'Data': results})

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({'Status': 500, 'Message': str(e)}), 500
