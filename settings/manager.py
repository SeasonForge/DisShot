import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Dict, Any

from config import (
    CONFIG_PATH,
    DEFAULT_HOTKEY,
    DEFAULT_DISCORD_CLIENT_ID,
    DEFAULT_DISCORD_CLIENT_SECRET,
    DEFAULT_LOCAL_STORAGE_DIR,
)
from settings.secure_store import encrypt_string, decrypt_string

logger = logging.getLogger(__name__)


@dataclass
class DiscordDestinationConfig:
    type: str = "discord"
    guild_id: str = ""
    guild_name: str = ""
    channel_id: str = ""
    channel_name: str = ""
    webhook_id: str = ""
    # Encrypted fields in json, decrypted in memory
    webhook_url: str = ""
    webhook_token: str = ""


@dataclass
class AppConfig:
    hotkey: str = DEFAULT_HOTKEY
    discord_client_id: str = DEFAULT_DISCORD_CLIENT_ID
    discord_client_secret: str = DEFAULT_DISCORD_CLIENT_SECRET  # encrypted in file
    destination: Optional[DiscordDestinationConfig] = None
    notifications_enabled: bool = True
    play_sound: bool = True
    start_with_windows: bool = False
    save_local_copy: bool = False
    local_copy_dir: str = DEFAULT_LOCAL_STORAGE_DIR
    language: str = "system"


class SettingsManager:
    def __init__(self, config_path: Path = CONFIG_PATH):
        self.config_path = config_path
        self.config = AppConfig()
        self.load()

    def load(self) -> AppConfig:
        if not self.config_path.exists() or self.config_path.stat().st_size == 0:
            self.config = AppConfig()
            self.save()
            return self.config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            dest_data = raw.get("destination")
            destination = None
            if dest_data:
                destination = DiscordDestinationConfig(
                    type=dest_data.get("type", "discord"),
                    guild_id=dest_data.get("guild_id", ""),
                    guild_name=dest_data.get("guild_name", ""),
                    channel_id=dest_data.get("channel_id", ""),
                    channel_name=dest_data.get("channel_name", ""),
                    webhook_id=dest_data.get("webhook_id", ""),
                    webhook_url=decrypt_string(dest_data.get("webhook_url_enc", "")),
                    webhook_token=decrypt_string(dest_data.get("webhook_token_enc", "")),
                )

            loaded_client_id = raw.get("discord_client_id", DEFAULT_DISCORD_CLIENT_ID)
            if loaded_client_id == "1340989932029706341":
                loaded_client_id = DEFAULT_DISCORD_CLIENT_ID

            loaded_secret = decrypt_string(raw.get("discord_client_secret_enc", "")) or DEFAULT_DISCORD_CLIENT_SECRET

            self.config = AppConfig(
                hotkey=raw.get("hotkey", DEFAULT_HOTKEY),
                discord_client_id=loaded_client_id,
                discord_client_secret=loaded_secret,
                destination=destination,
                notifications_enabled=raw.get("notifications_enabled", True),
                play_sound=raw.get("play_sound", True),
                start_with_windows=raw.get("start_with_windows", False),
                save_local_copy=raw.get("save_local_copy", False),
                local_copy_dir=raw.get("local_copy_dir", DEFAULT_LOCAL_STORAGE_DIR),
                language=raw.get("language", "system"),
            )
            return self.config
        except Exception as e:
            logger.error("Failed to load configuration from %s: %s", self.config_path, e)
            self.config = AppConfig()
            return self.config

    def save(self) -> bool:
        try:
            raw_dest = None
            if self.config.destination:
                raw_dest = {
                    "type": self.config.destination.type,
                    "guild_id": self.config.destination.guild_id,
                    "guild_name": self.config.destination.guild_name,
                    "channel_id": self.config.destination.channel_id,
                    "channel_name": self.config.destination.channel_name,
                    "webhook_id": self.config.destination.webhook_id,
                    "webhook_url_enc": encrypt_string(self.config.destination.webhook_url),
                    "webhook_token_enc": encrypt_string(self.config.destination.webhook_token),
                }

            data = {
                "hotkey": self.config.hotkey,
                "discord_client_id": self.config.discord_client_id,
                "discord_client_secret_enc": encrypt_string(self.config.discord_client_secret),
                "destination": raw_dest,
                "notifications_enabled": self.config.notifications_enabled,
                "play_sound": self.config.play_sound,
                "start_with_windows": self.config.start_with_windows,
                "save_local_copy": self.config.save_local_copy,
                "local_copy_dir": self.config.local_copy_dir,
                "language": self.config.language,
            }

            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error("Failed to save configuration to %s: %s", self.config_path, e)
            return False

    def is_configured(self) -> bool:
        return (
            self.config.destination is not None
            and bool(self.config.destination.webhook_url)
        )

    def set_destination(self, dest: Optional[DiscordDestinationConfig]) -> None:
        self.config.destination = dest
        self.save()

    def clear_destination(self) -> None:
        self.config.destination = None
        self.save()
