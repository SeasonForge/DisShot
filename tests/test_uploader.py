import unittest
from unittest.mock import patch, MagicMock
import requests

from discord.uploader import DiscordUploader
from upload.base import UploadResult


class TestDiscordUploader(unittest.TestCase):
    def setUp(self):
        self.webhook_url = "https://discord.com/api/webhooks/123/token_abc"
        self.uploader = DiscordUploader(self.webhook_url)
        self.sample_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

    @patch("requests.post")
    def test_upload_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "111222333",
            "attachments": [
                {
                    "id": "444555",
                    "filename": "screenshot.png",
                    "size": 1234,
                    "url": "https://cdn.discordapp.com/attachments/111/222/screenshot.png",
                    "proxy_url": "https://media.discordapp.net/attachments/111/222/screenshot.png"
                }
            ]
        }
        mock_post.return_value = mock_response

        result = self.uploader.upload_image(self.sample_bytes)

        self.assertTrue(result.success)
        self.assertEqual(result.url, "https://cdn.discordapp.com/attachments/111/222/screenshot.png")
        self.assertIsNone(result.error_message)
        self.assertEqual(result.status_code, 200)

    @patch("requests.post")
    def test_upload_404_not_found(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_post.return_value = mock_response

        result = self.uploader.upload_image(self.sample_bytes)

        self.assertFalse(result.success)
        self.assertIn("not found", result.error_message.lower())

    @patch("requests.post")
    def test_upload_429_rate_limit(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_post.return_value = mock_response

        result = self.uploader.upload_image(self.sample_bytes)

        self.assertFalse(result.success)
        self.assertIn("rate limit", result.error_message.lower())

    @patch("requests.post")
    def test_upload_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        result = self.uploader.upload_image(self.sample_bytes)

        self.assertFalse(result.success)
        self.assertIn("timed out", result.error_message.lower())

    def test_empty_bytes(self):
        result = self.uploader.upload_image(b"")
        self.assertFalse(result.success)
        self.assertIn("empty", result.error_message.lower())

    def test_empty_webhook(self):
        empty_uploader = DiscordUploader("")
        result = empty_uploader.upload_image(self.sample_bytes)
        self.assertFalse(result.success)
        self.assertIn("not configured", result.error_message.lower())


if __name__ == "__main__":
    unittest.main()
