# Voice Typer

A high-performance, local/cloud GUI speech-to-text recorder that types into any text field across your system. Optimized for Wayland (Pop!_OS) and multi-language support including Egyptian Arabic.

## Features
- **Dual Mode STT**: 
  - **Local**: Uses `faster-whisper` (Small model) for private, offline transcription.
  - **Cloud**: Uses `Groq (Whisper-Large-V3-Turbo)` for near-instant, high-accuracy results.
- **Smart Punctuation**: Uses Llama-3.1 to intelligently add punctuation and grammar to your speech.
- **Egyptian Dialect Support**: Specifically tuned to handle Egyptian Arabic vocabulary and natural flow.
- **Wayland Optimized**: Uses `evdev` for global hotkeys and a clipboard-bridge for reliable typing in any app.
- **System Tray**: Minimizes to the tray to stay out of your way.
- **Push-to-Talk or Toggle**: Choose between holding a key or tapping to record.

## Prerequisites (Linux)
- `python3` and `venv`
- `alsa-utils` (for `arecord` and `aplay`)
- `wl-clipboard` (standard on Pop!_OS, for typing support)

## Setup & Installation
1. Clone or navigate to the directory.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. **Permissions (Important for Hotkeys & Typing)**:
   ```bash
   sudo usermod -aG input $USER
   sudo modprobe uinput
   sudo chmod +666 /dev/uinput
   # You may need to log out and back in for group changes to take effect.
   ```

## How to Run
Run the launch script:
```bash
./run.sh
```

## Configuration
- **Hotkey**: Default is **Right Alt**. Change it in the settings (⚙) to Ctrl, Space, etc.
- **Language**: Set to `ar` for Egyptian Arabic or `en` for English.
- **Mode**: Switch between Push-to-Talk (Hold) and Toggle (Tap) in settings.
