from flask import current_app
from textblob import TextBlob
from elasticsearch import Elasticsearch
import praw
import json
import time

def main():
    try:
        # --- Reddit API ---
        reddit = praw.Reddit(
            client_id='y4guG7yMRMDMlDG0dAPIfw',
            client_secret='0HCylFphxkIuqb0E7KZFzzavraCEig',
            user_agent='script:sentiment_analysis:v1.0 (by u/Severe-Strength1175)'
        )

        # --- Elasticsearch ---
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic:9200"],
            basic_auth=("elastic", "elastic"),
            verify_certs=False
        )
        index_name = "transportation_reddit_posts"

        keywords = [
            "congestion", "traffic", "freeway", "traffic jam", "heavy traffic", "slow traffic",
            "stuck in traffic", "accident", "crash", "roadwork", "road closure", "lane closure",
            "detour", "road construction", "delay", "running late", "took forever", "took ages",
            "late to work", "peak hour", "rush hour", "morning traffic", "evening traffic", "highway"
        ]
        subreddits = [
            "melbourne", "australia", "melbournefood", "victoriajustice", "melbournetrains", "melbournetrains", "melbournecycling",
            "Geelong", "Ballarat", "Bendigo", "Wodonga", "unimelb", "Monash"
        ]

        results = []
        for sub in subreddits:
            current_app.logger.info(f"Searching r/{sub}...")
            try:
                posts = reddit.subreddit(sub).search(
                    query=" OR ".join(keywords),
                    limit=100,
                    sort="new",
                    time_filter="hour"
                )
            except Exception as e:
                current_app.logger.warning(f"Failed to fetch from {sub}: {e}")
                continue

            for post in posts:
                title = post.title or ""
                selftext = post.selftext or ""
                full_text = f"{title}. {selftext}"

                if not any(k in full_text.lower() for k in keywords):
                    continue  # skip irrelevant posts

                sentiment = TextBlob(full_text).sentiment.polarity

                post_data = {
                    'id': post.id,
                    'title': title,
                    'original_text': full_text,
                    'sentiment': sentiment,
                    'url': post.url,
                    'created_utc': post.created_utc,
                    'created_time': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(post.created_utc)),
                    'subreddit': post.subreddit.display_name
                }

                results.append(post_data)

                try:
                    es.index(index=index_name, document=post_data)
                except Exception as es_error:
                    current_app.logger.error(f"ES insert failed: {es_error}")

        current_app.logger.info(f"Collected {len(results)} posts.")
        return json.dumps({
            "message": "Harvest completed.",
            "count": len(results)
        }, ensure_ascii=False)

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return json.dumps({
            "message": "Harvest failed.",
            "error": str(e)
        })
