# Voice Typer

A simple, local GUI speech-to-text recorder that types into any text field across your system.

## Features
- **Local STT**: Uses `faster-whisper` for high-accuracy, private transcription.
- **Push-to-Talk**: Hold **Right Control** to record, release to transcribe and type.
- **Universal Typing**: Works in browsers, CLIs, editors, or any focused text field.
- **Privacy Focused**: No audio ever leaves your machine.

## Prerequisites (Linux)
- `python3` and `venv`
- `alsa-utils` (for `arecord`)

## How to Run
1. Navigate to the `voice_typer` directory.
2. Run the `run.sh` script:
   ```bash
   ./run.sh
   ```

## Configuration
- **Hotkey**: Currently set to `Right Control`. You can change it in `typer_controller.py` by modifying `self.trigger_key`.
- **Model**: Set to `base` for a balance of speed/accuracy. Change in `main.py` if needed (e.g., `tiny` for speed, `small` for better accuracy).
