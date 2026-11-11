"""
Unit and Integration Test for Android APK Download Endpoint.
"""
import unittest
from fastapi.testclient import TestClient
from src.api.app import app

class TestApkDownloadEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_download_apk_success(self):
        response = self.client.get("/download/agrimind.apk")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("content-type"), "application/vnd.android.package-archive")
        self.assertIn("agrimind-debug.apk", response.headers.get("content-disposition", ""))
        self.assertGreater(len(response.content), 10_000_000)

if __name__ == "__main__":
    unittest.main()
