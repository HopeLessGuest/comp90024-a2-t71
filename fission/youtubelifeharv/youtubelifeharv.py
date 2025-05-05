from datetime import datetime, timedelta
import json
import os
from youtube_helper import build_youtube_client, search_videos, get_video_details, load_api_key
from es_helper import connect_elasticsearch, send_to_elasticsearch, log_search_period_to_es, get_latest_date
from elasticsearch import Elasticsearch
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


# Extracts video IDs from a list of search result items.
def extract_video_ids(search_items):
    return [
        item['id']['videoId']
        for item in search_items
        if item.get('id', {}).get('kind') == 'youtube#video' and 'videoId' in item['id']
    ]


# Main entrypoint for Fission
def main():
    # get current time in ISO format
    now = datetime.now().isoformat()[1:19]

    # print separate line
    print(f"================================================================================")
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

    search_results = []
    video_ids = []
    video_statistics = []

    # Connect to ES
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    es = connect_elasticsearch()

    # custom result number and prompt
    search_prompt = 'melbourne food'
    max_pages = 20

    # custom search date
    start_date = datetime(2025, 1, 1)
    search_time_range = 3

    # get search start date and end date
    start_date, end_date = get_next_search_period(es, log_index, search_time_range)

    # Daily incremental search loop (excluding end_date)
    current_date = start_date
    while current_date <= end_date:
        next_date = current_date + timedelta(days=1)
        for page_items in search_videos(
                youtube,
                max_results=50,
                query=search_prompt,
                start_date=current_date,
                end_date=next_date,
                max_pages=max_pages
        ):
            search_results.extend(page_items)

            # Extract video IDs and get statistics
            ids_this_page = extract_video_ids(page_items)
            video_ids.extend(ids_this_page)
            video_statistics.extend(get_video_details(youtube, ids_this_page))

        current_date = next_date  # Move to next day

    # Prepare output
    output = video_statistics

    # Send data to ES and receive returned results stats
    indexing_stats = send_to_elasticsearch(es, output, data_index, data_id_field)

    # Record search period to ES log
    try:
        log_search_period_to_es(es, start_date, end_date, search_prompt, len(video_statistics), log_index, indexing_stats)
        print(f"[OK] Logged search period to {log_index}")
    except Exception as e:
        print(f"[X] Failed to log search period: {e}")

    # # Write searched log
    # save_end_date(end_date)

    # return as JSON
    return "done"

# if __name__ == '__main__':
#     print(main())
