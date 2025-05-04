from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from elasticsearch import Elasticsearch


# Load API Key
def load_api_key(filepath='youtube_api_key.txt'):
    zip_path = '/userfunc/deployarchive/youtube_api_key.txt'
    secrets_path = '/secrets/youtube-api-key'
    local_path = filepath

    if os.path.exists(secrets_path):
        print(f"✅ Using secret path: {secrets_path}")
        with open(secrets_path, 'r') as f:
            return f.read().strip()
    elif os.path.exists(zip_path):
        print(f"✅ Using zip path: {zip_path}")
        with open(zip_path, 'r') as f:
            return f.read().strip()
    elif os.path.exists(local_path):
        print(f"✅ Using local path: {local_path}")
        with open(local_path, 'r') as f:
            return f.read().strip()
    else:
        raise FileNotFoundError(f"API key not found in {zip_path} or {filepath} or {secrets_path}")


# Build YouTube API client
def build_youtube_client(api_key):
    return build('youtube', 'v3', developerKey=api_key)


# Search videos
def search_videos(youtube, query, region='AU', max_results=50, start_date=None, end_date=None):
    """
    Search for YouTube videos within an optional date range.

    Parameters:
        youtube: Authenticated YouTube API client.
        query (str): Search query.
        region (str): Region code (default 'AU').
        max_results (int): Max results to fetch (default 20).
        start_date (datetime, optional): Start datetime.
        end_date (datetime, optional): End datetime.

    Returns:
        dict: YouTube API response.
    """
    search_params = {
        'part': 'snippet',
        'q': query,
        'type': 'video',
        'regionCode': region,
        'maxResults': max_results
    }

    if start_date:
        search_params['publishedAfter'] = start_date.isoformat("T") + "Z"
    if end_date:
        search_params['publishedBefore'] = end_date.isoformat("T") + "Z"

    next_page_token = None
    while True:
        if next_page_token:
            search_params['pageToken'] = next_page_token

        response = youtube.search().list(**search_params).execute()
        items = response.get('items', [])
        yield items  # Yield a page of items

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break  # No more pages


# Get video details
def get_video_details(youtube, video_ids):
    response = youtube.videos().list(
        part='snippet,statistics,contentDetails',
        id=','.join(video_ids)
    ).execute()
    return response.get("items", [])


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


# Get the next date range for YouTube search (default: 7 days)
def get_next_search_period(days=7):
    # last_end = load_last_date()
    last_end = datetime.fromisoformat("2025-01-01") - timedelta(days=1)
    start = last_end + timedelta(days=1)
    end = start + timedelta(days=days - 1)
    print(f"[Search Period] Start: {start.isoformat()}, End: {end.isoformat()}")
    return start, end


# Send data to Elastic Search
def send_to_elasticsearch(es, items, index):
    for item in items:
        video_id = item.get("id")
        if video_id:
            try:
                es.index(index=index, id=video_id, document=item)
            except Exception as e:
                print(f"❌ Failed to index video {video_id}: {e}")


# Connect to k8s Elastic Search database
def connect_elasticsearch():
    es = Elasticsearch(
        "https://elasticsearch-master.elastic.svc.cluster.local:9200",
        basic_auth=("elastic", "elastic"),
        verify_certs=False
    )
    if es.ping():
        print("✅ Connected to Elasticsearch")
    else:
        print("❌ Failed to connect to Elasticsearch")
    return es


# Extracts video IDs from a list of search result items.
def extract_video_ids(search_items):
    return [
        item['id']['videoId']
        for item in search_items
        if item.get('id', {}).get('kind') == 'youtube#video' and 'videoId' in item['id']
    ]


# Log the search start and end date to Elasticsearch for tracking search history
def log_search_period_to_es(es, start_date, end_date, query=None, result_count=None, index="youtube-log"):
    doc = {
        "start_date": start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "timestamp": datetime.utcnow().isoformat()
    }
    if query:
        doc["query"] = query
    if result_count is not None:
        doc["result_count"] = result_count

    es.index(index=index, document=doc)


# Main entrypoint for Fission
def main():
    # get current time in ISO format
    now = datetime.now().isoformat()[1:19]

    # set default search start time
    search_start_date = "2025-01-01"

    # set api key
    api_key = load_api_key()
    youtube = build_youtube_client(api_key)

    # set log file path and es index name
    log_file = "search_log.txt"
    data_index = "youtube-videos-tariff"
    log_index = "youtube-videos-tariff-logs"

    # custom result number and prompt
    max_results = 2
    search_prompt = 'Trump tariff'

    # custom search date
    start_date = None
    end_date = None
    search_date_range = 1

    # get search start date and end date
    start_date, end_date = get_next_search_period(days=search_date_range)

    search_results = []
    video_ids = []
    video_statistics = []
    # get search video snippet
    for page_items in search_videos(youtube, max_results=50, query=search_prompt, start_date=start_date,
                                    end_date=end_date):
        search_results.extend(page_items)

        # Only extract IDs from this page
        ids_this_page = extract_video_ids(page_items)
        video_ids.extend(ids_this_page)

        # Fetch video details for this page's video IDs
        video_statistics.extend(get_video_details(youtube, ids_this_page))

    # Prepare output
    output = video_statistics

    # Connect and send data to ES
    try:
        es = connect_elasticsearch()
        send_to_elasticsearch(es, output, data_index)
    except Exception as e:
        print(f"❌ Error sending to Elasticsearch: {e}")

    # Record search period to ES log
    try:
        log_search_period_to_es(es, start_date, end_date, search_prompt, len(video_statistics), log_index,)
        print(f"📝 Logged search period to {log_index}")
    except Exception as e:
        print(f"❌ Failed to log search period: {e}")

    # # Write searched log
    # save_end_date(end_date)

    # return as JSON
    return "done"

# if __name__ == '__main__':
#     print(main())
