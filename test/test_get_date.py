# Team 71
# Yifu Chen 1609437, Kexing Ma 1697372, Jiejun Xie 1418316, Xinhe Liu 1477404, Anqi Liao 1578312

gifrom datetime import datetime, timedelta

now = datetime.now()
last_end = datetime.fromisoformat("2025-01-01") - timedelta(days=1)
print(last_end)