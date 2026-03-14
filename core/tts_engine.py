"""
tts_engine.py
-------------
TTS using ElevenLabs for genuine emotional voices.
Falls back to gTTS if API key missing.
"""

import os
import time
import logging
from pathlib import Path
from dataclasses import dataclass
from .voice_mapper import VoiceParameters

logger = logging.getLogger(__name__)


@dataclass
class AudioResult:
    file_path: str
    duration_seconds: float
    sample_rate: int
    file_size_bytes: int
    engine_used: str
    ssml_path: str = ""


# Each emotion gets different ElevenLabs voice settings
# stability  : low = more expressive, high = more consistent
# style      : low = neutral, high = very dramatic
# speed      : 0.7 = slow, 1.0 = normal, 1.4 = fast
EMOTION_SETTINGS = {
    "joy":         {"stability": 0.35, "style": 0.45, "speed": 1.10},
    "excitement":  {"stability": 0.15, "style": 0.90, "speed": 1.35},
    "gratitude":   {"stability": 0.60, "style": 0.30, "speed": 0.95},
    "sadness":     {"stability": 0.80, "style": 0.05, "speed": 0.72},
    "frustration": {"stability": 0.25, "style": 0.65, "speed": 1.15},
    "anger":       {"stability": 0.15, "style": 0.95, "speed": 1.25},
    "fear":        {"stability": 0.55, "style": 0.20, "speed": 0.82},
    "surprise":    {"stability": 0.20, "style": 0.75, "speed": 1.20},
    "curiosity":   {"stability": 0.50, "style": 0.35, "speed": 1.00},
    "neutral":     {"stability": 0.75, "style": 0.00, "speed": 1.00},
}

VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel — warm expressive voice
MODEL_ID = "eleven_turbo_v2"


class TTSEngine:

    def __init__(self, output_dir: str = "audio_output", lang: str = "en"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lang = lang
        self.api_key = os.getenv("ELEVENLABS_API_KEY", "")

    def synthesise(
        self,
        text: str,
        params: VoiceParameters,
        ssml: str = "",
        filename: str = "",
    ) -> AudioResult:

        timestamp = int(time.time() * 1000)
        filename = f"empathy_{params.emotion}_{timestamp}.mp3"
        out_path = self.output_dir / filename

        if self.api_key:
            try:
                engine = self._elevenlabs(text, params, out_path)
            except Exception as e:
                logger.warning("ElevenLabs failed: %s — falling back to gTTS", e)
                engine = self._gtts(text, params, out_path)
        else:
            engine = self._gtts(text, params, out_path)

        ssml_path = ""
        if ssml:
            ssml_path = str(out_path).replace(".mp3", ".ssml")
            Path(ssml_path).write_text(ssml, encoding="utf-8")

        file_size = out_path.stat().st_size

        return AudioResult(
            file_path=str(out_path),
            duration_seconds=0.0,
            sample_rate=22050,
            file_size_bytes=file_size,
            engine_used=engine,
            ssml_path=ssml_path,
        )

    def _elevenlabs(self, text: str, params: VoiceParameters, out_path: Path) -> str:
        import requests

        emotion = params.emotion
        s = EMOTION_SETTINGS.get(emotion, EMOTION_SETTINGS["neutral"])

        # Scale style and speed by intensity
        intensity = params.intensity
        style  = min(s["style"] * (0.4 + intensity * 0.6), 1.0)
        speed  = s["speed"]
        stability = s["stability"]

        # Push further at high intensity
        if intensity > 0.7:
            if emotion in ("excitement", "anger", "frustration", "surprise"):
                speed    = min(speed + 0.1, 1.5)
                style    = min(style + 0.1, 1.0)
                stability = max(stability - 0.05, 0.1)
            elif emotion in ("sadness", "fear"):
                speed = max(speed - 0.05, 0.65)

        payload = {
            "text": text,
            "model_id": MODEL_ID,
            "voice_settings": {
                "stability": stability,
                "similarity_boost": 0.75,
                "style": style,
                "use_speaker_boost": True,
                "speed": speed,
            },
        }

        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            json=payload,
            headers={
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(f"ElevenLabs {response.status_code}: {response.text[:300]}")

        out_path.write_bytes(response.content)
        logger.info("ElevenLabs: emotion=%s speed=%.2f style=%.2f stability=%.2f",
                    emotion, speed, style, stability)
        return "elevenlabs"

    def _gtts(self, text: str, params: VoiceParameters, out_path: Path) -> str:
        from gtts import gTTS
        slow = params.rate_percent < 85
        tts = gTTS(text=text, lang=self.lang, slow=slow)
        tts.save(str(out_path))
        return "gtts"
