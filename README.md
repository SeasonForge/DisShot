# DisShot 📸

Fast, lightweight Windows desktop application that captures screen regions on hotkey (`Print Screen` or custom combo), uploads them directly to your Discord channel, and automatically copies the attachment link to your clipboard.

```text
[Print Screen] → [Select Area] → [Upload to Discord] → [URL in Clipboard] (Ctrl+V)
```

## Features

- **Global Hotkey with Interactive Recorder**: Press `Print Screen` (or set custom shortcuts like `Ctrl+Shift+S`, `F10`, etc. via the in-app recorder) from any game or application.
- **DPI-Aware & Multi-Monitor Support**: Virtual desktop composite capture across multi-display setups without coordinate offsets.
- **Discord OAuth2 & Webhooks**: One-click authentication with official Discord server & channel selection UI, plus direct Webhook URL fallback.
- **Hardware-Backed Encryption**: Credentials and tokens are encrypted locally with Windows DPAPI (`CryptProtectData`).
- **Zero Friction**: Stays quietly in the system tray with balloon notifications and audio cues.
- **Native Clipboard Integration**: Instant Windows Win32 clipboard writing for 100% reliable pasting.

## Quick Start

### Option 1: Standalone Portable EXE (Recommended)
Download the latest `DisShot.exe` from [Releases](../../releases) and run it! No installation or Python required.

### Option 2: Run from Source

1. Clone repository:
   ```bash
   git clone https://github.com/your-username/DisShot.git
   cd DisShot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Building Executable

To build a single-file standalone `.exe`:
```bash
pip install pyinstaller pillow
pyinstaller --noconfirm --onefile --windowed --name "DisShot" --icon "icon.ico" main.py
```

The compiled binary will be located in `dist/DisShot.exe`.

## Architecture & Project Structure

```text
DisShot/
├── main.py                  # Application entry point with DPI awareness
├── config.py                # Configuration constants
├── requirements.txt         # Dependencies
├── app/
│   ├── lifecycle.py         # Main application controller
│   ├── tray.py              # System tray icon and context menu
│   └── hotkey.py            # Global keyboard hook (pynput)
├── capture/
│   └── sniper.py            # DPI-aware multi-monitor region capture overlay
├── discord/
│   ├── auth.py              # Discord OAuth2 loopback server & PKCE
│   ├── ipc.py               # Discord Desktop IPC named-pipe client
│   ├── destination.py       # Discord destination model
│   └── uploader.py          # Discord webhook multipart uploader
├── upload/
│   └── base.py              # UploadService and UploadResult abstraction
├── clipboard/
│   └── manager.py           # Native Win32 clipboard manager
├── settings/
│   ├── secure_store.py      # Windows DPAPI encryption
│   └── manager.py           # Local JSON configuration manager
├── ui/
│   ├── setup_dialog.py      # Onboarding & Discord connection wizard
│   ├── settings_dialog.py   # Settings & channel management
│   ├── hotkey_widget.py     # Interactive Hotkey Recorder widget
│   └── notifications.py     # System notifications and sounds
└── tests/                   # Automated unit & integration tests
```

## License

MIT License. Open source and free to use.
