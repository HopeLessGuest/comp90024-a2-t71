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
INDEX_NAME = "crime_offender_principle_year_sex_age"
SCROLL_TIMEOUT = "2m"

# === Fields to include in output ===
YEAR_FIELDS = [
    "2008–09", "2009–10", "2010–11", "2011–12", "2012–13",
    "2013–14", "2014–15", "2015–16", "2016–17", "2017–18",
    "2018–19", "2019–20", "2020–21", "2021–22", "2022–23", "2023–24"
]

def main():
    req = request
    gender = req.headers.get('X-Fission-Params-Gender')
    age = req.headers.get('X-Fission-Params-Age')
    method = req.headers.get('X-Fission-Params-Method')

    if not all([gender, age, method]):
        return jsonify({'Status': 400, 'Message': 'gender, age, and method are required'}), 400

    cache_key = f"crime:{gender}:{age}:{method}"
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
            "_source": ["Principal offence"] + YEAR_FIELDS,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"gender.keyword": gender}},
                        {"match": {"Age": age}},
                        {"match": {"method.keyword": method}}
                    ]
                }
            }
        }

        response = es.search(index=INDEX_NAME, body=search_body, scroll=SCROLL_TIMEOUT)
        hits = response.get("hits", {}).get("hits", [])
        scroll_id = response.get("_scroll_id")
        results = []

        while hits:
            for hit in hits:
                src = hit["_source"]
                entry = {
                    "Principal offence": src.get("Principal offence")
                }
                for year_field in YEAR_FIELDS:
                    entry[year_field] = src.get(year_field)
                results.append(entry)

            response = es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
            hits = response.get("hits", {}).get("hits", [])

        es.clear_scroll(scroll_id=scroll_id)

        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(results))
        return jsonify({'Status': 200, 'Data': results})

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({'Status': 500, 'Message': str(e)}), 500