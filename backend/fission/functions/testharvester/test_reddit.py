from flask import current_app, request
# from deep_translator import GoogleTranslator
from textblob import TextBlob
from elasticsearch import Elasticsearch
import praw
import json

def main():
    """Main entrypoint for Fission function: Harvest Reddit posts with sentiment analysis and store in Elasticsearch."""
    try:
        # Reddit API setup
        reddit = praw.Reddit(
            client_id='y4guG7yMRMDMlDG0dAPIfw',
            client_secret='0HCylFphxkIuqb0E7KZFzzavraCEig',
            user_agent='script:sentiment_analysis:v1.0 (by u/Severe-Strength1175)'
        )

        # ElasticSearch setup
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic:9200"],
            basic_auth=("elastic", "elastic"),
            verify_certs=False   
        )
        index_name = "reddit_posts"

        keywords = [
        "melbourne travel", "sydney trip", "brisbane visit", "adelaide guide", "perth recommendations", 
        "tasmania road trip", "cairns itinerary", "darwin travel tips", "hobart travel", "gold coast activities",
        "australia travel", "australia backpacking", "australia itinerary", "australia travel tips", "australia travel guide",
        "things to do in melbourne", "must visit in sydney", "great ocean road tour", 
        "blue mountains hike", "phillip island penguins", "bondi beach surfing", 
        "best hikes australia", "weekend trips from melbourne", "day trips near sydney",
        "where to go in australia", "underrated places australia", "hidden gems australia",
        "best coffee melbourne", "melbourne brunch spots", "cheap eats sydney", 
        "top restaurants brisbane", "seafood in tasmania", "farmers market australia", 
        "food in chinatown melbourne", "best dumplings melbourne", "australian snacks to try", 
        "food trucks in sydney", "night markets melbourne", "what to eat in australia",
        "how to use myki", "public transport melbourne", "sydney metro vs bus", 
        "tram not coming", "bike rental melbourne", "car rental australia",
        "uber in brisbane", "is myki worth it", "australia driving tips", 
        "interstate trains australia", "airport to city transport", "how bad is traffic in sydney",
        "is melbourne worth visiting", "traveling solo in australia", 
        "best time to visit australia", "australia travel budget", "backpacking australia", 
        "tips for road trips", "how safe is australia", "australia travel scams", 
        "how many days in sydney", "should I visit cairns or gold coast", "best time to visit melbourne",
        "van life australia", "working holiday visa", "australia hostels", 
        "wifi in australia", "australia travel sim card", "melbourne reddit meetup", 
        "australia vs new zealand travel", "travel photography australia", 
        "nature photography spots", "sunset point australia", "best beaches in australia"
        ]

        subreddits = ['australia', 'melbourne', 'sydney', 'brisbane', 'perth', 'adelaide', 'canberra', 'goldcoast', 'foodmelbourne',  'melbournefood', 'melbournetrains', 'melbournecycling', 'Geelong', 'Ballarat', 'Bendigo', 'Wodonga', 'unimelb', 'Monash']
        results = []
        # translator = GoogleTranslator(source='auto', target='en')

        for sub in subreddits:
            current_app.logger.info(f"Searching r/{sub}...")

            try:
                posts = reddit.subreddit(sub).top(limit=100, time_filter='day')
            except Exception as e:
                current_app.logger.warning(f"Failed to fetch from {sub}: {e}")
                continue

            for post in posts:
                title = post.title or ""
                selftext = post.selftext or ""
                full_text = f"{title}. {selftext}"

                # try:
                #     translated = translator.translate(full_text)
                # except Exception as e:
                #     current_app.logger.warning(f"Translation failed for post {post.id}: {e}")
                #     continue

                # if not translated or not any(k in translated.lower() for k in keywords):
                #     continue

                sentiment = TextBlob(full_text).sentiment.polarity

                post_data = {
                    'id': post.id,
                    'title': title,
                    # 'translated': translated,
                    'original_text': full_text,
                    'sentiment': sentiment,
                    'url': post.url,
                    'created_utc': post.created_utc,
                    'subreddit': post.subreddit.display_name
                }

                # Append to results
                results.append(post_data)

                # Insert into ElasticSearch
                try:
                    es.index(index=index_name, document=post_data)
                except Exception as es_error:
                    current_app.logger.error(f"Failed to insert into Elasticsearch: {es_error}")

        current_app.logger.info(f"Successfully collected {len(results)} posts.")

        return json.dumps({
            "message": "Harvest completed.",
            "count": len(results),
            "posts": results
        }, ensure_ascii=False)

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return json.dumps({
            "message": "Harvest failed.",
            "error": str(e)
        })
