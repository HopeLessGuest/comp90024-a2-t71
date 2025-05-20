import os
import json
import logging
from flask import request, jsonify
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from typing import Optional
import redis

# Set up logging
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

def main():
    logging.info('Elasticsearch API - Aggregation for Heatmap Initiated')


    # Extract and validate headers
    req = request
    start_date: Optional[str] = req.headers.get('X-Fission-Params-Startdate')
    end_date: Optional[str] = req.headers.get('X-Fission-Params-Enddate')

    if not (start_date and end_date):
        return jsonify({'Status': 400, 'Message': 'Start date and end date are required.'}), 400


    # Check Redis cache
    cache_key = f"trafficaggbyhour:{start_date}:{end_date}"
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

        # Adjust the time range to cover full days
        start_time = f"{start_date}T00:00:00"
        end_time = f"{end_date}T23:59:59"

        # Build the aggregation query
        search_body = {
            "size": 0,
            "query": {
                "range": {
                    "latest_stats.interval_start": {
                        "gte": start_time,
                        "lte": end_time
                    }
                }
            },
            "aggs": {
                "hourly_aggregation": {
                    "date_histogram": {
                        "field": "latest_stats.interval_start",
                        "fixed_interval": "2h"
                    },
                    "aggs": {
                        "avg_density": {"avg": {"field": "latest_stats.average_density"}},
                        "avg_congestion": {"avg": {"field": "latest_stats.congestion"}},
                        "avg_speed": {"avg": {"field": "latest_stats.speed"}},
                        "avg_delay": {"avg": {"field": "latest_stats.delay"}}
                    }
                }
            }
        }

        # Execute the search
        response = es.search(index=INDEX_NAME, body=search_body)

        # Extract and format results
        results = [
            {
                "timestamp": bucket["key_as_string"],
                "avg_density": bucket["avg_density"]["value"],
                "avg_congestion": bucket["avg_congestion"]["value"],
                "avg_speed": bucket["avg_speed"]["value"],
                "avg_delay": bucket["avg_delay"]["value"]
            }
            for bucket in response["aggregations"]["hourly_aggregation"]["buckets"]
        ]

        # Cache the result in Redis
        redis_client.setex(cache_key, timedelta(minutes=10), json.dumps(results))

        logging.info(f"Search Results: {len(results)} tracks retrieved and cached.")
        return jsonify({'Status': 200, 'Data': results})


    except Exception as e:
        logging.error(f'Error at Elasticsearch API: {str(e)}')
        return ERROR, 500
