import json
from bs4 import BeautifulSoup
from tqdm import tqdm

# === CONFIGURATION ===
INPUT_FILE = "d:/Newfolder/mastodon_cleaned.ndjson"
OUTPUT_FILE = "d:/Newfolder/mastodon_neat.ndjson"
BATCH_SIZE = 1000

# Fields to keep
def extract_relevant_fields(doc):
    account = doc.get("account", {})
    return {
        "createdAt": doc.get("createdAt"),
        "content": strip_html(doc.get("content")),
        "sentiment": doc.get("sentiment"),
        "favouritesCount": doc.get("favouritesCount"),
        "tags": [tag.get("name") for tag in doc.get("tags", [])],
        "repliesCount": doc.get("repliesCount"),
        "account": {
            "fields": account.get("fields"),
            "followersCount": account.get("followersCount"),
            "username": account.get("username"),
            "acct": account.get("acct"),
            "followingCount": account.get("followingCount"),
            "displayName": account.get("displayName"),
            "note": strip_html(account.get("note")),
        },
        "language": doc.get("language"),
        "@timestamp": doc.get("@timestamp"),
    }

def strip_html(text):
    if not isinstance(text, str):
        return text
    return BeautifulSoup(text, "html.parser").get_text()

def process_file_streaming(input_path, output_path, batch_size=1000):
    buffer = []
    total_processed = 0

    with open(input_path, "r", encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
        lines = iter(infile)
        for index_line in tqdm(lines, desc="Processing lines", unit=" lines"):
            try:
                doc_line = next(lines)  # Corresponding doc line
                index_obj = json.loads(index_line)
                doc_obj = json.loads(doc_line)

                if "doc" in doc_obj:
                    cleaned_doc = extract_relevant_fields(doc_obj["doc"])
                    buffer.append(json.dumps(index_obj) + "\n")
                    buffer.append(json.dumps({"doc": cleaned_doc}) + "\n")
                    total_processed += 1

                if len(buffer) >= 2 * batch_size:
                    outfile.writelines(buffer)
                    buffer.clear()

            except Exception as e:
                print("Skipping malformed pair:", e)

        if buffer:
            outfile.writelines(buffer)

    print(f"\n✅ Done. Total documents processed: {total_processed}")
    print(f"✅ Output written to: {output_path}")

# Run
process_file_streaming(INPUT_FILE, OUTPUT_FILE, batch_size=BATCH_SIZE)
