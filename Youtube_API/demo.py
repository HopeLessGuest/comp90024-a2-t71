from googleapiclient.discovery import build
from datetime import datetime
import json

API_KEY = 'AIzaSyBbDw8fz5hE2bIQSZY-vlhSz2bTGoiwGTg'
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Get today's date in YYYYMMDD format
date_str = datetime.now().strftime('%Y%m%d_%H%M')

search_response = youtube.search().list(
    part='snippet',
    q='Trump tariff',
    type='video',
    regionCode='AU',
    maxResults=100
).execute()

video_ids = [
    item['id']['videoId']
    for item in search_response['items']
    if item.get('id', {}).get('kind') == 'youtube#video' and 'videoId' in item['id']
]

video_response = youtube.videos().list(
    part='snippet,statistics,contentDetails',
    id=','.join(video_ids)
).execute()

video_statistics = youtube.videos().list(
    part='statistics,snippet',
    id=','.join(video_ids)
).execute()

# save data to files
with open(f'youtube_video_search_data_{date_str}.json', 'w', encoding='utf-8') as f:
    json.dump(search_response, f, ensure_ascii=False, indent=2)

with open(f'youtube_video_detail_{date_str}.json', 'w', encoding='utf-8') as f:
    json.dump(video_statistics, f, ensure_ascii=False, indent=2)