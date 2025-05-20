from pathlib import Path

import numpy as np
import pandas as pd
from elasticsearch import helpers

from mkx_es import get_es

DATA_FOLDER = Path("../../../process_data/mkx-data")


def tst2():
    """关键一步：统一替换列名里的 EN-dash"""
    df = pd.read_excel("inflation-RBA-2.xlsx")
    df.columns = [col.replace("\u2013", "-") for col in df.columns]

    # 先拿到除 date 之外的所有列名
    # noinspection PyUnresolvedReferences
    value_cols = df.columns.difference(['date'])
    # 如果这些列全是 NaN，就删掉该行
    df = df.dropna(subset=value_cols, how='all')

    # 把日期转 ISO 字符串
    df["date"] = (
        pd.to_datetime(df["date"], utc=True)
        .dt.strftime("%Y-%m-%d %H:%M:%S%z")
    )

    # 导出为新的excel
    df.to_excel("inflation-RBA-3.xlsx", index=False)

    # # 导出成 ndjson（每行一条 JSON，供 _bulk 用）
    # df.to_json("inflation.ndjson", orient="records", lines=True)


def batch_upload_data():
    """
    批量写入数据，假设已经有了index
    """

    es = get_es()

    index = "inflation-rba"

    excel_path = "mkx/process_data/mkx-data/inflation-RBA-3.xlsx"
    df = pd.read_excel(excel_path)
    df = df.replace({np.nan: None})
    df["date"] = (
        pd.to_datetime(df["date"], utc=True)
        .dt.strftime("%Y-%m-%d %H:%M:%S%z")
    )

    def doc_generator(dataframe: pd.DataFrame):
        for record in dataframe.to_dict(orient="records"):
            yield {
                "_index": index,
                "_id": record["date"],
                "_source": record
            }

    success, errors = helpers.bulk(
        client=es,
        actions=doc_generator(df),
        chunk_size=1000,
        request_timeout=60
    )

    print(f"Indexed: {success}  |  Errors: {errors}")


if __name__ == '__main__':
    batch_upload_data()
