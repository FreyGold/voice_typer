import os
import wave
import numpy as np
import sounddevice as sd
import threading
import tempfile

class Recorder:
    def __init__(self, samplerate=16000, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self.temp_dir = os.path.join(tempfile.gettempdir(), "voice-typer")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.temp_filename = os.path.join(self.temp_dir, "temp_raw.wav")
        self.trimmed_filename = os.path.join(self.temp_dir, "temp_recording.wav")
        self.recording_data = []
        self.stream = None
        self.is_recording = False

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio Callback Status: {status}")
        self.recording_data.append(indata.copy())

    def start(self):
        # Cleanup old files
        for f in [self.temp_filename, self.trimmed_filename]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

        self.recording_data = []
        self.is_recording = True
        try:
            self.stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype='int16',
                callback=self._audio_callback
            )
            self.stream.start()
        except Exception as e:
            print(f"Recorder: Start Error: {e}")
            self.is_recording = False

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"Recorder: Stop Error: {e}")
            self.stream = None
        self.is_recording = False

        if not self.recording_data:
            return None

        # Concatenate all blocks
        audio_data = np.concatenate(self.recording_data, axis=0)
        
        # Save raw recording
        self._write_wav(self.temp_filename, audio_data)
        
        if len(audio_data) > 1000:
            return self.trim_silence_python(audio_data, self.trimmed_filename)
        return self.temp_filename

    def _write_wav(self, filename, data):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(self.samplerate)
            wf.writeframes(data.tobytes())

    def trim_silence_python(self, audio_data, output_file):
        try:
            # Flatten if multi-channel (though we use mono)
            flat_data = audio_data.flatten()
            
            # Threshold: ~500 is a good starting point for -30dB approx
            threshold = 500 
            
            # Find indices where amplitude exceeds threshold
            mask = np.abs(flat_data) > threshold
            if not np.any(mask):
                # Fallback: just write the raw data to output_file if silent
                self._write_wav(output_file, audio_data)
                return output_file

            # Get first and last active index
            start_idx = np.argmax(mask)
            end_idx = len(mask) - np.argmax(mask[::-1])

            # Add a small padding (0.1s) to avoid clipping words
            padding = int(0.1 * self.samplerate)
            start_idx = max(0, start_idx - padding)
            end_idx = min(len(flat_data), end_idx + padding)

            trimmed_data = audio_data[start_idx:end_idx]

            # Write trimmed file
            self._write_wav(output_file, trimmed_data)
            
            print(f"Trim: {len(audio_data)} -> {len(trimmed_data)} frames")
            return output_file
        except Exception as e:
            print(f"Trim Error: {e}")
            self._write_wav(output_file, audio_data)
            return output_file

    def play_last(self):
        target = self.trimmed_filename if os.path.exists(self.trimmed_filename) else self.temp_filename
        if os.path.exists(target):
            threading.Thread(target=self._play_thread, args=(target,), daemon=True).start()

    def _play_thread(self, target):
        try:
            with wave.open(target, 'rb') as wf:
                data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
                sd.play(data, self.samplerate)
                sd.wait()
        except Exception as e:
            print(f"Playback Error: {e}")
