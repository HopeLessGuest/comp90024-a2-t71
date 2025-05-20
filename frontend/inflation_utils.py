from typing import Literal

import nltk
import pandas as pd
import requests
from nltk.sentiment import SentimentIntensityAnalyzer

POST_P = "mkx-data/reddit_no_dup_0509-1204.xlsx"
RBA_P = "mkx-data/inflation-RBA-3.xlsx"
COMMENT_P = "mkx-data/reddit_comments_0509-1204.xlsx"

ES_HOSTS: list = [
    "https://127.0.0.1:9200",
    "https://192.168.99.200:9200",
    "https://elasticsearch-master.elastic:9200",
]
ES_HOST = ES_HOSTS[1]

API_HOSTS: list = [
    "http://192.168.99.200:9876"
]
API_HOST = API_HOSTS[0]


def get_rsp_data(u):
    resp_0 = requests.get(u, timeout=10)
    if resp_0.ok:
        return resp_0.json()
    else:
        raise RuntimeError(resp_0.text)


def get_posts_rsp_data():
    u = API_HOST + "/inflation/reddit_posts"
    return get_rsp_data(u)


def get_comments_rsp_data():
    u = API_HOST + "/inflation/reddit_comments"
    return get_rsp_data(u)


def get_df(source: Literal["u", "l"], content: Literal["post", "rba"]):
    assert source in ["u", "l"]
    assert content in ["post", "rba", "comment"]

    if source == "l":
        if content == "post":
            return pd.read_excel(POST_P)
        elif content == "rba":
            return pd.read_excel(RBA_P)
        return None
    elif source == "u":
        if content == "post":
            rsp_data = get_posts_rsp_data()
        elif content == "comment":
            rsp_data = get_comments_rsp_data()
        else:
            raise RuntimeError
        df = transform_rsp_data_to_df_v2(rsp_data)
        return df
    else:
        raise RuntimeError


def transform_rsp_data_to_df_v1(rsp_data):
    rsp_data = [dic_i["_source"] for dic_i in rsp_data]
    keys = rsp_data[0].keys()
    data_cols = list(zip(*gnr_rows(rsp_data)))
    dic = dict(zip(keys, data_cols))
    df = pd.DataFrame(dic)
    return df


def transform_rsp_data_to_df_v2(rsp_data):
    rsp_data = [dic_i["_source"] for dic_i in rsp_data]
    keys = rsp_data[0].keys()
    data_rows = gnr_rows(rsp_data)
    df = pd.DataFrame(data_rows, columns=keys)
    return df


def gnr_rows(rsp_data):
    for dic_i in rsp_data:
        tmp = list(dic_i.values())
        yield tmp


COL_NAME = {
    "vote": "score",
    "comment": "num_comments",
    "cpi": "Year-ended inflation",
}


def tst2():
    nltk.download("vader_lexicon")


def datetime_to_str(series):
    return series.astype("string")


def str_to_datetime(series):
    return pd.to_datetime(series, errors="coerce", utc=True)


def clean_df(df, content: Literal["post", "rba"]):
    if content == "post":
        df["text"] = df["title"].fillna("") + " " + df["selftext"].fillna("")
        df["created_utc"] = str_to_datetime(df["created_utc"])
        df = df.dropna(subset=["created_utc"])
        df = df[df["created_utc"] <= pd.Timestamp.now(tz="UTC")]
        return df
    elif content == "rba":
        df["date"] = pd.to_datetime(df["date"], utc=True)
        return df
    else:
        raise NotImplementedError


def post_sentiment_scores(df):
    sia = SentimentIntensityAnalyzer()
    return df["text"].apply(sia.polarity_scores).apply(pd.Series)


def analyze_sentiment_scores(
    df, mode: Literal["valence", "arousal", "compound"]
) -> pd.Series:
    if mode == "valence":
        return df["pos"] - df["neg"]  # 方向
    elif mode == "arousal":
        return df["compound"].abs()  # 强度
    elif mode == "compound":
        return df["compound"]
    raise NotImplementedError


def statistic_by_season(
    df,
    date_column,
    on_column,
    rst_column_name,
    mode: Literal["size", "mean"],
    time_range_slice,
) -> pd.Series:
    rsp = df.set_index(date_column).resample("QE")

    if mode == "size":
        s = rsp.size()
    elif mode == "mean":
        s = rsp[on_column].mean()
    else:
        raise NotImplementedError
    return s.rename(rst_column_name).loc[time_range_slice]
