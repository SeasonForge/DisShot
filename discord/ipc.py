import struct
import json
import uuid
import logging
from typing import Optional, Tuple, Dict, Any, List

logger = logging.getLogger(__name__)


class DiscordIPC:
    """
    Direct Inter-Process Communication (IPC) with the running Discord Desktop application
    via Windows Named Pipe (\\\\.\\pipe\\discord-ipc-0).
    """
    def __init__(self, client_id: str):
        self.client_id = client_id.strip()
        self._pipe = None
        self._connected = False

    def is_discord_running(self) -> bool:
        """
        Quick check if any Discord IPC pipe is active.
        """
        for i in range(10):
            pipe_name = rf"\\.\pipe\discord-ipc-{i}"
            try:
                with open(pipe_name, "r+b", buffering=0) as f:
                    return True
            except Exception:
                continue
        return False

    def connect(self) -> Tuple[bool, Optional[str]]:
        """
        Connects to the Discord named pipe and performs the IPC handshake.
        """
        for i in range(10):
            pipe_name = rf"\\.\pipe\discord-ipc-{i}"
            try:
                self._pipe = open(pipe_name, "r+b", buffering=0)
                
                # Op 0 = HANDSHAKE
                handshake_data = json.dumps({"v": 1, "client_id": self.client_id}).encode("utf-8")
                self._pipe.write(struct.pack("<II", 0, len(handshake_data)) + handshake_data)

                # Read handshake response
                header = self._pipe.read(8)
                if len(header) < 8:
                    self.close()
                    continue

                op, length = struct.unpack("<II", header)
                raw_resp = self._pipe.read(length)
                resp = json.loads(raw_resp.decode("utf-8"))

                # Check if Discord returned an error (e.g. invalid client id)
                if "code" in resp and resp["code"] != 0:
                    err_msg = resp.get("message", "Invalid Client ID or Discord IPC error")
                    logger.warning("Discord IPC Handshake error: %s", err_msg)
                    self.close()
                    return False, err_msg

                self._connected = True
                logger.info("Connected to Discord Desktop IPC on %s", pipe_name)
                return True, None
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.debug("Pipe %s connection attempt failed: %s", pipe_name, e)
                self.close()
                continue

        return False, "Discord desktop client is not running."

    def authorize(self, scopes: List[str] = None) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Sends AUTHORIZE command to the running Discord client.
        Prompts the native authorization popup inside the Discord app.
        Returns (success, code, error_message).
        """
        if scopes is None:
            scopes = ["webhook.incoming"]

        ok, err = self.connect()
        if not ok:
            return False, None, err

        try:
            nonce = str(uuid.uuid4())
            payload = {
                "cmd": "AUTHORIZE",
                "args": {
                    "client_id": self.client_id,
                    "scopes": scopes,
                    "prompt": "consent"
                },
                "nonce": nonce
            }
            payload_bytes = json.dumps(payload).encode("utf-8")
            
            # Op 1 = FRAME
            self._pipe.write(struct.pack("<II", 1, len(payload_bytes)) + payload_bytes)
            logger.info("Sent AUTHORIZE request to Discord Desktop client. Waiting for in-app approval...")

            # Read response frame (blocks until user clicks Authorize or Cancel in Discord)
            header = self._pipe.read(8)
            if len(header) < 8:
                return False, None, "Connection to Discord was closed."

            op, length = struct.unpack("<II", header)
            raw_resp = self._pipe.read(length)
            resp = json.loads(raw_resp.decode("utf-8"))

            if resp.get("evt") == "ERROR":
                err_data = resp.get("data", {})
                msg = err_data.get("message", "Authorization was denied in Discord.")
                return False, None, msg

            data = resp.get("data", {})
            code = data.get("code")
            if code:
                logger.info("Received authorization code from Discord Desktop IPC!")
                return True, code, None
            
            return False, None, "No authorization code returned from Discord."
        except Exception as e:
            logger.error("Error during Discord IPC authorize: %s", e)
            return False, None, str(e)
        finally:
            self.close()

    def close(self):
        if self._pipe:
            try:
                self._pipe.close()
            except Exception:
                pass
            self._pipe = None
        self._connected = False
