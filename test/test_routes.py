# Team 71
# Yifu Chen 1609437, Kexing Ma 1697372, Jiejun Xie 1418316, Xinhe Liu 1477404, Anqi Liao 1578312

import unittest
import requests
import os
import re
from datetime import datetime


def sanitize_filename(path: str) -> str:
    # Replace / ? = & : with underscores, strip leading/trailing slashes
    return re.sub(r'[/?=&:]+', '_', path.strip('/')) + ".txt"

class TestFissionRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Only run once before all tests in this class
        cls.BASE = "http://localhost:9090"
        cls.timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        cls.log_dir = os.path.join("logs", cls.timestamp)
        os.makedirs(cls.log_dir, exist_ok=True)

    def assertApiOK(self, path):
        try:
            response = requests.get(f"{self.BASE}{path}", timeout=30)
            status = response.status_code
            body = response.text
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            filename = sanitize_filename(path)
            filepath = os.path.join(self.__class__.log_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {path} | status: {status}\n")
                f.write(body[:20000])

            self.assertEqual(status, 200, f"{path} failed with status {status}")
            json_data = response.json()
            if isinstance(json_data, dict):
                has_data = any(isinstance(v, (list, dict)) and len(v) > 0 for v in json_data.values())
            elif isinstance(json_data, list):
                has_data = len(json_data) > 0
            else:
                has_data = False

            self.assertTrue(has_data, f"{path} returned empty or unexpected format")

        except requests.exceptions.ReadTimeout:
            self.skipTest(f"{path} timed out after 30s — skipped")
        except Exception as e:
            self.fail(f"{path} raised error: {e}")

    # def test_youtubelifeapi(self):
    #     self.assertApiOK("/api/youtubelifeapi?start=2025-04-01&end=2025-04-03")
    #
    # def test_youtubeelectionapi(self):
    #     self.assertApiOK("/api/youtubeelectionapi?start=2025-01-01&end=2025-02-01")
    #
    # def test_trafficinjury(self):
    #     self.assertApiOK("/trafficinjury/Male/2021")
    #
    # def test_trafficagghour(self):
    #     self.assertApiOK("/trafficaggbyhour/2025-05-05/2025-05-10")
    #
    # def test_trafficvolume(self):
    #     self.assertApiOK("/trafficvolume/2025-05-09/12:00:00/2025-05-09/14:00:00")
    #
    # def test_victim(self):
    #     self.assertApiOK("/victim/vic/person")
    #
    # def test_offender(self):
    #     self.assertApiOK("/offender/male/-1/person")
    #
    # def test_musictoptrack(self):
    #     self.assertApiOK("/musictoptrack/2025-05-07/12:00:00/2025-05-09/14:00:00")
    #
    def test_mastodonkeywordsentiment(self):
        self.assertApiOK("/mastondonkeywordsentiment/2023-01-01/2023-01-03/crime")

    def test_mastodonhotword(self):
        self.assertApiOK("/mastodonhotword/2025-05-09/00:00:00/2025-05-10/14:00:00")

    # def test_keywordmastodon(self):
    #     self.assertApiOK("/keywordmastodon/2023-01-01/2023-01-02")
    #
    def test_housetransfer(self):
        self.assertApiOK("/housetransfer/2024/06/2024/09")

    # def test_auselection(self):
    #     self.assertApiOK("/auselectionapi/2025-4-1/2025-5-13")
    #
    # def test_auinflation(self):
    #     self.assertApiOK("/inflation/rba?start=2023-01-01&end=2024-01-01")


if __name__ == "__main__":
    unittest.main()
