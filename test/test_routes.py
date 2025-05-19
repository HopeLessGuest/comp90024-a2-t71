# Team 71
# Yifu Chen 1609437, Kexing Ma 1697372, Jiejun Xie 1418316, Xinhe Liu 1477404, Anqi Liao 1578312

import unittest
import requests

class TestFissionRoutes(unittest.TestCase):

    BASE_URL = "http://localhost:9090/api"  # 如果部署到远程服务，请修改为对应 IP 或域名

    def test_youtubelifeapi(self):
        """Test life video API route"""
        params = {
            "start": "2025-04-01",
            "end": "2025-04-10"
        }
        url = f"{self.BASE_URL}/youtubelifeapi"
        response = requests.get(url, params=params)
        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json())

    def test_youtubeelectapi(self):
        """Test election video API route"""
        params = {
            "start": "2024-01-01",
            "end": "2024-12-31"
        }
        url = f"{self.BASE_URL}/youtubeelectapi"
        response = requests.get(url, params=params)
        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.json())

    # 你可以继续添加更多路由的测试函数

if __name__ == "__main__":
    unittest.main()
