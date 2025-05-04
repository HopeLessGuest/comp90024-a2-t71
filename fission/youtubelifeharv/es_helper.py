from datetime import datetime
from elasticsearch import Elasticsearch

# Connect to Kubernetes Elasticsearch
def connect_elasticsearch():
    es = Elasticsearch(
        "https://elasticsearch-master.elastic.svc.cluster.local:9200",
        basic_auth=("elastic", "elastic"),
        verify_certs=False
    )
    if es.ping():
        print("✅ Connected to Elasticsearch")
    else:
        print("❌ Failed to connect to Elasticsearch")
    return es


# Send list of documents to Elasticsearch with _id = video_id
def send_to_elasticsearch(es, items, index):
    for item in items:
        video_id = item.get("id")
        if video_id:
            try:
                es.index(index=index, id=video_id, document=item)
            except Exception as e:
                print(f"❌ Failed to index video {video_id}: {e}")


# Log the search metadata to Elasticsearch log index
def log_search_period_to_es(es, start_date, end_date, query=None, result_count=None, index="youtube-log"):
    doc = {
        "start_date": start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }
    if query:
        doc["query"] = query
    if result_count is not None:
        doc["result_count"] = result_count

    es.index(index=index, document=doc)
