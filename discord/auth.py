import base64
import hashlib
import http.server
import logging
import os
import secrets
import socketserver
import threading
import urllib.parse
import webbrowser
from typing import Optional, Tuple, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal
import requests

from config import (
    OAUTH_REDIRECT_HOST,
    OAUTH_REDIRECT_PORT,
    OAUTH_REDIRECT_URI,
    DISCORD_AUTH_BASE_URL,
    DISCORD_TOKEN_URL,
)
from discord.destination import DiscordDestination
from discord.ipc import DiscordIPC

logger = logging.getLogger(__name__)


def generate_pkce_pair() -> Tuple[str, str]:
    """
    Generates (code_verifier, code_challenge) for OAuth2 PKCE.
    """
    code_verifier = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(hashed).decode("ascii").rstrip("=")
    return code_verifier, code_challenge


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """
    Handles the incoming redirect from Discord on 127.0.0.1:8765/callback.
    """
    server: "OAuthServer"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        query_params = urllib.parse.parse_qs(parsed.query)

        error = query_params.get("error", [None])[0]
        code = query_params.get("code", [None])[0]
        state = query_params.get("state", [None])[0]
        guild_id = query_params.get("guild_id", [None])[0]

        if error:
            error_description = query_params.get("error_description", [error])[0]
            if error == "access_denied" or "cancelled" in str(error_description).lower() or "cancel" in str(error).lower():
                self.server.auth_error = "Authorization cancelled."
            else:
                self.server.auth_error = f"Discord error: {error_description}"
            self._send_html_response(
                title="Authorization Cancelled",
                heading="Authorization was cancelled",
                message="You can close this tab and return to Screenshotter.",
                success=False
            )
        elif code:
            self.server.auth_code = code
            self.server.auth_state = state
            self.server.auth_guild_id = guild_id
            self._send_html_response(
                title="Connected to Discord!",
                heading="Successfully Connected!",
                message="Your Discord destination is linked. You can close this tab and start capturing screenshots with Screenshotter.",
                success=True
            )
        else:
            self.server.auth_error = "Invalid callback request received."
            self._send_html_response(
                title="Error",
                heading="Authentication Failed",
                message="No authorization code received. You can close this window.",
                success=False
            )

        # Notify the waiting thread
        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def _send_html_response(self, title: str, heading: str, message: str, success: bool):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        color = "#5865F2" if success else "#ED4245"
        icon_svg = (
            '<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#5865F2" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>'
            if success else
            '<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#ED4245" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{title} — Screenshotter</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #1e1f22;
            color: #dbdee1;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }}
        .card {{
            background-color: #2b2d31;
            padding: 40px 48px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
            text-align: center;
            max-width: 440px;
        }}
        .icon {{ margin-bottom: 20px; }}
        h1 {{ color: #ffffff; font-size: 24px; margin: 0 0 12px 0; }}
        p {{ font-size: 15px; line-height: 1.5; color: #949ba4; margin: 0; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">{icon_svg}</div>
        <h1>{heading}</h1>
        <p>{message}</p>
    </div>
</body>
</html>"""
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress noisy HTTP logs
        return


class OAuthServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.auth_code: Optional[str] = None
        self.auth_state: Optional[str] = None
        self.auth_guild_id: Optional[str] = None
        self.auth_error: Optional[str] = None


class DiscordAuthFlow(QObject):
    """
    Orchestrates the OAuth2 PKCE login flow for Discord webhook destination.
    """
    finished = pyqtSignal(bool, object, str)  # (success, DiscordDestination or None, message)

    def __init__(self, client_id: str, client_secret: Optional[str] = None):
        super().__init__()
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip() if client_secret else ""
        self._server: Optional[OAuthServer] = None
        self._code_verifier: str = ""
        self._state: str = ""
        self._is_cancelled: bool = False

    def start_authorization(self) -> None:
        """
        Starts local loopback server, launches browser, and handles the exchange asynchronously.
        """
        self._is_cancelled = False
        threading.Thread(target=self._run_flow, daemon=True).start()

    def cancel(self) -> None:
        """
        Cancels the active authorization flow and shuts down the local listener.
        """
        logger.info("Cancelling Discord authorization flow...")
        self._is_cancelled = True
        if self._server:
            try:
                self._server.shutdown()
            except Exception as e:
                logger.debug("Error shutting down server: %s", e)

    def _run_flow(self) -> None:
        # 1. First attempt direct authorization via running Discord Desktop app (IPC)
        ipc = DiscordIPC(self.client_id)
        if ipc.is_discord_running():
            logger.info("Discord Desktop client detected. Attempting direct in-app authorization...")
            ipc_ok, ipc_code, ipc_err = ipc.authorize(["webhook.incoming"])
            
            if self._is_cancelled:
                self.finished.emit(False, None, "Authorization cancelled.")
                return

            if ipc_ok and ipc_code:
                logger.info("Direct Discord Desktop authorization succeeded!")
                self._exchange_code(ipc_code, redirect_uri="")
                return
            elif ipc_err and ("cancelled" in ipc_err.lower() or "denied" in ipc_err.lower() or "oauth2" in ipc_err.lower()):
                logger.info("User cancelled or denied authorization in Discord Desktop (%s). Aborting flow.", ipc_err)
                self.finished.emit(False, None, "Authorization cancelled.")
                return
            else:
                logger.info("Discord Desktop IPC authorization skipped (%s), falling back to browser...", ipc_err)

        if self._is_cancelled:
            self.finished.emit(False, None, "Authorization cancelled.")
            return

        # 2. Fallback to Browser OAuth2 flow with local loopback server
        self._code_verifier, code_challenge = generate_pkce_pair()
        self._state = secrets.token_urlsafe(16)

        try:
            self._server = OAuthServer(
                (OAUTH_REDIRECT_HOST, OAUTH_REDIRECT_PORT),
                OAuthCallbackHandler
            )
        except Exception as e:
            logger.error("Failed to start local OAuth loopback server on port %d: %s", OAUTH_REDIRECT_PORT, e)
            self.finished.emit(False, None, f"Could not start local listener on port {OAUTH_REDIRECT_PORT}. Check if another instance is running.")
            return

        # Construct authorization URL
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "webhook.incoming",
            "redirect_uri": OAUTH_REDIRECT_URI,
            "state": self._state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "prompt": "consent",
        }
        auth_url = f"{DISCORD_AUTH_BASE_URL}?{urllib.parse.urlencode(params)}"
        logger.info("Opening browser for Discord OAuth: %s", auth_url)

        try:
            webbrowser.open(auth_url)
        except Exception as e:
            logger.error("Failed to open browser: %s", e)

        # Wait for callback
        logger.info("Waiting for Discord authorization callback...")
        try:
            self._server.serve_forever()
        except Exception as e:
            logger.debug("OAuth server loop finished: %s", e)
        finally:
            try:
                self._server.server_close()
            except Exception:
                pass

        if self._is_cancelled:
            logger.info("Auth flow was cancelled.")
            self.finished.emit(False, None, "Authorization cancelled.")
            return

        # Handle result
        if self._server.auth_error:
            self.finished.emit(False, None, self._server.auth_error)
            return

        if not self._server.auth_code:
            self.finished.emit(False, None, "Authorization cancelled or timed out.")
            return

        if self._server.auth_state != self._state:
            self.finished.emit(False, None, "Security error: OAuth state mismatch.")
            return

        # Exchange authorization code for token and webhook details
        self._exchange_code(self._server.auth_code, redirect_uri=OAUTH_REDIRECT_URI)

    def _exchange_code(self, code: str, redirect_uri: str = OAUTH_REDIRECT_URI) -> None:
        logger.info("Exchanging authorization code for Discord webhook token...")
        payload = {
            "client_id": self.client_id,
            "grant_type": "authorization_code",
            "code": code,
        }

        if redirect_uri:
            payload["redirect_uri"] = redirect_uri

        if self._code_verifier:
            payload["code_verifier"] = self._code_verifier

        if self.client_secret:
            payload["client_secret"] = self.client_secret

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            response = requests.post(
                DISCORD_TOKEN_URL,
                data=payload,
                headers=headers,
                timeout=15
            )

            if response.status_code != 200:
                logger.error("Token exchange failed (%d): %s", response.status_code, response.text)
                self.finished.emit(False, None, f"Discord token exchange failed (HTTP {response.status_code}).")
                return

            data = response.json()
            webhook_data = data.get("webhook")

            if not webhook_data or not webhook_data.get("url"):
                logger.error("No webhook returned in Discord OAuth response: %s", data)
                self.finished.emit(False, None, "Discord did not return a webhook for the selected channel.")
                return

            webhook_url = webhook_data["url"]
            webhook_id = str(webhook_data.get("id", ""))
            guild_id = str(webhook_data.get("guild_id", ""))
            channel_id = str(webhook_data.get("channel_id", ""))
            webhook_name = webhook_data.get("name", "Screenshotter")
            webhook_token = webhook_data.get("token", "")

            # Fetch channel / guild name if possible via webhook info
            destination = DiscordDestination(
                guild_id=guild_id,
                guild_name=webhook_name or f"Guild {guild_id}",
                channel_id=channel_id,
                channel_name=f"Channel {channel_id}",
                webhook_url=webhook_url,
                webhook_token=webhook_token
            )

            logger.info("Successfully configured Discord destination: %s", destination.name)
            self.finished.emit(True, destination, "Discord connected successfully!")

        except requests.exceptions.RequestException as e:
            logger.error("Network error during token exchange: %s", e)
            self.finished.emit(False, None, f"Network error during Discord connection: {e}")
        except Exception as e:
            logger.error("Unexpected error during token exchange: %s", e)
            self.finished.emit(False, None, f"Unexpected error: {e}")
