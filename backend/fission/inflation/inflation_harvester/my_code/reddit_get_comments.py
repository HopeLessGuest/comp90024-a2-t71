import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pandas as pd
import praw
import prawcore
from tqdm import tqdm

from fc import get_es, df_clean_for_es, upload_batch_data_to_index, create_index

DATA_FOLDER = Path("../../../process_data/mkx-data")

# ────────────────────── 参数区 ──────────────────────
DATA_IN = DATA_FOLDER / "reddit_no_dup_0509-1204.xlsx"
DATA_OUT = DATA_FOLDER / "reddit_comments_0509-1204.xlsx"
BATCH_SZ = 10_000  # 每到阈值立即写盘
MAX_RETRY = 6  # 单帖最多容忍几次 429
THRESHOLD = 2  # 忽略 child_count≤2 的枝杈
SLEEP_BETWEEN_POSTS = 1  # 轻微限速（秒）

# 在模块顶部预编译一个清理用的正则
_ILLEGAL_CHARS = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F]')


def create_index_inflation_reddit_comments(es, index_name):
    """如果已创建同名index，则不会做任何事"""
    mapping_0 = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 1
        },
        "mappings": {
            "properties": {
                "link_id": {"type": "keyword"},
                "comment_id": {"type": "keyword"},
                "parent_id": {"type": "keyword"},
                "author": {"type": "keyword"},
                "created_utc": {"type": "date", "format": "yyyy-MM-dd HH:mm:ssZ"},
                "score": {"type": "integer"},
                "body": {"type": "text"},
            }
        }
    }
    create_index(es=es, msg_body=mapping_0, index_name=index_name)


def gnr_multi_sheet_input_file_to_df(f_path) -> Generator:
    """mainly for the comment xlsx, because it is a single xlsx file with multi sheets"""
    xls = pd.ExcelFile(f_path)  # 先读目录，不载入内容
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        yield df


def comments_to_es(df: pd.DataFrame | str):
    es = get_es()

    index_name = "inflation-reddit-comments"
    create_index_inflation_reddit_comments(es, index_name)

    if isinstance(df, pd.DataFrame):
        df = df_clean_for_es(df, mode="comment")
        upload_batch_data_to_index(
            df,
            index_name,
            es,
            "comment_id",
        )
    elif isinstance(df, str):
        for df_i in gnr_multi_sheet_input_file_to_df(
                f_path=df
        ):
            df_i = df_clean_for_es(df_i, mode="comment")
            # "mkx-data/reddit_comments_0509-1204.xlsx"
            upload_batch_data_to_index(
                df_i,
                index_name,
                es,
                "comment_id",
            )


# ────────────────────── 工具函数 ─────────────────────
def flatten_comment(c, link_id):
    raw = c.body or ""
    # 先截断，再清理（也可以先清理再截断）
    clean = _ILLEGAL_CHARS.sub("", raw)[:4000]
    return {
        "link_id": link_id,
        "comment_id": c.id,
        "parent_id": c.parent_id.split("_")[-1],
        "author": str(c.author) if c.author else "[deleted]",
        "created_utc": datetime.fromtimestamp(c.created_utc, timezone.utc)
        .strftime("%Y-%m-%d %H:%M:%S"),
        "score": c.score,
        "body": clean,
    }


def safe_replace_more(subm):
    """递归展开评论树，自动处理 429"""
    retry = 0
    while True:
        try:
            subm.comments.replace_more(limit=None, threshold=THRESHOLD)
            return
        except prawcore.exceptions.TooManyRequests as e:
            retry += 1
            if retry > MAX_RETRY:
                raise
            wait = int(e.response.headers.get("Retry-After", 30))
            wait += random.randint(5, 15)  # 抖动
            print(f"⏳ 429 退避 {wait}s  (重试 {retry}/{MAX_RETRY})")
            time.sleep(wait)


def flush_buffer(writer, buf, sheet_no):
    """把缓冲区写入新工作表并清空"""
    if not buf:
        return sheet_no
    pd.DataFrame(buf).to_excel(
        writer, sheet_name=f"comments_{sheet_no}", index=False
    )
    print(f"✅ 写入 comments_{sheet_no} ({len(buf)} rows)")
    buf.clear()
    return sheet_no + 1


# ────────────────────── 主流程 ─────────────────────
def get_comments(df, to="es"):
    # 1. 帖子清单
    post_ids = df["id"].dropna().tolist()
    print(f"📝 待抓 {len(post_ids)} 篇帖子")

    # 2. Reddit 实例
    reddit = praw.Reddit(
        client_id="ea32-gL0osbrWNkehaG5jg",
        client_secret="DV35mgPefuLdq3_AI-XMkUdsJ9PENg",
        user_agent="inflation_bot/0.4 (by u/your_username)",
        timeout=20  # 单次 HTTP 最多 20 s
    )

    buffer, sheet_no = [], 1
    with pd.ExcelWriter(DATA_OUT, engine="openpyxl", mode="w") as writer:
        for pid in tqdm(post_ids, desc="posts"):
            try:
                subm = reddit.submission(id=pid)
                safe_replace_more(subm)

                for c in subm.comments.list():
                    # noinspection PyUnresolvedReferences
                    if isinstance(c, praw.models.Comment):
                        buffer.append(flatten_comment(c, pid))
                        if len(buffer) >= BATCH_SZ:
                            if to.lower() == "es":
                                comments_to_es(df=pd.DataFrame(buffer))
                            sheet_no = flush_buffer(writer, buffer, sheet_no)

                time.sleep(SLEEP_BETWEEN_POSTS)

            except Exception as err:
                print(f"⚠️  {pid} 抓取失败：{err}")
                sheet_no = flush_buffer(writer, buffer, sheet_no)
                continue  # 继续下一个帖子

        # 最后一批
        if to == "es":
            comments_to_es(df=pd.DataFrame(buffer))
        flush_buffer(writer, buffer, sheet_no)

    print(f"🎉 all comments fetched. saved to {DATA_OUT}")
