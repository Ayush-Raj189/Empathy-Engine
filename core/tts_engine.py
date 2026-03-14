"""
tts_engine.py
-------------
TTS synthesis pipeline for the Empathy Engine.
Uses gTTS + pure Python audio manipulation.
No pydub, no pyttsx3 — works on Python 3.14.
"""

import io
import time
import wave
import struct
import array
import logging
import tempfile
import os
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

        timestamp = int(time.time() * 1000)
        filename = f"empathy_{params.emotion}_{timestamp}.mp3"
        out_path = self.output_dir / filename

        # Step 1: gTTS — use slow for sadness/fear, normal for rest
        slow = params.rate_percent < 85
        tts = gTTS(text=text, lang=self.lang, slow=slow)

        # Step 2: Save to temp mp3 first
        tmp_mp3 = str(out_path) + "_raw.mp3"
        tts.save(tmp_mp3)

        # Step 3: Try to apply prosody via ffmpeg if available
        # ffmpeg is available on Streamlit Cloud
        try:
            self._apply_ffmpeg_prosody(tmp_mp3, str(out_path), params)
            os.remove(tmp_mp3)
        except Exception as e:
            logger.warning("ffmpeg prosody failed (%s), using raw audio", e)
            # Fallback: just use the raw mp3
            import shutil
            shutil.move(tmp_mp3, str(out_path))

        # Save SSML
        ssml_path = ""
        if ssml:
            ssml_path = str(out_path).replace(".mp3", ".ssml")
            Path(ssml_path).write_text(ssml, encoding="utf-8")

        file_size = out_path.stat().st_size
        logger.info("Audio synthesised: %s | emotion=%s | rate=%d%%",
                    out_path.name, params.emotion, params.rate_percent)

        return AudioResult(
            file_path=str(out_path),
            duration_seconds=0.0,
            sample_rate=22050,
            file_size_bytes=file_size,
            engine_used="gtts+ffmpeg",
            ssml_path=ssml_path,
        )

    def _apply_ffmpeg_prosody(
        self, input_path: str, output_path: str, params: VoiceParameters
    ) -> None:
        """
        Use ffmpeg (available on Streamlit Cloud) to apply:
          - atempo: speed/rate change (0.5 to 2.0)
          - asetrate + aresample: pitch shift
          - volume: amplitude
        """
        import subprocess

        # Rate: convert percent to atempo factor (0.5–2.0 range)
        rate_factor = params.rate_percent / 100.0
        rate_factor = max(0.5, min(rate_factor, 2.0))

        # Pitch: semitones to frequency ratio
        # asetrate changes pitch by altering sample rate
        # then aresample restores original sample rate
        base_rate = 22050
        pitch_ratio = 2 ** (params.pitch_st / 12.0)
        pitched_rate = int(base_rate * pitch_ratio)

        # Volume: dB to linear factor
        vol_linear = 10 ** (params.volume_db / 20.0)
        vol_linear = max(0.3, min(vol_linear, 3.0))

        # Build ffmpeg filter chain
        # Order: pitch shift → speed → volume
        filter_chain = (
            f"asetrate={pitched_rate},"
            f"aresample={base_rate},"
            f"atempo={rate_factor:.3f},"
            f"volume={vol_linear:.3f}"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-af", filter_chain,
            "-codec:a", "libmp3lame",
            "-q:a", "4",
            output_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg error: {result.stderr[-200:]}")
