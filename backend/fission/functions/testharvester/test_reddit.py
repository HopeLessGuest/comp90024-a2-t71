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
            "australia open", "tennis", "jannik sinner", "alexander zverev", "carlos alcaraz",
            "taylor fritz", "daniil medvedev", "casper ruud", "novak djokovic", "alex de minaur",
            "andrey rublev", "grigor dimitrov", "stefanos tsitsipas", "tommy paul", "holger rune",
            "ugo humbert", "jack draper", "lorenzo musetti", "frances tiafoe", "hubert hurkacz",
            "karen khachanov", "arthur fils", "ben shelton", "sebastian korda", "alejandro tabilo",
            "jiri lehecka", "alexei popyrin", "tomas machac", "jordan thompson", "sebastian baez",
            "felix auger-aliassime", "giovanni mpetshi perricard", "francisco cerundolo",
            "flavio cobolli", "nick kyrgios", "kei nishikori", "pablo carreño busta", "reilly opelka",
            "jenson brooksby", "dominic stricker", "stan wawrinka", "omar jasika", "james mccabe",
            "li tu", "tristan schoolkate", "lucas pouille", "kasidit samrej", "nishesh basavareddy",
            "aryna sabalenka", "iga swiatek", "coco gauff", "jasmine paolini", "qinwen zheng",
            "elena rybakina", "jessica pegula", "emma navarro", "daria kasatkina", "danielle collins",
            "paula badosa", "diana shnaider", "anna kalinskaya", "mirra andreeva",
            "beatriz haddad maia", "jelena ostapenko", "marta kostyuk", "donna vekic", "madison keys",
            "karolina muchova", "victoria azarenka", "katie boulter", "magdalena frech",
            "yulia putintseva", "liudmila samsonova", "ekaterina alexandrova",
            "anastasia pavlyuchenkova", "elina svitolina", "linda noskova", "leylah fernandez",
            "maria sakkari", "dayana yastremska", "belinda bencic", "caty mcnally"
        ]

        subreddits = ['australia', 'tennis', 'sports', 'melbourne']
        results = []
        # translator = GoogleTranslator(source='auto', target='en')

        for sub in subreddits:
            current_app.logger.info(f"Searching r/{sub}...")

            try:
                posts = reddit.subreddit(sub).top(limit=100, time_filter='month')
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
