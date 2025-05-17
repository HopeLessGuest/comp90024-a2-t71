# API: YouTube Life Data

**Endpoint:** `/api/youtubelifeapi`  
**Method:** `GET`  
**Description:**  
Returns lifestyle-related YouTube video data (e.g., food, vlog, citywalk) within a specified date range from Elasticsearch index `youtube-videos-life`.

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
  "result_count": 10000,
  "data": [
    {
      "id": "abc123",
      "snippet": {
        "title": "Exploring Melbourne Food Markets",
        "description": "...",
        "tags": ["melbourne", "food", "vlog"],
        "publishedAt": "2025-05-01T01:00:00Z"
      },
      "statistics": {
        "viewCount": 12000,
        "likeCount": 500,
        "commentCount": 85,
        "favoriteCount": 10
      }
    }
  ]
}
