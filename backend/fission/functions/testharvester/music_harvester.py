import requests
import json
from datetime import datetime
from pytz import timezone
from flask import current_app
from elasticsearch import Elasticsearch

# --- API & Elasticsearch Configuration ---
LASTFM_API_KEY = 'e4d3f7baeccf311b70a1b3f1d2a8abf4'

ES_HOST = "https://elasticsearch-master.elastic:9200"
ES_USER = "elastic"
ES_PASS = "elastic"
ES_INDEX = "music_top_tracks_australia"

# --- Utility Functions ---
def get_melbourne_timestamp():
    mel_tz = timezone('Australia/Melbourne')
    return datetime.now(mel_tz).isoformat()

def get_top_tracks_australia(limit=50):
    URL = 'http://ws.audioscrobbler.com/2.0/'
    params = {
        'method': 'geo.getTopTracks',
        'country': 'Australia',
        'api_key': LASTFM_API_KEY,
        'format': 'json',
        'limit': limit
    }
    response = requests.get(URL, params=params)
    response.raise_for_status()
    data = response.json()
    timestamp = get_melbourne_timestamp()

    results = []
    for track in data.get('tracks', {}).get('track', []):
        results.append({
            'timestamp': timestamp,
            'track': track['name'],
            'artist': track['artist']['name'],
            'listeners': int(track['listeners'])
        })
    return results

# --- Main Entrypoint for Fission ---
def main():
    try:
        # Step 1: Get top tracks
        top_tracks = get_top_tracks_australia(limit=50)

        # Step 2: Connect to Elasticsearch
        es = Elasticsearch(
            hosts=[ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            verify_certs=False
        )

        # Step 3: Insert into Elasticsearch
        count = 0
        for record in top_tracks:
            try:
                es.index(index=ES_INDEX, document=record)
                count += 1
            except Exception as e:
                current_app.logger.error(f"Failed to insert record: {e}")

        current_app.logger.info(f"Successfully inserted {count} Last.fm records into Elasticsearch.")
        return json.dumps({
            "message": f"Last.fm harvest completed. Inserted {count} records.",
            "count": count
        })

    except Exception as e:
        current_app.logger.error(f"Unexpected error in Last.fm harvester: {e}")
        return json.dumps({
            "message": "Last.fm harvest failed.",
            "error": str(e)
        })
