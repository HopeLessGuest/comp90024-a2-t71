from datetime import datetime, timedelta

now = datetime.now()
last_end = datetime.fromisoformat("2025-01-01") - timedelta(days=1)
print(last_end)