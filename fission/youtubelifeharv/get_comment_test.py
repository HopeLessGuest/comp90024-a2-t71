from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


API_KEY = 'AIzaSyDj-BtQS5lNlUxTjNyUtTEAKJ7KsIfJj1w'
VIDEO_ID = 'BdFlHP3U2Bk'

def get_comments(video_id, api_key, max_results=100):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)

        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=max_results,
            textFormat='plainText'
        )

        response = request.execute()

        comments = []
        for item in response.get('items', []):
            snippet = item['snippet']['topLevelComment']['snippet']
            comment_text = snippet['textDisplay']
            author = snippet['authorDisplayName']
            like_count = snippet['likeCount']
            comments.append({
                'author': author,
                'text': comment_text,
                'likes': like_count
            })

        return comments

    except HttpError as e:
        print(f"[X] API Error: {e}")
        return []

# 示例运行
if __name__ == '__main__':
    comments = get_comments(VIDEO_ID, API_KEY)
    for i, c in enumerate(comments, 1):
        print(f"{i}. {c['author']} ({c['likes']} likes): {c['text']}")
