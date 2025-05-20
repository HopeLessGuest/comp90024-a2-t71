import json

from elasticsearch import Elasticsearch
from flask import request, jsonify, Response

HOSTS_LST = [
    "https://127.0.0.1:9200",
    "https://192.168.99.200:9200",
    "https://elasticsearch-master.elastic:9200",
]
HOSTS = HOSTS_LST[2]


def get_es():
    return Elasticsearch(
        hosts=[HOSTS],
        basic_auth=("elastic", "elastic"),
        verify_certs=False,
    )


def minimal_tst():
    es = get_es()

    # 1️⃣ 直接 match_all，size=10
    resp = es.search(index="inflation-reddit-posts", size=10, query={"match_all": {}})

    # 2️⃣ 提取命中文档
    msg = resp["hits"]
    msg_data = msg["hits"]

    # 3️⃣ 打印结果示例
    print(f"总命中 {msg['total']['value']} 条，先看前 10 条：\n")
    for h in msg_data:
        src = h["_source"]
        # print(
        #     f"- {src['created_utc']} "
        #     f"| score={src['score']} "
        #     f"| {src['title'][:80]}…"
        # )
        print(json.dumps(src))


def gnr_scroll_v1(es, index_name="inflation-reddit-posts"):
    resp = es.search(index=index_name, scroll="2m", size=1000, query={"match_all": {}})
    scroll_id = resp["_scroll_id"]

    batch: list = resp["hits"]["hits"]
    while batch:
        yield batch
        resp = es.scroll(scroll_id=scroll_id, scroll="2m")
        batch = resp["hits"]["hits"]


def tst_gnr_scroll_v1():
    es = get_es()
    rst = []
    for batch in gnr_scroll_v1(es, "inflation-reddit-posts"):
        rst.extend(batch)
    return json.dumps(rst)


def gnr_scroll_v2(
    es,
    index_name,
    scroll="2m",
    size=1000,
    query=None,
):
    """生成器，每次yield一个str，是一行数据的ndjson格式"""
    if query is None:
        query = {"match_all": {}}

    resp = es.search(index=index_name, scroll=scroll, size=size, query=query)
    scroll_id = resp["_scroll_id"]

    batch: list = resp["hits"]["hits"]
    while batch:
        for doc in batch:
            yield json.dumps(doc["_source"]) + "\n"  # 一行 NDJSON
        resp = es.scroll(scroll_id=scroll_id, scroll="2m")
        scroll_id = resp["_scroll_id"]

    es.clear_scroll(scroll_id=scroll_id)


def build_stream_response_on_gnr_scroll_v2(
    es,
    index_name,
    scroll="2m",
    size=1000,
    query=None,
):
    gen = gnr_scroll_v2(es, index_name, scroll, size, query)
    return Response(gen, mimetype="application/x-ndjson", direct_passthrough=True)


def fission_es_both_tst():
    return str(get_es().info())


def tst_get_param_query_body():
    return jsonify(get_param_query_body())


def get_param_query_body():
    """
    获取请求携带的参数信息
    {
        "param_item": param_item,
        "query": query,
        "body": body,
    }
    """
    param_item: str = request.headers.get("X-Fission-Params-Item")
    query: dict = request.args  # /api/foo?x=1
    body = request.get_json(silent=True)
    return {
        "param_item": param_item,
        "query": query,
        "body": body,
    }


def get_all_rows(es, index_name):
    pass


def build_es_query_param(query, date_field_name):
    if query:
        range_param = {}
        if query.get("start"):
            # 追加午夜 + 时区，匹配映射格式 yyyy-MM-dd HH:mm:ssZ
            range_param["gte"] = f"{query['start']} 00:00:00+0000"
        if query.get("end"):
            range_param["lte"] = f"{query['end']} 23:59:59+0000"

        es_query = (
            {"bool": {"filter": [{"range": {date_field_name: range_param}}]}}
            if range_param
            else {"match_all": {}}
        )
    else:
        es_query = {"match_all": {}}

    return es_query


def inflation_reddit_posts(es: Elasticsearch, query: dict):
    """
    Args:
        es (Elasticsearch):
        query (dict): 字典有start和end键，值格式样例为2000-11-01。表示搜索范围日期。
            如果不指定日期，应该传入空字典{}，而不是传入None或其他值。

    Returns:
        list: 每个元素对应一行Elasticsearch的数据，把它添加缩进和换行后的样例为，
            {
                '_id': '17d0acl',
                '_index': 'inflation-reddit-posts',
                '_score': 1.0,
                '_source':
                    {
                        'created_utc':
                        '2023-10-21 11:17:14+0000',
                        'id': '17d0acl',
                        'num_comments': 22,
                        'score': 0,
                        'selftext': 'xxx',
                        'subreddit': 'australia',
                        'title': '',
                        'url': 'https://xxx/'
                    }
            }
    """
    es_query = build_es_query_param(query, date_field_name="created_utc")
    resp = es.search(index="inflation-reddit-posts", size=9999, query=es_query)

    msg: dict = resp["hits"]
    msg_data: list = msg["hits"]

    return msg_data

    # return build_stream_response_on_gnr_scroll_v2(
    #     es, index_name="inflation-reddit-posts"
    # )


def inflation_reddit_comments(es: Elasticsearch, query: dict) -> list:
    es_query = build_es_query_param(query, date_field_name="created_utc")
    resp = es.search(index="inflation-reddit-comments", size=9999, query=es_query)
    msg: dict = resp["hits"]
    msg_data: list = msg["hits"]
    return msg_data


def inflation_rba(es: Elasticsearch, query: dict) -> list:
    """"""
    es_query = build_es_query_param(query, date_field_name="date")
    resp = es.search(index="inflation-rba", size=9999, query=es_query)

    msg: dict = resp["hits"]
    msg_data: list = msg["hits"]
    return msg_data


def tst_inflation_rba() -> list:
    es = get_es()
    query = {
        "start": "2020-01-01",
        "end": "2024-01-01",
    }
    return inflation_rba(es, query)


ROUTER = {
    "reddit_posts": inflation_reddit_posts,
    "rba": inflation_rba,
    "reddit_comments": inflation_reddit_comments,
}


def tst_inflation_reddit_posts():
    es = get_es()
    query = {
        # "start": "2020-01-01",
        # "end": "2024-01-01",
    }
    return inflation_reddit_posts(es, query)


def route(es, req_info):
    param_item = req_info.get("param_item")
    assert param_item in ROUTER

    query = req_info.get("query")
    # body = req_info.get("body")

    operation = ROUTER.get(param_item)
    return operation(es, query)


def tst_route():
    es = get_es()
    req_info: dict = get_param_query_body()
    return route(es, req_info)


def main():
    a = jsonify(tst_route())
    # a = tst_inflation_rba()
    return a


if __name__ == "__main__":
    main()
