from flask import current_app, request
from mastodon import Mastodon
from bs4 import BeautifulSoup
from textblob import TextBlob
from elasticsearch import Elasticsearch
import json

# Keywords to track
keywords = [
    "congestion", "traffic", "freeway", "traffic jam", "heavy traffic", "slow traffic",
    "stuck in traffic", "accident", "crash", "roadwork", "road closure", "lane closure",
    "detour", "road construction", "delay", "running late", "took forever", "took ages",
    "late to work", "peak hour", "rush hour", "morning traffic", "evening traffic", "highway"
]

def html_to_text(html):
    return BeautifulSoup(html, "html.parser").get_text()

def get_sentiment(text):
    return TextBlob(text).sentiment.polarity  # range: [-1.0, 1.0]

def get_matching_keywords(text, keywords):
    text_lower = text.lower() if text else ""
    return [kw for kw in keywords if kw.lower() in text_lower]

def main():
    """Main entrypoint for Fission function"""
    try:
        # Connect to Mastodon
        mastodon = Mastodon(
            access_token='MxI5hBw-a0vz7HjNeRXEqv7cDnAx6o8hqLlE_Qs3YVE',
            api_base_url='https://aus.social'
        )

        # Connect to ElasticSearch
        es = Elasticsearch(
            hosts=["https://elasticsearch-master.elastic:9200"],
            basic_auth=("elastic", "elastic"),
            verify_certs=False   
        )

        index_name = "mastodon_posts"  

        cleaned = []
        max_pages = 5  # Reduce pages for function speed
        max_id = None

        for _ in range(max_pages):
            try:
                toots = mastodon.timeline_public(limit=50, max_id=max_id)
            except Exception as e:
                current_app.logger.error(f"API error: {e}")
                break

            if not toots:
                break

            for toot in toots:
                raw_text = html_to_text(toot.get("content", ""))
                matched_keywords = get_matching_keywords(raw_text, keywords)

                if matched_keywords:
                    post_data = {
                        "id": toot.get("id"),
                        "created_at": str(toot.get("created_at")),
                        "original_content": raw_text,
                        "account": {
                            "username": toot.get("account", {}).get("username", "")
                        },
                        "sentiment": get_sentiment(raw_text),
                        "matched_keywords": matched_keywords
                    }

                    # Append to list
                    cleaned.append(post_data)

                    # Insert into ElasticSearch
                    try:
                        es.index(index=index_name, document=post_data)
                    except Exception as es_error:
                        current_app.logger.error(f"Failed to insert into Elasticsearch: {es_error}")

            max_id = toots[-1]["id"]

        current_app.logger.info(f"Successfully harvested {len(cleaned)} posts.")

        return json.dumps({
            "message": "Harvest completed.",
            "count": len(cleaned),
            "posts": cleaned
        }, ensure_ascii=False)

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return json.dumps({
            "message": "Harvest failed.",
            "error": str(e)
        })
