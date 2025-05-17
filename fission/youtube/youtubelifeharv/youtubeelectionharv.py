from datetime import datetime, timedelta
import os
import json
from youtube_helper import (build_youtube_client, load_api_key, collect_video_statistics_by_day, get_next_search_period)
from es_helper import (connect_elasticsearch, send_to_elasticsearch, log_search_to_es, get_latest_date)
import urllib3
from youtubelifeharv import collect_and_store_for_keywords

# Main entrypoint for Fission
def main():
    # get current time in ISO format
    now = datetime.now().isoformat()[1:19]

    # print separate line
    print(f"==================== Function started ====================")
    print(f"[OK] Program started at {now} ")

    # set api key
    api_key = load_api_key()
    # Anqi's
    # api_key = 'AIzaSyAe4U7EGjlauzCwu-6Sj-Nxf1wEz8lSBpQ'

    # My unimelb email
    api_key = 'AIzaSyDj-BtQS5lNlUxTjNyUtTEAKJ7KsIfJj1w'
    youtube = build_youtube_client(api_key)

    # # set log file path and es index name
    # log_file = "search_log.txt"
    # data_index = "youtube-videos-tariff"
    # data_id_field = "id"
    # log_index = "youtube-videos-tariff-logs"

    # set log file path and es index name
    log_file = "search_log.txt"
    data_index = "youtube-videos-election"
    data_id_field = "id"
    log_index = "youtube-videos-election-logs"

    # Connect to ES
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    es = connect_elasticsearch()

    # custom result number and prompt
    search_prompts = [
        'australia election',
    ]

    max_pages = 3

    # custom search date range
    search_time_range = 1

    # get search start date and end date
    start_date, end_date = get_next_search_period(es, log_index, search_time_range)

    # [Override] Force start date manually (useful for backfilling or testing)
    start_date = datetime(2024, 11, 1)
    end_date = datetime(2024, 12, 30)

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
