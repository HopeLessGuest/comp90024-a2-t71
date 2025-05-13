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
ES_INDEX = "youtube-videos-election"  # Election data index

# === Main function for Fission ===
def main():
    try:
        # === Step 1: Extract 'start' and 'end' from query string ===
        start_date_str = request.args.get("start")
        end_date_str = request.args.get("end")

        # === Step 2: Set default values if missing ===
        if not start_date_str:
            start_date_str = "2024-01-01"  # Default start for election videos
        if not end_date_str:
            end_date_str = datetime.now(timezone.utc).date().isoformat()

        # === Step 3: Parse to ISO format ===
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").isoformat() + "Z"
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").isoformat() + "Z"

        # === Step 4: Connect to Elasticsearch ===
        es = Elasticsearch(
            hosts=[ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            verify_certs=False
        )

        # === Step 5: Build and send ES query ===
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
            "size": 10000
        }

        response = es.search(
            index=ES_INDEX,
            query=query["query"],
            sort=query["sort"],
            size=query["size"],
            source_excludes=[
                "snippet.thumbnails",
                "snippet.localized",
                "snippet.defaultAudioLanguage",
                "snippet.defaultLanguage",
                "contentDetails.caption",
                "contentDetails.licensedContent",
                "contentDetails.projection",
                "contentDetails.contentRating",
                "contentDetails.regionRestriction"
            ]
        )
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
        logging.error(f"[X] Error occurred: {e}")
        return Response(
            json.dumps({"status": 500, "message": str(e)}),
            mimetype='application/json',
            status=500
        )
