# API: YouTube Election Data

**Endpoint:** `/api/youtubeelectionapi`  
**Method:** `GET`  
**Description:**  
Retrieves YouTube videos related to elections, politics, or voting within a given date range from Elasticsearch index `youtube-videos-election`.

---

## Query Parameters

| Parameter | Type   | Required | Default Value  | Description                        |
|-----------|--------|----------|----------------|------------------------------------|
| `start`   | string | No       | `2024-01-01`   | Start date in format `YYYY-MM-DD` |
| `end`     | string | No       | today (UTC)    | End date in format `YYYY-MM-DD`   |

---

## Behavior When Parameters Are Missing

- If `start` is **not provided**, it defaults to **`2024-01-01`**
- If `end` is **not provided**, it defaults to **current UTC date**

---

## Response Example

```json
{
  "status": 200,
  "result_count": 8432,
  "data": [
    {
      "id": "xyz789",
      "snippet": {
        "title": "Australian Election Analysis 2025",
        "description": "...",
        "tags": ["election", "australia", "voting"],
        "publishedAt": "2025-04-12T09:00:00Z"
      },
      "statistics": {
        "viewCount": 30000,
        "likeCount": 1400,
        "commentCount": 250,
        "favoriteCount": 20
      }
    }
  ]
}