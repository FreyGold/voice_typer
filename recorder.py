import subprocess
import os
import signal
import time

class Recorder:
    def __init__(self, samplerate=16000, channels=1):
        self.samplerate = samplerate
        self.channels = channels
        self.process = None
        self.temp_filename = os.path.join(os.getcwd(), "temp_raw.wav")
        self.trimmed_filename = os.path.join(os.getcwd(), "temp_recording.wav")

    def start(self):
        # Cleanup
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
                # Optimized ffmpeg command for faster silence removal
                trim_cmd = [
                    "ffmpeg", "-y", "-i", self.temp_filename,
                    "-af", "silenceremove=start_threshold=-40dB:start_duration=0.1:stop_threshold=-40dB:stop_duration=0.1:stop_periods=-1",
                    "-c:a", "pcm_s16le", self.trimmed_filename
                ]
                try:
                    subprocess.run(trim_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    if os.path.exists(self.trimmed_filename) and os.path.getsize(self.trimmed_filename) > 1000:
                        return self.trimmed_filename
                except:
                    pass
                return self.temp_filename
        return None

    def play_last(self):
        if os.path.exists(self.trimmed_filename):
            subprocess.Popen(["aplay", self.trimmed_filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif os.path.exists(self.temp_filename):
            subprocess.Popen(["aplay", self.temp_filename], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
