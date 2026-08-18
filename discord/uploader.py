import logging
import requests
from typing import Optional

from upload.base import UploadService, UploadResult

logger = logging.getLogger(__name__)


class DiscordUploader(UploadService):
    """
    Uploads screenshots to a Discord incoming webhook endpoint and retrieves attachment URL.
    """
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url.strip()

    def upload_image(self, image_bytes: bytes, filename: str = "screenshot.png") -> UploadResult:
        if not self.webhook_url:
            return UploadResult(
                success=False,
                error_message="Discord destination is not configured."
            )

        if not image_bytes:
            return UploadResult(
                success=False,
                error_message="Captured image data is empty."
            )

        # Discord webhook endpoint with wait=true returns the created message JSON with attachments
        upload_endpoint = self.webhook_url
        if "wait=true" not in upload_endpoint:
            separator = "&" if "?" in upload_endpoint else "?"
            upload_endpoint = f"{upload_endpoint}{separator}wait=true"

        files = {
            "files[0]": (filename, image_bytes, "image/png")
        }

        try:
            logger.info("Uploading %d bytes to Discord webhook...", len(image_bytes))
            response = requests.post(
                upload_endpoint,
                files=files,
                timeout=15
            )

            if response.status_code in (200, 201):
                data = response.json()
                attachments = data.get("attachments", [])
                if attachments and "url" in attachments[0]:
                    url = attachments[0]["url"]
                    logger.info("Upload successful! URL: %s", url)
                    return UploadResult(
                        success=True,
                        url=url,
                        status_code=response.status_code,
                        extra=data
                    )
                else:
                    return UploadResult(
                        success=False,
                        error_message="Discord response did not contain an attachment URL.",
                        status_code=response.status_code
                    )

            elif response.status_code == 404:
                return UploadResult(
                    success=False,
                    error_message="Discord webhook was not found. Please reconnect Discord.",
                    status_code=response.status_code
                )
            elif response.status_code == 401 or response.status_code == 403:
                return UploadResult(
                    success=False,
                    error_message="Discord webhook authorization failed. Please reconnect Discord.",
                    status_code=response.status_code
                )
            elif response.status_code == 429:
                return UploadResult(
                    success=False,
                    error_message="Discord rate limit reached. Please try again in a few seconds.",
                    status_code=response.status_code
                )
            else:
                logger.error("Discord upload returned %d: %s", response.status_code, response.text)
                return UploadResult(
                    success=False,
                    error_message=f"Discord upload failed (HTTP {response.status_code}).",
                    status_code=response.status_code
                )

        except requests.exceptions.Timeout:
            logger.error("Discord upload timed out.")
            return UploadResult(
                success=False,
                error_message="Connection timed out while uploading to Discord."
            )
        except requests.exceptions.RequestException as e:
            logger.error("Network error during Discord upload: %s", e)
            return UploadResult(
                success=False,
                error_message=f"Network error: {e}"
            )
        except Exception as e:
            logger.error("Unexpected error during Discord upload: %s", e)
            return UploadResult(
                success=False,
                error_message=f"Unexpected error: {e}"
            )
