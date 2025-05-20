from flask import current_app
from elasticsearch import Elasticsearch
import urllib.request
import json

# Elasticsearch configuration
ES_HOST = "https://elasticsearch-master.elastic:9200"
ES_USER = "elastic"
ES_PASS = "elastic"
ES_INDEX = "transportation_volume_real_time"

# VicRoads API endpoint
VICROADS_API_URL = "https://data-exchange-api.vicroads.vic.gov.au/bluetooth_data/links_geometry"

def simplify_record(item):
    """Extract and simplify the relevant fields from a full record"""
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "length": item.get("length"),
        "min_number_of_lanes": item.get("min_number_of_lanes"),
        "minimum_tt": item.get("minimum_tt"),
        "average_coord": item.get("coordinates", []),
        "latest_stats": item.get("latest_stats", {})
    }

def main():
    """Main entrypoint for the Fission function to fetch VicRoads data and store it in Elasticsearch"""

    try:
        # Step 1: Fetch data from the public VicRoads API
        headers = {
            'Cache-Control': 'no-cache',
            'Ocp-Apim-Subscription-Key': 'd57463ba28da4b07a6375c3b7ac80cd6',
            'User-Agent': 'Mozilla/5.0'
        }
        req = urllib.request.Request(VICROADS_API_URL, headers=headers)
        req.get_method = lambda: 'GET'

        with urllib.request.urlopen(req) as response:
            raw_data = response.read().decode('utf-8')
            json_data = json.loads(raw_data)

        # Step 2: Simplify and filter records with valid 'latest_stats'
        simplified = [simplify_record(record) for record in json_data if record.get("latest_stats")]

        # Step 3: Connect to Elasticsearch with basic authentication (insecure certs ignored)
        es = Elasticsearch(
            hosts=[ES_HOST],
            basic_auth=(ES_USER, ES_PASS),
            verify_certs=False
        )

        # Step 4: Index the cleaned documents into Elasticsearch
        count = 0
        for record in simplified:
            try:
                es.index(index=ES_INDEX, document=record)
                count += 1
            except Exception as es_err:
                current_app.logger.error(f"Failed to insert document {record.get('id')}: {es_err}")

        current_app.logger.info(f"Successfully ingested {count} records into {ES_INDEX}.")

        return json.dumps({
            "message": "Bluetooth data harvest completed.",
            "count": count
        })

    except Exception as e:
        current_app.logger.error(f"Unexpected error: {e}")
        return json.dumps({
            "message": "Harvest failed.",
            "error": str(e)
        })
