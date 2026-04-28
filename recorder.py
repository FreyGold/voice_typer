import subprocess
import os
import signal
import time
import numpy as np
import wave

class Recorder:
    def __init__(self, samplerate=16000, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self.process = None
        self.temp_filename = os.path.join(os.getcwd(), "temp_raw.wav")
        self.trimmed_filename = os.path.join(os.getcwd(), "temp_recording.wav")

    def start(self):
        for f in [self.temp_filename, self.trimmed_filename]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

        command = ["arecord", "-f", "S16_LE", "-r", str(self.samplerate), "-c", str(self.channels), "-t", "wav", self.temp_filename]
        self.process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self):
        if self.process:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=1)
            except:
                self.process.kill()
                self.process.wait()
            self.process = None
            
            if os.path.exists(self.temp_filename) and os.path.getsize(self.temp_filename) > 1000:
                return self.trim_silence_python(self.temp_filename, self.trimmed_filename)
        return None

    def trim_silence_python(self, input_file, output_file):
        try:
            with wave.open(input_file, 'rb') as wav:
                params = wav.getparams()
                frames = wav.readframes(params.nframes)
                # Convert buffer to numpy array
                audio_data = np.frombuffer(frames, dtype=np.int16)

            # Calculate energy/amplitude
            # Threshold: ~500 is a good starting point for -30dB approx
            threshold = 500 
            
            # Find indices where amplitude exceeds threshold
            mask = np.abs(audio_data) > threshold
            if not np.any(mask):
                return input_file # Fallback if entirely silent

            # Get first and last active index
            start_idx = np.argmax(mask)
            end_idx = len(mask) - np.argmax(mask[::-1])

            # Add a small padding (0.1s) to avoid clipping words
            padding = int(0.1 * self.samplerate)
            start_idx = max(0, start_idx - padding)
            end_idx = min(len(audio_data), end_idx + padding)

            trimmed_data = audio_data[start_idx:end_idx]

            # Write trimmed file
            with wave.open(output_file, 'wb') as wav_out:
                wav_out.setparams(params)
                wav_out.writeframes(trimmed_data.tobytes())

            raw_size = os.path.getsize(input_file)
            trim_size = os.path.getsize(output_file)
            reduction = 100 - (trim_size / raw_size * 100)
            print(f"Python Trim: {raw_size} -> {trim_size} bytes (Reduced {reduction:.1f}%)")
            
            return output_file
        except Exception as e:
            print(f"Python Trim Error: {e}")
            return input_file

    def play_last(self):
        target = self.trimmed_filename if os.path.exists(self.trimmed_filename) else self.temp_filename
        if os.path.exists(target):
            subprocess.Popen(["aplay", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
