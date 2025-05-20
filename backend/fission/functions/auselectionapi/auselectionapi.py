from flask import request, jsonify
from elasticsearch8 import Elasticsearch
import time
from datetime import datetime

# ElasticSearch settings
POSTS_INDEX = "reddit_test"
COMMENTS_INDEX = "reddit_comments"
SCROLL_TIMEOUT = "2m"
USERNAME = "elastic"
PASSWORD = "elastic"


def main():
    try:
        # Get parameters from request
        start_date: Optional[str] = request.headers.get('X-Fission-Params-Startdate')
        end_date: Optional[str] = request.headers.get('X-Fission-Params-Enddate')

        if not (start_date and end_date):
            return jsonify({'Status': 400, 'Message': 'Start date and end date are required.'}), 400


        # Transfer date into unix timestamp
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        unix_start = int(time.mktime(start_dt.timetuple()))

        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        unix_end = int(time.mktime(end_dt.timetuple()))

        # ElasticSearch init
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic:9200"],
            basic_auth=(USERNAME, PASSWORD),
            verify_certs=False,
            ssl_show_warn=False
        )

        results = []

        # Use Elasticsearch Scroll to Retrieve a Specified Field from an Index, Sorted and Filtered by Its Timestamp Field
        def scroll_and_collect(index_name, source_field, timestamp_field, result_key):
            body = {
                "_source": [source_field],
                "query": {
                    "range": {
                        timestamp_field: {
                            "gte": unix_start,
                            "lte": unix_end,
                            "format": "epoch_second"
                        }
                    }
                },
                "sort": [{timestamp_field: "asc"}]
            }

            resp = es.search(index=index_name, body=body, scroll=SCROLL_TIMEOUT)
            scroll_id = resp.get("_scroll_id")
            hits      = resp.get("hits", {}).get("hits", [])

            while hits:
                for hit in hits:
                    val = hit["_source"].get(source_field)
                    if val:
                        results.append({result_key: val})
                resp = es.scroll(scroll_id=scroll_id, scroll=SCROLL_TIMEOUT)
                hits = resp.get("hits", {}).get("hits", [])
                
            es.clear_scroll(scroll_id=scroll_id)

        scroll_and_collect(POSTS_INDEX, "original_text", "created_utc", "comments")
        scroll_and_collect(COMMENTS_INDEX, "comment_body", "comment_created_utc", "comments")

        return jsonify({'Status': 200, 'Data Length': len(results), 'Data': results})

    except Exception as e:
        return jsonify({'Status': 500, 'Message': str(e)}), 500


