from datetime import datetime, timedelta
import os
import json
from youtube_helper import (build_youtube_client, load_api_key, collect_video_statistics_by_day)
from es_helper import (connect_elasticsearch, send_to_elasticsearch, log_search_period_to_es, get_latest_date)
import urllib3


# # Load the last recorded search date from the local log file (ISO format)
# def load_last_date(log_file="search_log.txt", search_start_date="2025-01-01"):
#     if Path(log_file).exists():
#         with open(log_file, "r") as f:
#             lines = f.read().strip().splitlines()
#             if lines:
#                 return datetime.fromisoformat(lines[-1])
#     return datetime.fromisoformat(search_start_date) - timedelta(days=1)
#
#
# # Load the last recorded search date from the ES log file (ISO format)
#
# def load_last_date_from_es(es, index="youtube-log"):
#     resp = es.search(
#         index=index,
#         size=1,
#         sort=[{"end_date": {"order": "desc"}}]
#     )
#     if resp['hits']['hits']:
#         return datetime.fromisoformat(resp['hits']['hits'][0]['_source']['end_date'])
#     return datetime.fromisoformat("2025-01-01") - timedelta(days=1)
#
#
# # Append the current search end date to the log file in ISO format
# def save_end_date(end_date, log_file="search_log.txt"):
#     with open(log_file, "a") as f:
#         f.write(end_date.date().isoformat() + "\n")


# Get the date search range for YouTube search (default: 7 days)
def get_next_search_period(es, log_index, search_range=7):
    start_date = get_latest_date(es, log_index) + timedelta(days=1)
    end_date = start_date + timedelta(days=search_range - 1)
    print(f"[Search Period] Start: {start_date.date()}, End: {end_date.date()}")
    return start_date, end_date


# Collects YouTube video data for a list of search prompts, stores them into Elasticsearch,
#     and logs the metadata into a separate log index.
#  Returns summary of indexing stats or errors for each keyword.
def collect_and_store_for_keywords(youtube, es, search_prompts, start_date, end_date, data_index, log_index,
                                   data_id_field="id", max_pages=20):
    all_stats = []

    for prompt in search_prompts:
        print(f"\n▶ Searching: {prompt}")
        try:
            # Perform search and collect video details for the date range
            search_results, video_ids, video_statistics = collect_video_statistics_by_day(
                youtube=youtube,
                search_prompt=prompt,
                start_date=start_date,
                end_date=end_date,
                max_pages=max_pages
            )

            # Send video details to Elasticsearch
            indexing_stats = send_to_elasticsearch(
                es,
                video_statistics,
                index=data_index,
                id_field=data_id_field
            )

            # Log the search metadata to Elasticsearch
            log_search_period_to_es(
                es=es,
                start_date=start_date,
                end_date=end_date,
                query=prompt,
                result_count=len(video_statistics),
                index=log_index,
                **indexing_stats
            )

            # Record stats for current keyword
            all_stats.append({
                "keyword": prompt,
                **indexing_stats
            })

        except Exception as e:
            print(f"[X] Failed to collect for keyword '{prompt}': {e}")
            all_stats.append({
                "keyword": prompt,
                "error": str(e)
            })

    return all_stats

# Main entrypoint for Fission
def main():
    # get current time in ISO format
    now = datetime.now().isoformat()[1:19]

    # print separate line
    print(f"==================== Function started ====================")
    print(f"[OK] Program started at {now} ")

    # set api key
    api_key = load_api_key()
    api_key = 'AIzaSyAe4U7EGjlauzCwu-6Sj-Nxf1wEz8lSBpQ'
    youtube = build_youtube_client(api_key)

    # # set log file path and es index name
    # log_file = "search_log.txt"
    # data_index = "youtube-videos-tariff"
    # data_id_field = "id"
    # log_index = "youtube-videos-tariff-logs"

    # set log file path and es index name
    log_file = "search_log.txt"
    data_index = "youtube-videos-life"
    data_id_field = "id"
    log_index = "youtube-videos-life-logs"

    # Connect to ES
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    es = connect_elasticsearch()

    # custom result number and prompt
    search_prompts = [
        'melbourne food',
        'melbourne shopping',
        'melbourne tourism',
        # 'melbourne restaurants',
        # 'melbourne citywalk'
    ]
    max_pages = 2

    # custom search date
    start_date = datetime(2025, 1, 1)
    search_time_range = 3

    # get search start date and end date
    start_date, end_date = get_next_search_period(es, log_index, search_time_range)

    # Collects YouTube video data for a list of search prompts, stores them into Elasticsearch,
    # and logs the metadata into a separate log index.
    # Store returned general stats inall_stats
    all_stats = collect_and_store_for_keywords(
        youtube=youtube,
        es=es,
        search_prompts=search_prompts,
        start_date=start_date,
        end_date=end_date,
        data_index=data_index,
        log_index=log_index,
        max_pages=max_pages
    )

    # return as JSON
    return all_stats
    # return json.dumps(all_stats, ensure_ascii=False)

# if __name__ == '__main__':
#     print(main())
