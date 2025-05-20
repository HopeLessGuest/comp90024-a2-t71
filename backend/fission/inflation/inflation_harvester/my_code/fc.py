import os
import random
import time
from datetime import datetime, timezone
from math import ceil
from pathlib import Path

import pandas as pd
import praw
from elasticsearch import Elasticsearch, helpers
from elasticsearch.helpers import BulkIndexError

from reddit_get_comments import get_comments

DATA_FOLDER = Path("mkx-data")
HOSTS_LST = [
    "https://127.0.0.1:9200",
    "https://192.168.99.200:9200",
    "https://elasticsearch-master.elastic:9200",
]
HOSTS = HOSTS_LST[2]


def create_index(es, msg_body, index_name):
    """If an index with the same name already exists, do nothing."""
    if es.indices.exists(index=index_name):
        print(f'Index "{index_name}" already exists; skipping creation.')
    else:
        es.indices.create(index=index_name, body=msg_body)
        print(f'Index "{index_name}" has been created.')


def upload_batch_data_to_index(df, index_name, es, id_col_name):
    def actions():
        for rec in df.to_dict(orient="records"):
            yield {"_index": index_name, "_id": rec[id_col_name], "_source": rec}

    try:
        success, _ = helpers.bulk(
            es.options(request_timeout=60),
            actions(),
            chunk_size=1000
        )
        print(f"✅ Successfully wrote {success} documents")
    except BulkIndexError as e:
        print(f"❌ {len(e.errors)} failures occurred; first error:")
        print(e.errors[0])
        raise


def get_es():
    return Elasticsearch(
        hosts=[HOSTS],
        basic_auth=("elastic", "elastic"),
        verify_certs=False
    )


def create_index_inflation_reddit_posts(es, index_name):
    """If an index with the same name already exists, do nothing."""
    mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "title": {"type": "text"},
                "subreddit": {"type": "keyword"},
                "score": {"type": "integer"},
                "num_comments": {"type": "integer"},
                "created_utc": {"type": "date", "format": "yyyy-MM-dd HH:mm:ssZ"},
                "url": {"type": "keyword"},
                "selftext": {"type": "text"}
            }
        }
    }
    create_index(es=es, msg_body=mapping, index_name=index_name)


def df_clean_for_es(df, mode):
    assert mode in ["comment", "post"]
    if mode == "comment":
        df = df[df["author"] != "[deleted]"]
    df["created_utc"] = (
        pd.to_datetime(df["created_utc"], utc=True)
        .dt.strftime("%Y-%m-%d %H:%M:%S%z")
    )
    return df.replace({pd.NA: None})


def posts_to_es(df: pd.DataFrame | str):
    """
    Args:
        df: dataframe or xlsx path
    """
    es = get_es()

    index_name = "inflation-reddit-posts"
    create_index_inflation_reddit_posts(es, index_name)

    if isinstance(df, pd.DataFrame):
        pass
    elif isinstance(df, str):
        df = pd.read_excel(df)

    df = df_clean_for_es(df, mode="post")
    upload_batch_data_to_index(df, index_name, es, "id")


def lst_split(lst, num_pieces):
    elem_per_piece = ceil(len(lst) / num_pieces)
    rst = []
    for i in range(num_pieces):
        start = i * elem_per_piece
        end = min(start + elem_per_piece, len(lst))
        rst.append(lst[start:end])
    return rst


def subm_extract_dict(subm):
    return {
        "id": subm.id,
        "title": subm.title,
        "subreddit": subm.subreddit.display_name,
        "score": subm.score,
        "num_comments": subm.num_comments,
        "created_utc": str(datetime.fromtimestamp(subm.created_utc, timezone.utc)),
        "url": subm.url,
        "selftext": subm.selftext[:4000],
    }


