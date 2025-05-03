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
def search_videos(youtube, query, region='AU', max_results=20, start_date=None, end_date=None):
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

    response = youtube.search().list(**search_params).execute()
    return response


# Get video details
def get_video_details(youtube, video_ids):
    response = youtube.videos().list(
        part='snippet,statistics,contentDetails',
        id=','.join(video_ids)
    ).execute()
    return response


# Load the last recorded search date from the log file (ISO format)
def load_last_date(log_file="search_log.txt", search_start_date="2025-01-01"):
    if Path(log_file).exists():
        with open(log_file, "r") as f:
            lines = f.read().strip().splitlines()
            if lines:
                return datetime.fromisoformat(lines[-1])
    return datetime.fromisoformat(search_start_date) - timedelta(days=1)


# Append the current search end date to the log file in ISO format
def save_end_date(end_date, log_file="search_log.txt"):
    with open(log_file, "a") as f:
        f.write(end_date.date().isoformat() + "\n")


# Get the next date range for YouTube search (default: 7 days)
def get_next_search_period(days=7):
    last_end = load_last_date()
    start = last_end + timedelta(days=1)
    end = start + timedelta(days=days - 1)
    print(f"[Search Period] Start: {start.isoformat()}, End: {end.isoformat()}")
    return start, end


# Send data to Elastic Search
def send_to_elasticsearch(es, items, index="youtube-videos"):
    for item in items:
        video_id = item.get("id")
        if video_id:
            es.index(index=index, id=video_id, document=item)


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


# Main entrypoint for Fission
def main():
    # get current time in ISO format
    now = datetime.now().isoformat()[1:19]

    # set default search start time
    search_start_date = "2025-01-01"

    # set api key
    api_key = load_api_key()
    youtube = build_youtube_client(api_key)

    # set log file path
    log_file = "search_log.txt"

    # custom result number and prompt
    max_results = 2
    search_prompt = 'Trump tariff'

    # custom search date
    start_date, end_date = get_next_search_period()
    search_response = search_videos(youtube, max_results=max_results, query="interest rates", start_date=start_date,
                                    end_date=end_date)

    # Extract video IDs
    video_ids = [
        item['id']['videoId']
        for item in search_response['items']
        if item.get('id', {}).get('kind') == 'youtube#video' and 'videoId' in item['id']
    ]

    # Get video details
    video_statistics = get_video_details(youtube, video_ids)

    # Prepare output
    output = video_statistics.get("items", [])

    es = connect_elasticsearch()
    send_to_elasticsearch(es, output)

    # Write searched log
    save_end_date(end_date)

    # return as JSON
    return json.dumps(output, ensure_ascii=False, indent=2)


# if __name__ == '__main__':
#     print(main())
