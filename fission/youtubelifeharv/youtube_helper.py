from googleapiclient.discovery import build
import os
from datetime import timedelta

# Load API Key
def load_api_key(filepath='youtube_api_key.txt'):
    zip_path = '/userfunc/deployarchive/youtube_api_key.txt'
    secrets_path = '/secrets/youtube-api-key'
    local_path = filepath

    if os.path.exists(secrets_path):
        print(f"[OK] Using secret path: {secrets_path}")
        with open(secrets_path, 'r') as f:
            return f.read().strip()
    elif os.path.exists(zip_path):
        print(f"[OK] Using zip path: {zip_path}")
        with open(zip_path, 'r') as f:
            return f.read().strip()
    elif os.path.exists(local_path):
        print(f"[OK] Using local path: {local_path}")
        with open(local_path, 'r') as f:
            return f.read().strip()
    else:
        raise FileNotFoundError(f"API key not found in {zip_path} or {filepath} or {secrets_path}")

# Build YouTube API client
def build_youtube_client(api_key):
    return build('youtube', 'v3', developerKey=api_key)

# Search for YouTube videos with optional date range and pagination
def search_videos(youtube, query, region='AU', max_results=50, start_date=None, end_date=None, max_pages=None):
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

    print(f'[Searching from time period]: {start_date.isoformat("T") + "Z"} to {end_date.isoformat("T") + "Z"}')
    next_page_token = None
    page_count = 0

    while True:
        if next_page_token:
            search_params['pageToken'] = next_page_token

        response = youtube.search().list(**search_params).execute()
        items = response.get('items', [])
        yield items

        page_count += 1
        if max_pages is not None and page_count >= max_pages:
            break

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

# Get detailed info for a list of video IDs
def get_video_details(youtube, video_ids):
    response = youtube.videos().list(
        part='snippet,statistics,contentDetails',
        id=','.join(video_ids)
    ).execute()
    return response.get("items", [])
