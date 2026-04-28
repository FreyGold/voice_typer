from faster_whisper import WhisperModel
import os
from openai import OpenAI
import re

class Transcriber:
    def __init__(self, mode="local", model_size="small", api_key=None):
        self.mode = mode
        self.model = None
        self.client = None
        
        if mode == "local":
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        else:
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key
            )

    def clean_transcription(self, text):
        if not text:
            return ""

        # Remove Whisper hallucinations from silent/garbage audio
        hallucinations = [
            r"thank you\.?", r"thanks for watching\.?", 
            r"subtitles by .*?", r"please subscribe\.?"
        ]
        temp_text = text.strip()
        for h in hallucinations:
            if re.fullmatch(h, temp_text, flags=re.IGNORECASE):
                return ""

        # 1. Remove vocal fillers (um, uh, ah, er, etc.)
        # Matches words like "um", "uh" at word boundaries, case-insensitive
        fillers = r'\b(um|uh|ah|er|eh|hm|hmm|like|you know)\b'
        text = re.sub(fillers, '', text, flags=re.IGNORECASE)

        # 2. Remove immediate consecutive duplicate words/phrases
        # Matches "the the" or "I think I think"
        # \b(\w+(?:\s+\w+)*) matches a word or phrase
        # \s+\1 matches the same word/phrase again
        pattern = r'\b(.+?)(?:\s+\1\b)+'
        text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE)

        # 3. Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 4. Final duplicate word pass (single words)
        text = re.sub(r'\b(\w+)( \1\b)+', r'\1', text, flags=re.IGNORECASE)

        return text

    def transcribe(self, audio_path):
        if not os.path.exists(audio_path):
            return ""
            
        text = ""
        if self.mode == "local":
            segments, info = self.model.transcribe(audio_path, beam_size=5)
            text = " ".join([segment.text for segment in segments])
        else:
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), audio_file.read()),
                    model="whisper-large-v3-turbo",
                    response_format="text"
                )
                text = transcription

        return self.clean_transcription(text)
