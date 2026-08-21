import os
from pathlib import Path

APP_NAME = "DisShot"
APP_VERSION = "1.0.4"

# AppData configuration directory
APPDATA_DIR = Path(os.getenv("APPDATA", Path.home())) / APP_NAME
APPDATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = APPDATA_DIR / "config.json"

# Hotkey defaults
DEFAULT_HOTKEY = "print_screen"

# Discord OAuth2 defaults
DEFAULT_DISCORD_CLIENT_ID = "1539174412618563665"
DEFAULT_DISCORD_CLIENT_SECRET = "QwEiXjtV6GONHNIiNrOYmNb--UF0yJyQ"
OAUTH_REDIRECT_HOST = "127.0.0.1"
OAUTH_REDIRECT_PORT = 8765
OAUTH_REDIRECT_URI = f"http://{OAUTH_REDIRECT_HOST}:{OAUTH_REDIRECT_PORT}/callback"
DISCORD_AUTH_BASE_URL = "https://discord.com/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"

# Local storage defaults
DEFAULT_LOCAL_STORAGE_DIR = str(Path.home() / "Pictures" / APP_NAME)

# Project & Donation links
PROJECT_REPO_URL = "https://github.com/SeasonForge/DisShot"
DONATE_URL = "https://plisio.net/donate/IF4FNXAb"
