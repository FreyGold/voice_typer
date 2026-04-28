from faster_whisper import WhisperModel
import os
from openai import OpenAI
import re

class Transcriber:
    def __init__(self, mode="local", model_size="small", api_key=None):
        self.mode = mode
        self.model = None
        self.client = None
        self.api_key = api_key
        
        if mode == "local":
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        else:
            self.client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key
            )

    def clean_transcription(self, text):
        if not text: return ""
        hallucinations = [r"thank you\.?", r"thanks for watching\.?", r"subtitles by .*?", r"please subscribe\.?"]
        temp_text = text.strip()
        for h in hallucinations:
            if re.fullmatch(h, temp_text, flags=re.IGNORECASE): return ""
        
        fillers = r'\b(um|uh|ah|er|eh|hm|hmm|you know)\b'
        text = re.sub(fillers, '', text, flags=re.IGNORECASE)
        pattern = r'\b(.+?)(?:\s+\1\b)+'
        text = re.sub(pattern, r'\1', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def refine_punctuation(self, text, language="auto"):
        """Uses LLM to fix punctuation and grammar while keeping original words for any language."""
        if not self.client or not text or len(text) < 5:
            return text
            
        try:
            # Generalized prompt for all languages
            prompt = f"Fix the punctuation and capitalization of this speech-to-text result. Keep the original words and dialect exactly as they are. Just add periods, commas, and question marks where appropriate. If the text is informal, keep it informal. \n\nLanguage: {language}\nText: {text}"
            
            completion = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a professional multilingual editor. You fix punctuation without changing words or translating. Output ONLY the corrected text."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Refinement error: {e}")
            return text

    def transcribe(self, audio_path, language=None, refine=False):
        if not os.path.exists(audio_path): return ""
        
        initial_prompt = ""
        if language == "ar":
            initial_prompt = "يا باشا، الكلام ده بالعامية المصرية، زي ما بننطق في القاهرة كده."

        text = ""
        if self.mode == "local":
            segments, info = self.model.transcribe(audio_path, beam_size=5, language=language, 
                                                 initial_prompt=initial_prompt if initial_prompt else None)
            text = " ".join([segment.text for segment in segments])
        else:
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), audio_file.read()),
                    model="whisper-large-v3-turbo",
                    response_format="text",
                    language=language if language != "auto" else None,
                    prompt=initial_prompt if initial_prompt else None
                )
                text = transcription

        text = self.clean_transcription(text)
        
        if refine and self.mode == "cloud":
            text = self.refine_punctuation(text, language)
            
        return text
