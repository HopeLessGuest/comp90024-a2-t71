import tweepy
import json
import os

BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "AAAAAAAAAAAAAAAAAAAAAEQZ0wEAAAAAGCYQlufJzfJGEVOWdYsR%2BvJxkFw%3DiRkWJ4Bn7USKzYTu7mb95YSnx5AqJEuK43ELHshioVpGN60Sel")

# Initialize Twitter client using Tweepy
client = tweepy.Client(bearer_token=BEARER_TOKEN)

# Define search query
query = "Trump Australia -is:retweet lang:en"

# Request 100 recent tweets
response = client.search_recent_tweets(
    query=query,
    max_results=50,
    tweet_fields=["id", "text", "created_at", "lang", "author_id"]
)

# Extract tweet data from response
tweets = [tweet.data for tweet in response.data or []]

# Write tweets to a JSON file
with open('twitter_data.json', "w", encoding="utf-8") as f:
    json.dump(tweets, f, ensure_ascii=False, indent=2)

print(f"{len(tweets)} tweets Saved")
