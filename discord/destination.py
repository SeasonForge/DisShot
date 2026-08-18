from dataclasses import dataclass
from typing import Optional
from upload.base import Destination


@dataclass
class DiscordDestination(Destination):
    guild_id: str = ""
    guild_name: str = ""
    channel_id: str = ""
    channel_name: str = ""
    webhook_url: str = ""
    webhook_token: str = ""

    def __init__(
        self,
        guild_id: str = "",
        guild_name: str = "",
        channel_id: str = "",
        channel_name: str = "",
        webhook_url: str = "",
        webhook_token: str = "",
    ):
        name = f"#{channel_name}" if channel_name else (guild_name or "Discord Channel")
        super().__init__(type="discord", id=channel_id or webhook_url, name=name)
        self.guild_id = guild_id
        self.guild_name = guild_name
        self.channel_id = channel_id
        self.channel_name = channel_name
        self.webhook_url = webhook_url
        self.webhook_token = webhook_token
