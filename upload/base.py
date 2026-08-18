from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Destination:
    type: str
    id: str
    name: str = ""
    extra: Optional[Dict[str, Any]] = None


@dataclass
class UploadResult:
    success: bool
    url: Optional[str] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


class UploadService(ABC):
    @abstractmethod
    def upload_image(self, image_bytes: bytes, filename: str = "screenshot.png") -> UploadResult:
        """
        Uploads image bytes to destination and returns UploadResult with attachment URL.
        """
        pass
