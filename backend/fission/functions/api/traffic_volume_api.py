import os
import json
import logging
import redis
from flask import request, jsonify
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from typing import Optional

# set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Redis configuration
REDIS_HOST = "172.22.34.220"
REDIS_PORT = 6379
REDIS_DB = 0
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Index name
INDEX_NAME = "transportation_volume_real_time"

BAD_PARAMS = json.dumps({'Status': 400, 'Message': 'Invalid Parameters'})
ERROR = json.dumps({'Status': 500, 'Message': 'Internal Server Error'})

SCROLL_TIMEOUT = "2m"

def main():
    logging.info('Elasticsearch API - Search Initiated')

    # Get parameters from request
    req = request
    start_date: Optional[str] = req.headers.get('X-Fission-Params-Startdate')
    start_time: Optional[str] = req.headers.get('X-Fission-Params-Starttime')
    end_date: Optional[str] = req.headers.get('X-Fission-Params-Enddate')
    end_time: Optional[str] = req.headers.get('X-Fission-Params-Endtime')

    logging.info(f"Index: {INDEX_NAME}")
    logging.info(f"Start Date: {start_date}")
    logging.info(f"Start Time: {start_time}")
    logging.info(f"End Date: {end_date}")
    logging.info(f"End Time: {end_time}")

    if not (start_date and start_time and end_date and end_time):
        return jsonify({'Status': 400, 'Message': 'Start date, start time, end date, and end time are required.'}), 400

    # Construct full datetime
    start_datetime = f"{start_date}T{start_time}"
    end_datetime = f"{end_date}T{end_time}"

    # Check Redis cache
    cache_key = f"trafficvolume:{start_datetime}:{end_datetime}"
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
                "average_coord",
                # "latest_stats.congestion",
                # "latest_stats.speed",
                "latest_stats.average_density",
                # "latest_stats.delay",
                "latest_stats.interval_start"
            ],
            "query": {
                "range": {
                    "latest_stats.interval_start": {
                        "gte": start_datetime,
                        "lte": end_datetime
                    }
                }
            },
            "sort": [{"latest_stats.interval_start": "asc"}]
        }

        response = es.search(index=INDEX_NAME, body=search_body, scroll=SCROLL_TIMEOUT)
        hits = response.get("hits", {}).get("hits", [])
        scroll_id = response.get("_scroll_id")
        results = []

        while hits:
            for hit in hits:
                results.append({
                    "coordinates": hit["_source"].get("average_coord"),
                    # "congestion": hit["_source"].get("latest_stats", {}).get("congestion"),
                    # "speed": hit["_source"].get("latest_stats", {}).get("speed"),
                    "average_density": hit["_source"].get("latest_stats", {}).get("average_density"),
                    # "delay": hit["_source"].get("latest_stats", {}).get("delay"),
                    "interval_start": hit["_source"].get("latest_stats", {}).get("interval_start")
                })

            response = es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
            hits = response.get("hits", {}).get("hits", [])

        es.clear_scroll(scroll_id=scroll_id)

        # Cache the result in Redis
        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(results))

        logging.info(f"Search Results: {len(results)} entries retrieved and cached.")
        return jsonify({'Status': 200, 'Data': results})

    except Exception as e:
        logging.error(f'Error at Elasticsearch API: {str(e)}')
        return jsonify({'Status': 500, 'Message': str(e)}), 500
