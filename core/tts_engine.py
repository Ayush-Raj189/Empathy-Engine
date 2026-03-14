"""
tts_engine.py
-------------
Text-to-Speech synthesis pipeline for the Empathy Engine.
Uses gTTS for synthesis + pydub for prosody post-processing.
Cloud deployment: gTTS only, no pyttsx3.
"""

import io
import time
import logging
from pathlib import Path
from dataclasses import dataclass

from gtts import gTTS
from pydub import AudioSegment
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

        if not filename:
            timestamp = int(time.time() * 1000)
            filename = f"empathy_{params.emotion}_{timestamp}.mp3"

        out_path = self.output_dir / filename

        raw_audio = self._gtts_synthesise(text, params)
        final_audio = self._apply_prosody(raw_audio, params)
        final_audio.export(str(out_path), format="mp3", bitrate="128k")

        ssml_path = ""
        if ssml:
            ssml_path = str(out_path).replace(".mp3", ".ssml")
            Path(ssml_path).write_text(ssml, encoding="utf-8")

        duration = len(final_audio) / 1000.0
        file_size = out_path.stat().st_size

        return AudioResult(
            file_path=str(out_path),
            duration_seconds=duration,
            sample_rate=final_audio.frame_rate,
            file_size_bytes=file_size,
            engine_used="gtts",
            ssml_path=ssml_path,
        )

    def _gtts_synthesise(self, text: str, params: VoiceParameters) -> AudioSegment:
        tts = gTTS(text=text, lang=self.lang, slow=params.slow)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return AudioSegment.from_mp3(buf)

    def _apply_prosody(self, audio: AudioSegment, params: VoiceParameters) -> AudioSegment:
        audio = self._adjust_speed(audio, params.rate_percent)
        audio = self._adjust_pitch(audio, params.pitch_st)
        audio = self._adjust_volume(audio, params.volume_db)
        return audio

    def _adjust_speed(self, audio: AudioSegment, rate_pct: int) -> AudioSegment:
        if rate_pct == 100:
            return audio
        speed_factor = rate_pct / 100.0
        altered = audio._spawn(
            audio.raw_data,
            overrides={"frame_rate": int(audio.frame_rate * speed_factor)},
        )
        return altered.set_frame_rate(audio.frame_rate)

    def _adjust_pitch(self, audio: AudioSegment, semitones: int) -> AudioSegment:
        if semitones == 0:
            return audio
        ratio = 2 ** (semitones / 12.0)
        new_rate = int(audio.frame_rate * ratio)
        shifted = audio._spawn(
            audio.raw_data,
            overrides={"frame_rate": new_rate},
        )
        return shifted.set_frame_rate(audio.frame_rate)

    def _adjust_volume(self, audio: AudioSegment, db: float) -> AudioSegment:
        if abs(db) < 0.1:
            return audio
        return audio + db
