from googleapiclient.discovery import build
from datetime import datetime
import json
from elasticsearch import Elasticsearch

# Helper function: Load API Key
def load_api_key(filepath='.secrets/youtube_api_key.txt'):
    with open(filepath, 'r') as f:
        return f.read().strip()


# Helper function: Build YouTube API client
def build_youtube_client(api_key):
    return build('youtube', 'v3', developerKey=api_key)


# Helper function: Search videos
def search_videos(youtube, query, region='AU', max_results=5):
    response = youtube.search().list(
        part='snippet',
        q=query,
        type='video',
        regionCode=region,
        maxResults=max_results
    ).execute()
    return response


# Helper function: Get video details
def get_video_details(youtube, video_ids):
    response = youtube.videos().list(
        part='snippet,statistics,contentDetails',
        id=','.join(video_ids)
    ).execute()
    return response


# Main entrypoint for Fission
def main():
    #api_key = load_api_key()
    api_key = "AIzaSyBbDw8fz5hE2bIQSZY-vlhSz2bTGoiwGTg"
    youtube = build_youtube_client(api_key)

    search_response = search_videos(youtube, query='Trump tariff')

    # Extract video IDs
    video_ids = [
        item['id']['videoId']
        for item in search_response['items']
        if item.get('id', {}).get('kind') == 'youtube#video' and 'videoId' in item['id']
    ]

    # Get video details
    video_statistics = get_video_details(youtube, video_ids)

    # Prepare output
    output = search_response
    # output = {
    #     'search_response': search_response,
    #     'video_statistics': video_statistics
    # }

    # return as JSON
    return json.dumps(output, ensure_ascii=False, indent=2)

# if __name__ == '__main__':
#     print(main(None))
