from flask import current_app
from textblob import TextBlob
from elasticsearch8 import Elasticsearch
import praw
import json

def main():
    try:
        # Initialize Reddit client
        current_app.logger.info(f'Try to link to reddit...')
        reddit = praw.Reddit(
            client_id="D50EO1FxPl71JVPLQLYpoA",
            client_secret="35s0GSR5htqiw4BOte7o2pv-mFZxMg",
            user_agent="rabbit-ccc2 by u/CliveChen01",
            username="CliveChen01",
            password="CYF_20010423"
        )
        # ElasticSearch setup
        # username & password = elastic
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic:9200"],
            basic_auth=("elastic", "elastic"),
            verify_certs=False,
            ssl_show_warn=False
        )

        # Define subreddits, keywords, and sort methods
        subreddits = [
            "australia", "australian", "AustralianPolitics",
            "AskAnAustralian", "AusLeftPolitics",
            "ausfinance", "brisbane", "melbourne", "Sydney",
            "worldnews", "politics", "news"
        ]
        keywords = [
            "election", "vote", "voter turnout",
            "by-election", "preference voting",
            "poll", "swing", "campaign", "debate",
            "Albanese", "Dutton", "Morrison", "Chalmers","Greens", "Labor"
            "policy", "platform",
            "climate change", "energy policy",
            "housing affordability", "cost of living",
            "healthcare access", "Medicare",
            "immigration", "border policy",
            "economy", "unemployment",
            "education", "school funding",
            "media bias", "broken promises",
            "political opportunism", "accountability"
        ]

        # Data container
        results = []

        # Reddit Harvest
        for sub in subreddits:
            current_app.logger.info(f"Searching r/{sub}...")
            for kw in keywords:
                current_app.logger.info(f"Searching {kw} in r/{sub} section...")
                try:
                    posts = reddit.subreddit(sub).search(
                        query=kw,
                        sort='new',
                        time_filter='all',
                        limit=None
                    )
                except Exception as e:
                    current_app.logger.warning(f"Failed searching {kw} in r/{sub} section: {e}")
                    continue

                for post in posts:
                    title = post.title or ""
                    selftext = post.selftext or ""
                    full_text = f"{title}. {selftext}"
                    sentiment = TextBlob(full_text).sentiment.polarity
                    post_data = {
                            'id': post.id,
                            'title': title,
                            "subreddit": sub,
                            'original_text': full_text,
                            'sentiment': sentiment,
                            'name': post.name,
                            'created_utc': post.created_utc
                    }

                    results.append(post_data)

                    # Insert into ElaticSearch
                    try:
                        es.index(
                            index="reddit_test", 
                            id=post_data['created_utc'],
                            document=post_data
                        )
                    except Exception as es_error:
                        current_app.logger.error(f"Failed to insert into Elasticsearch: {es_error}")
                    # Get comments
                    try:
                        current_app.logger.info(f"Getting comments from posts -- {kw} in r/{sub} section...")
                        post.comments.replace_more(limit=None)
                        for comment in post.comments.list():
                            comment_data = {
                                'post_id': post.id,
                                'post_title': title,
                                'comment_id': comment.id,
                                'comment_body': comment.body,
                                'comment_created_utc': comment.created_utc
                            }
                            es.index(
                                index="reddit_comments",
                                id=comment.id,
                                document=comment_data
                            )
                    except Exception as ce:
                        current_app.logger.error(f"Failed to fetch/index comments for post {post.id}: {ce}")

        # Summarize results
        current_app.logger.info(f"Successfully collected {len(results)} posts.")
        return json.dumps({
                "message": "Reddit harvest completed.",
                "count": len(results),
                "posts": results
        }, ensure_ascii=False)

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return json.dumps({
            "message": "Harvest failed.",
            "error": str(e)
        })

