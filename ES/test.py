from elasticsearch import Elasticsearch


es = Elasticsearch(hosts=["http://localhost:9200"])


print(es.info())