def get_posts(
        sort_mode,
        keywords,
        subreddits,
        au_subrdts,
        save_to,
):
    assert save_to in ["es", "local_file"]
    # 1. 初始化
    reddit = praw.Reddit(
        client_id="ea32-gL0osbrWNkehaG5jg",
        client_secret="DV35mgPefuLdq3_AI-XMkUdsJ9PENg",
        user_agent="australia_cost_of_living_bot/0.1 by your_username"
    )

    base_q = "(" + " OR ".join(keywords) + ")"

    posts = []
    for sub in subreddits:
        is_au = sub.lower() in au_subrdts
        query = base_q if is_au else f"australia AND {base_q}"
        try:
            for subm in reddit.subreddit(sub).search(
                    query, sort=sort_mode, syntax="lucene", limit=1000):
                posts.append(subm_extract_dict(subm))
            time.sleep(1)
        except Exception as e:
            print(f"{sub}: search failed {e}")

    df = pd.DataFrame(posts)
    print(f"before removing dups，posts num is {len(df)}")

    df.drop_duplicates(subset="id", keep="first", inplace=True)
    print(f"after removing dups，posts num is {len(df)}")

    if save_to == "local_file":
        name_suffix = 1
        output_file_name = f"reddit_australia_cost_of_living_{name_suffix}.xlsx"
        output_file_path = str(DATA_FOLDER / output_file_name)
        while os.path.exists(output_file_path):
            name_suffix += 1
            output_file_name = f"reddit_australia_cost_of_living_{name_suffix}.xlsx"
            output_file_path = str(DATA_FOLDER / output_file_name)
        df.to_excel(output_file_path, index=False)
        print(f"saved to {output_file_path}.")
    elif save_to == "es":
        print("uploading to es...")
        posts_to_es(df)
        get_comments(df)


def main_entry(
        save_to
):
    assert save_to in ["es", "local_file"]

    sort_mode_list = [
        "relevance", "hot", "top", "new", "comments"
    ]

    keywords_candidates = [
        # core words
        "inflation", "stagflation", "hyperinflation",
        "cpi", '"consumer price index"', '"headline inflation"',
        '"core inflation"', '"price index"', '"price indices"',
        '"trimmed mean"', '"weighted median"',

        # official words
        '"rate hike"', '"interest rate hike"', '"rate rises"', '"cash rate"',
        '"mortgage rate"', '"home loan rate"', '"variable rate"',
        '"reserve bank"', "rba", '"rba decision"', '"abs cpi"',

        # living cost
        '"cost of living"', '"living cost*"', '"living expenses"', '"living costs"',
        '"affordability crisis"', '"can\'t afford"', '"struggling to pay"',

        # price
        '"price increase"', '"price rise"', '"price rises"', '"price hike"',
        '"price spike"', '"prices up"', '"prices are up"', '"price gouging"',
        '"food prices"', '"grocery prices"', '"grocery bill"', '"checkout shock"',
        '"fuel price"', '"petrol price"', '"petrol cost"', '"fuel excise"',
        '"power bill"', '"electricity bill"', '"utility bill"', '"bill shock"',

        # house, rent
        '"rent increase"', '"rent rise"', '"rent rises"', '"rent hike"',
        '"rent up"', '"rent crisis"', '"rent is insane"', '"rental vacancy"',
        '"housing affordability"', '"mortgage stress"',

        # wage
        '"wage growth"', '"real wage"', '"wage stagnation"', '"pay packet"',
        '"real income"', '"real earnings"',

        # aus supermarkets
        '"coles prices"', '"woolies prices"', '"aldi prices"'
    ]
    random.shuffle(keywords_candidates)
    keywords_candidates = lst_split(keywords_candidates, 6)

    # query = 'australia cost of living OR australia inflation'
    subreddit_candidates = [
        "australia",
        "australian",
        "aussie",
        "AusEcon",
        "AusFinance",
        "Economics",
        "AskAnAustralian",
    ]

    au_subrdts = {
        "australia", "ausfinance", "ausecon", "aussie", "askanaustralian"
    }

    for sort_mode_i in sort_mode_list:
        for keywords_i in keywords_candidates:
            print(
                f"Will be used:\n"
                f"sort_mode_i = {sort_mode_i},\n"
                f"keywords_i = {keywords_i}"
            )
            get_posts(
                sort_mode=sort_mode_i,
                keywords=keywords_i,
                subreddits=subreddit_candidates,
                au_subrdts=au_subrdts,
                save_to=save_to,
            )
            print("Completed, move to the next part.\n")


if __name__ == '__main__':
    main_entry(save_to="es")
