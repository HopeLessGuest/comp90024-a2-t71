from googleapiclient.discovery import build
from datetime import datetime
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
        raise FileNotFoundError(f"API key not found in {fission_path} or {filepath} or {secrets_path}")


# Build YouTube API client
def build_youtube_client(api_key):
    return build('youtube', 'v3', developerKey=api_key)


# Search videos
def search_videos(youtube, query, region='AU', max_results=20):
    response = youtube.search().list(
        part='snippet',
        q=query,
        type='video',
        regionCode=region,
        maxResults=max_results
    ).execute()
    return response


# Get video details
def get_video_details(youtube, video_ids):
    response = youtube.videos().list(
        part='snippet,statistics,contentDetails',
        id=','.join(video_ids)
    ).execute()
    return response


# Load the last recorded search date from the log file (ISO format)
def load_last_date(log_file="search_log.txt"):
    if Path(log_file).exists():
        with open(log_file, "r") as f:
            lines = f.read().strip().splitlines()
            if lines:
                return datetime.fromisoformat(lines[-1])
    return datetime.fromisoformat(START_DATE) - timedelta(days=1)


# Append the current search end date to the log file in ISO format
def save_end_date(log_file="search_log.txt", end_date):
    with open(log_file, "a") as f:
        f.write(end_date.date().isoformat() + "\n")


# Calculate the next search period based on the last recorded date
def get_next_search_period(days=7):
    last_end = load_last_date()
    start = last_end + timedelta(days=1)
    end = start + timedelta(days=days - 1)
    return start, end


# Main entrypoint for Fission
def main():
    # get current time in ISO format
    now = datetime.now().isoformat()[1:19]

    # set default search start time
    start_time = "2025-01-01"

    # set api key
    api_key = load_api_key()
    youtube = build_youtube_client(api_key)

    # set log file path
    log_file = "search_log.txt"

    # custom result number
    max_results = 2
    search_response = search_videos(youtube, query='Trump tariff', max_results=max_results)

    # Extract video IDs
    video_ids = [
        item['id']['videoId']
        for item in search_response['items']
        if item.get('id', {}).get('kind') == 'youtube#video' and 'videoId' in item['id']
    ]

    # Connect es
    # es = Elasticsearch(hosts=["http://localhost:9200"])
    # for item in search_response['items']:
    #     if item.get('id', {}).get('kind') == 'youtube#video':
    #         doc = {
    #             'videoId': item['id']['videoId'],
    #             'title': item['snippet']['title'],
    #             'publishedAt': item['snippet']['publishedAt'],
    #             'description': item['snippet'].get('description', ''),
    #             'channelTitle': item['snippet']['channelTitle']
    #         }
    #
    #         es.index(index='youtube-videos', document=doc)

    # Get video details
    video_statistics = get_video_details(youtube, video_ids)

    # Prepare output
    output = video_statistics

    # return as JSON
    return json.dumps(output, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    print(main())
