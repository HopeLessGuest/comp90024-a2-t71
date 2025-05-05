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


# Send list of documents to Elasticsearch with custom index, return upload stats
def send_to_elasticsearch(es, items, index, id_field=None):
    stats = {
        "docs_attempted": 0,
        "created": 0,
        "updated": 0,
        "failed": 0
    }

    for item in items:
        stats["docs_attempted"] += 1
        try:
            if id_field and id_field in item:
                doc_id = item[id_field]
                result = es.index(index=index, id=doc_id, document=item)
            else:
                result = es.index(index=index, document=item)

            if result.get("result") == "created":
                stats["created"] += 1
            elif result.get("result") == "updated":
                stats["updated"] += 1

        except Exception as e:
            print(f"[X] Failed to index document: {e}")
            stats["failed"] += 1

    return stats


# Log the search metadata to Elasticsearch log index
def log_search_period_to_es(es, start_date, end_date, query=None, result_count=None, index="youtube-log",
                            indexing_stats=None):
    doc = {
        "start_date": start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }

    if query:
        doc["query"] = query
    if result_count is not None:
        doc["result_count"] = result_count
    if indexing_stats:
        doc["docs_attempted"] = indexing_stats.get("docs_attempted", 0)
        doc["created"] = indexing_stats.get("created", 0)
        doc["updated"] = indexing_stats.get("updated", 0)
        doc["failed"] = indexing_stats.get("failed", 0)

    try:
        es.index(index=index, document=doc)
        print(f"[OK] Logged search period to {index}")
    except Exception as e:
        print(f"[X] Failed to log search period: {e}")


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
            print(f"[!] Index '{index}' has no logs. Using fallback start date: 2025-05-01")
    except Exception as e:
        print(f"[X] Error querying index '{index}': {e}")
        print("[!] Using fallback start date: 2025-05-01 due to error.")

    return datetime.fromisoformat("2025-05-01")
