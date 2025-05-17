from googleapiclient.discovery import build
from youtube_helper import *

# Hardcoded YouTube API key
API_KEY = 'AIzaSyAe4U7EGjlauzCwu-6Sj-Nxf1wEz8lSBpQ'

# Create YouTube API client
youtube = build('youtube', 'v3', developerKey=API_KEY)

# Fixed query parameters
query = "Australia election"
start_date = "2009-01-01T00:00:00Z"
end_date = "2009-06-30T23:59:59Z"
region = "AU"

# Search settings
max_results = 50         # Maximum allowed per page
max_pages = 10           # Up to 500 results total
all_items = []
next_page_token = None

# Fetch up to 500 videos using pagination
request = youtube.search().list(
    part="snippet",
    q=query,
    type="video",
    regionCode=region,
    publishedAfter=start_date,
    publishedBefore=end_date,
    maxResults=max_results,
    pageToken=next_page_token
)
response = request.execute()
total = response.get("pageInfo", {}).get("totalResults", 0)
# Get approximate total result count (may exceed 500)
estimated_total = response.get("pageInfo", {}).get("totalResults", 0)

# Print summary
print(f"📊 Estimated total results: {total}")

