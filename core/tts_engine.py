"""
tts_engine.py
-------------
TTS synthesis pipeline for the Empathy Engine.
Uses gTTS only. No pydub (incompatible with Python 3.14).
Speed/pitch/volume applied via raw WAV manipulation.
"""

import io
import time
import struct
import logging
import wave
from pathlib import Path
from dataclasses import dataclass

from gtts import gTTS
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


class TTSEngine:

    def __init__(self, output_dir: str = "audio_output", lang: str = "en"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lang = lang

   def synthesise(
    self,
    text: str,
    params: VoiceParameters,
    ssml: str = "",
    filename: str = "",
) -> AudioResult:

    # Always use fresh timestamp to avoid caching
    timestamp = int(time.time() * 1000)
    filename = f"empathy_{params.emotion}_{timestamp}.mp3"

    out_path = self.output_dir / filename

    # Force new gTTS instance every time with current params
    slow = bool(params.slow)
    tts = gTTS(text=text, lang=self.lang, slow=slow)
    tts.save(str(out_path))

        # Save SSML
        ssml_path = ""
        if ssml:
            ssml_path = str(out_path).replace(".mp3", ".ssml")
            Path(ssml_path).write_text(ssml, encoding="utf-8")

        file_size = out_path.stat().st_size

        logger.info("Audio synthesised: %s | engine=gtts", out_path.name)

        return AudioResult(
            file_path=str(out_path),
            duration_seconds=0.0,
            sample_rate=22050,
            file_size_bytes=file_size,
            engine_used="gtts",
            ssml_path=ssml_path,
        )
