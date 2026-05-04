# Voice Typer

A high-performance, local/cloud GUI speech-to-text recorder that types into any text field across your system. Optimized for Wayland (Pop!_OS), Linux, Windows, and macOS.

## Features
- **Dual Mode STT**: 
  - **Local**: Uses `faster-whisper` for private, offline transcription.
  - **Cloud**: Uses `Groq (Whisper-Large-V3-Turbo)` for near-instant, high-accuracy results.
- **Smart Punctuation**: Uses AI to intelligently add punctuation and grammar.
- **Egyptian Dialect Support**: Specifically tuned to handle Egyptian Arabic vocabulary.
- **Cross-Platform Launchers**: Native Start Menu/Dock support for all OSs.

## 🛠 System Dependencies

Before installing Python packages, ensure your system has the required audio and clipboard libraries:

### Linux (Ubuntu/Pop!_OS/Debian)
```bash
sudo apt update
sudo apt install python3-venv libportaudio2 xclip alsa-utils
```

### Windows
- Install [Python 3.10+](https://www.python.org/downloads/windows/) (Ensure "Add Python to PATH" is checked).

### macOS
```bash
brew install portaudio
```

## 🚀 Setup & Installation

1. **Create and activate a virtual environment:**
   ```bash
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Linux Permissions (For Hotkeys & Typing):**
   ```bash
   sudo usermod -aG input $USER
   # Reboot or log out for changes to take effect.
   ```

## 🖥 Adding to Start Menu / Applications

Native launchers are provided in the `launchers/` folder.

### Linux (GNOME/KDE/Pop!_OS)
1. Copy the desktop entry to your local applications folder:
   ```bash
   cp launchers/voice-typer.desktop ~/.local/share/applications/
   ```
2. Update the `Icon=` path in that file if you move your custom icon.
3. The app will now appear in your "Activities" or App Grid.

### Windows
1. Right-click `launchers/run_windows.bat` and select **Create shortcut**.
2. Rename the shortcut to `Voice Typer`.
3. Right-click the shortcut -> **Properties** -> **Change Icon** (choose an icon if you have one).
4. Press `Win + R`, type `shell:programs`, and press Enter.
5. Move your shortcut into this folder. It will now appear in your Start Menu.

### macOS
1. You can run `launchers/run_macos.sh` directly.
2. **To add to Dock/Launchpad:**
   - Open **Automator** app.
   - Choose **Application**.
   - Search for **Run Shell Script** and drag it in.
   - Set the content to: `/path/to/repo/launchers/run_macos.sh`
   - Save it as `Voice Typer.app` in your `/Applications` folder.

## ⚙ Configuration
- **Hotkey**: Default is **Right Alt**. Change it in settings (⚙).
- **Mode**: Switch between **Hold** (Push-to-Talk) and **Toggle** in settings.
- **Cloud Mode**: Requires a [Groq API Key](https://console.groq.com/keys).
