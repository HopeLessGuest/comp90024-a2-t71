from googleapiclient.discovery import build
import json

API_KEY = 'AIzaSyBbDw8fz5hE2bIQSZY-vlhSz2bTGoiwGTg'
youtube = build('youtube', 'v3', developerKey=API_KEY)


search_response = youtube.search().list(
    part='snippet',
    q='Melbourne',
    type='video',
    maxResults=5
).execute()

video_ids = [item['id']['videoId'] for item in search_response['items']]


video_response = youtube.videos().list(
    part='snippet,statistics,contentDetails',
    id=','.join(video_ids)
).execute()

video_statistics = youtube.videos().list(
    part='statistics,snippet',
    id=','.join(video_ids)
).execute()



with open('youtube_video_data.json', 'w', encoding='utf-8') as f:
    json.dump(search_response, f, ensure_ascii=False, indent=2)

with open('youtube_video_detail.json', 'w', encoding='utf-8') as f:
    json.dump(video_statistics, f, ensure_ascii=False, indent=2)