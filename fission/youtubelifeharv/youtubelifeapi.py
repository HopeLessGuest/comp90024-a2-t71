import os
import json
import logging
from datetime import datetime, timezone
from flask import request, Response
from elasticsearch import Elasticsearch

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Elasticsearch Configuration ===
ES_HOST = "https://elasticsearch-master.elastic:9200"
ES_USER = "elastic"
ES_PASS = "elastic"
ES_INDEX = "youtube-videos-life"

# === Main function for Fission ===
def main():
    try:
        # Step 1: Extract start and end from URL path
        path_parts = request.path.strip("/").split("/")

        # Ensure at least 3 parts: e.g., ['youtubelifeapi', '2023-01-01', '2023-12-31']
        if len(path_parts) < 3:
            return Response(
                json.dumps({"status": 400, "message": "11Expected format: /youtubelifeapi/{start}/{end}"}),
                mimetype='application/json',
                status=400
            )

        # Safe extraction of start/end
        start_date_str = path_parts[-2]
        end_date_str = path_parts[-1]

        # === Step 3: Connect to Elasticsearch ===
        es = Elasticsearch(
            hosts=[ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            verify_certs=False
        )

        # === Step 4: Build Elasticsearch query ===
        query = {
            "query": {
                "range": {
                    "snippet.publishedAt": {
                        "gte": start_date,
                        "lte": end_date
                    }
                }
            },
            "sort": [{"snippet.publishedAt": "asc"}],
            "size": 10
        }

        response = es.search(index=ES_INDEX, query=query["query"], sort=query["sort"], size=query["size"])
        hits = response.get("hits", {}).get("hits", [])
        results = [hit["_source"] for hit in hits]

        return Response(
            json.dumps({
                "status": 200,
                "result_count": len(results),
                "data": results
            }, ensure_ascii=False),
            mimetype='application/json'
        )

    except Exception as e:
        logging.error(f"[X] Failed to process request: {e}")
        return Response(
            json.dumps({"status": 500, "message": str(e)}),
            mimetype='application/json',
            status=500
        )
