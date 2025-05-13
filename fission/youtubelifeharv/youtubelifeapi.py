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
        # === Step 1: Attempt to get start/end from query parameters ===
        start_date_str = request.args.get("start")
        end_date_str = request.args.get("end")

        # === Step 2: If query parameters are missing, try to extract from path ===
        if not start_date_str or not end_date_str:
            # Expected path: /api/youtubelifeapi/start/YYYY-MM-DD/end/YYYY-MM-DD
            parts = request.path.strip("/").split("/")
            if "start" in parts and "end" in parts:
                start_index = parts.index("start") + 1
                end_index = parts.index("end") + 1
                if start_index < len(parts):
                    start_date_str = parts[start_index]
                if end_index < len(parts):
                    end_date_str = parts[end_index]

        # === Step 3: Fallback defaults if still not provided ===
        if not start_date_str:
            start_date_str = "2024-01-01"
        if not end_date_str:
            end_date_str = datetime.now(timezone.utc).date().isoformat()

        # === Step 4: Convert string to full ISO datetime format ===
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").isoformat() + "Z"
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").isoformat() + "Z"

        # === Step 5: Connect to Elasticsearch ===
        es = Elasticsearch(
            hosts=[ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            verify_certs=False
        )

        # === Step 6: Construct Elasticsearch query ===
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

        # === Step 7: Execute query and process results ===
        response = es.search(index=ES_INDEX, query=query["query"], sort=query["sort"], size=query["size"])
        hits = response.get("hits", {}).get("hits", [])
        results = [hit["_source"] for hit in hits]

        # === Step 8: Return formatted JSON response ===
        json_data = {
            "status": 200,
            "result_count": len(results),
            "data": results
        }
        return Response(json.dumps(json_data, ensure_ascii=False), mimetype='application/json')

    except Exception as e:
        # Return error response with status 500
        logging.error(f"[X] Failed to fetch data: {e}")
        return Response(json.dumps({"status": 500, "message": str(e)}), mimetype='application/json', status=500)
