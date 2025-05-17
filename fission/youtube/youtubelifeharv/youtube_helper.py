from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from datetime import timedelta
from es_helper import get_latest_date
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


# Extracts video IDs from a list of search result items.
def extract_video_ids(search_items):
    return [
        item['id']['videoId']
        for item in search_items
        if item.get('id', {}).get('kind') == 'youtube#video' and 'videoId' in item['id']
    ]


def collect_video_statistics_by_day(youtube, search_prompt, start_date, end_date, max_pages=10):
    """
    Perform daily YouTube searches over a date range and collect video metadata.
    Returns tuple: (search_results, video_ids, video_statistics) where:
                - search_results is a list of raw search result items,
                - video_ids is a list of video ID strings,
                - video_statistics is a list of full video detail dicts.
    """
    search_results = []
    video_ids = []
    video_statistics = []

    current_date = start_date
    while current_date <= end_date:
        next_date = current_date + timedelta(days=1)

        try:
            for page_items in search_videos(
                    youtube,
                    max_results=50,
                    query=search_prompt,
                    start_date=current_date,
                    end_date=next_date,
                    max_pages=max_pages
                      ):
                search_results.extend(page_items)

                ids_this_page = extract_video_ids(page_items)
                video_ids.extend(ids_this_page)
                video_details = get_video_details(youtube, ids_this_page)

                # add search_prompt to each detail item
                for video in video_details:
                    video['search_prompt'] = search_prompt
                video_statistics.extend(video_details)

        except HttpError as e:
            # Catch YouTube quota error
            if e.resp.status == 403 and 'quotaExceeded' in str(e):
                raise RuntimeError(f"QuotaExceeded for keyword '{search_prompt}' on {current_date.date()}") from e
            else:
                raise RuntimeError(f"Unexpected YouTube API error during search for '{search_prompt}' on {current_date.date()}: {str(e)}") from e
        current_date = next_date

    return search_results, video_ids, video_statistics

# Get the date search range for YouTube search (default: 7 days)
def get_next_search_period(es, log_index, search_range=7):
    start_date = get_latest_date(es, log_index) + timedelta(days=1)
    end_date = start_date + timedelta(days=search_range - 1)
    print(f"[Search Period] Start: {start_date.date()}, End: {end_date.date()}")
    return start_date, end_date