import os
import json
import logging
import redis
from flask import request, jsonify
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch

# set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Redis configuration
REDIS_HOST = "172.22.34.220"
REDIS_PORT = 6379
REDIS_DB = 0
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Index name
INDEX_NAME = "music_top_tracks_australia"

BAD_PARAMS = json.dumps({'Status': 400, 'Message': 'Invalid Parameters'})
ERROR = json.dumps({'Status': 500, 'Message': 'Internal Server Error'})

SCROLL_TIMEOUT = "2m"

def main():
    logging.info('Elasticsearch API - Top Tracks Search Initiated')

    # Extract and validate headers
    req = request
    start_date = req.headers.get('X-Fission-Params-Startdate')
    start_time = req.headers.get('X-Fission-Params-Starttime')
    end_date = req.headers.get('X-Fission-Params-Enddate')
    end_time = req.headers.get('X-Fission-Params-Endtime')

    logging.info(f"Received Headers: Start Date: {start_date}, Start Time: {start_time}, End Date: {end_date}, End Time: {end_time}")

    if not (start_date and start_time and end_date and end_time):
        logging.error("Missing start date, start time, end date, or end time in headers.")
        return jsonify({'Status': 400, 'Message': 'Start date, start time, end date, and end time are required.'}), 400

    # Combine dates and times into full datetime strings
    start_datetime = f"{start_date}T{start_time}"
    end_datetime = f"{end_date}T{end_time}"

    logging.info(f"Start DateTime: {start_datetime}")
    logging.info(f"End DateTime: {end_datetime}")

    # Check Redis cache
    cache_key = f"music_top_tracks:{start_datetime}:{end_datetime}"
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

        # Construct the search body
        search_body = {
            "_source": ["artist", "track", "listeners", "timestamp"],
            "query": {
                "range": {"timestamp": {"gte": start_datetime, "lte": end_datetime}}
            },
            "sort": [{"timestamp": "asc"}]
        }

        # Execute the search (scroll for all data)
        response = es.search(index=INDEX_NAME, body=search_body, scroll=SCROLL_TIMEOUT)
        hits = response.get("hits", {}).get("hits", [])
        scroll_id = response.get("_scroll_id")
        results = []

        while hits:
            for hit in hits:
                results.append({
                    "artist": hit["_source"].get("artist"),
                    "track": hit["_source"].get("track"),
                    "listeners": hit["_source"].get("listeners"),
                    "timestamp": hit["_source"].get("timestamp")
                })

            response = es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
            hits = response.get("hits", {}).get("hits", [])

        es.clear_scroll(scroll_id=scroll_id)

        # Cache the result in Redis
        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(results))

        logging.info(f"Search Results: {len(results)} tracks retrieved and cached.")
        return jsonify({'Status': 200, 'Data': results})

    except Exception as e:
        logging.error(f'Error at Elasticsearch API: {str(e)}')
        return jsonify({'Status': 500, 'Message': str(e)}), 500
