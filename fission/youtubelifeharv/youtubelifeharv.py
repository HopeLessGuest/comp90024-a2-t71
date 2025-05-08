from datetime import datetime, timedelta
import os
import json
from youtube_helper import (build_youtube_client, load_api_key, collect_video_statistics_by_day, get_next_search_period)
from es_helper import (connect_elasticsearch, send_to_elasticsearch, log_search_to_es, get_latest_date)
import urllib3


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
            log_search_to_es(
                es=es,
                start_date=start_date,
                end_date=end_date,
                query=prompt,
                result_count=len(video_statistics),
                index=log_index,
                indexing_stats=indexing_stats
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
    # api_key = 'AIzaSyAe4U7EGjlauzCwu-6Sj-Nxf1wEz8lSBpQ'
    api_key = 'AIzaSyBbDw8fz5hE2bIQSZY-vlhSz2bTGoiwGTg'
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

        # 'melbourne shopping',
        # 'melbourne tourism',

        # 'melbourne restaurants',
        # 'melbourne city walk',
        # 'melbourne cafe',
        'melbourne dessert',
        # 'melbourne vlog',
        # 'melbourne festival'
    ]
    max_pages = 5

    # custom search date range
    search_time_range = 1

    # get search start date and end date
    start_date, end_date = get_next_search_period(es, log_index, search_time_range)

    # [Override] Force start date manually (useful for backfilling or testing)
    start_date = datetime(2025, 4, 1)
    end_date = datetime(2025, 4, 7)

    # Collects YouTube video data for a list of search prompts, stores them into Elasticsearch,
    # and logs the metadata into a separate log index.
    # Store returned general stats in all_stats
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
    return json.dumps(all_stats, ensure_ascii=False, indent=2)


# if __name__ == '__main__':
#     print(main())
