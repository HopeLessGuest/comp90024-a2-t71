import os
import json
import logging
from flask import request, jsonify
from datetime import datetime
from elasticsearch import Elasticsearch

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Elasticsearch Configuration ===
ES_HOST = "https://elasticsearch-master.elastic:9200"
ES_USER = "elastic"
ES_PASS = "elastic"
ES_INDEX = "youtube-videos-life"

# === Main Function ===
def main():
    try:
        # Parse query parameters or use default
        start_date_str = request.args.get("start", "2024-01-01")
        end_date_str = request.args.get("end", datetime.utcnow().date().isoformat())

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").isoformat() + "Z"
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").isoformat() + "Z"

        # Connect to Elasticsearch
        es = Elasticsearch(
            hosts=[ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            verify_certs=False
        )

        # Construct query
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
            "size": 1  # Adjust as needed
        }

        # Query Elasticsearch
        response = es.search(index=ES_INDEX, body=query)
        hits = response.get("hits", {}).get("hits", [])
        results = [hit["_source"] for hit in hits]

        return jsonify({"status": 200, "data": results})

    except Exception as e:
        logging.error(f"[X] Failed to fetch data: {e}")
        return jsonify({"status": 500, "message": str(e)}), 500

# === Local testing ===
if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.add_url_rule('/', 'main', main, methods=['GET'])
    app.run(host='0.0.0.0', port=5000, debug=True)