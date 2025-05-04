from datetime import datetime
from elasticsearch import Elasticsearch

# Connect to Kubernetes Elasticsearch
def connect_elasticsearch():
    try:
        es = Elasticsearch(
            "https://elasticsearch-master.elastic.svc.cluster.local:9200",
            basic_auth=("elastic", "elastic"),
            verify_certs=False
        )
        return es
    except Exception as e:
        print(f"[X] Error connecting to Elasticsearch: {e}")
        return None


# Send list of documents to Elasticsearch with custom index
def send_to_elasticsearch(es, items, index, id_field=None):
    for item in items:
        try:
            if id_field and id_field in item:
                doc_id = item[id_field]
                es.index(index=index, id=doc_id, document=item)
            else:
                es.index(index=index, document=item)
        except Exception as e:
            print(f"[X] Failed to index document: {e}")


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


# Get the latest `end_date` from a given Elasticsearch log index.
def get_latest_date(es, index) -> datetime:
    query = {
        "size": 1,
        "sort": [{"end_date": "desc"}]
    }

    try:
        result = es.search(index=index, body=query)
        hits = result.get("hits", {}).get("hits", [])
        if hits:
            end_date_str = hits[0]["_source"].get("end_date")
            print(f"[OK] Latest end_date found in index '{index}': {end_date_str}")
            return datetime.fromisoformat(end_date_str)
        else:
            print(f"[!] Index '{index}' has no logs. Using fallback start date: 2025-05-02")
    except Exception as e:
        print(f"[X] Error querying index '{index}': {e}")
        print("[!] Using fallback start date: 2025-05-02 due to error.")

    return datetime.fromisoformat("2025-05-02")
