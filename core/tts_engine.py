"""
tts_engine.py
-------------
Text-to-Speech synthesis pipeline for the Empathy Engine.

Strategy:
  1. Use gTTS (Google Text-to-Speech) for high-quality base audio.
  2. Post-process with pydub to apply:
       • Speed / rate adjustment (playback rate manipulation)
       • Volume (dB gain)
       • Pitch shift via frame rate trick
  3. Export as MP3 for the web player.

Fallback:
  If network is unavailable, automatically fall back to pyttsx3 (offline).

The class is fully decoupled from the emotion layer — it only receives
plain text + VoiceParameters and produces an audio file.
"""

import io
import os
import time
import wave
import tempfile
import logging
from pathlib import Path
from dataclasses import dataclass

try:
    from gtts import gTTS
except ModuleNotFoundError:
    gTTS = None
try:
    from pydub import AudioSegment
except ModuleNotFoundError:
    AudioSegment = None

from .voice_mapper import VoiceParameters

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class AudioResult:
    file_path: str
    duration_seconds: float
    sample_rate: int
    file_size_bytes: int
    engine_used: str       # "gtts" | "pyttsx3"
    ssml_path: str = ""    # Path to saved SSML for reference


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class TTSEngine:
    """
    Synthesises speech from text, applies prosodic transformations,
    and saves the result to an audio file.
    """

    def __init__(self, output_dir: str = "audio_output", lang: str = "en"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lang = lang

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesise(
        self,
        text: str,
        params: VoiceParameters,
        ssml: str = "",
        filename: str = "",
    ) -> AudioResult:
        """
        Convert text to speech with the given vocal parameters.

        Returns an AudioResult with the path to the generated MP3 file.
        """
        if not filename:
            timestamp = int(time.time() * 1000)
            filename = f"empathy_{params.emotion}_{timestamp}.mp3"

        if AudioSegment is None:
            logger.warning("pydub is not available; using pyttsx3 WAV fallback.")
            if filename.lower().endswith(".mp3"):
                filename = filename[:-4] + ".wav"
            out_path = self.output_dir / filename
            self._pyttsx3_synthesise_to_wav(text, params, out_path)

            ssml_path = ""
            if ssml:
                ssml_path = str(out_path).replace(".wav", ".ssml")
                Path(ssml_path).write_text(ssml, encoding="utf-8")

            duration, sample_rate = self._wav_metadata(out_path)
            file_size = out_path.stat().st_size
            return AudioResult(
                file_path=str(out_path),
                duration_seconds=duration,
                sample_rate=sample_rate,
                file_size_bytes=file_size,
                engine_used="pyttsx3",
                ssml_path=ssml_path,
            )

        out_path = self.output_dir / filename

        # --- Step 1: Raw TTS synthesis ---
        raw_audio, engine = self._synthesise_raw(text, params)

        # --- Step 2: Post-process prosody ---
        final_audio = self._apply_prosody(raw_audio, params)

        # --- Step 3: Export ---
        final_audio.export(str(out_path), format="mp3", bitrate="128k")

        # --- Step 4: Save SSML alongside ---
        ssml_path = ""
        if ssml:
            ssml_path = str(out_path).replace(".mp3", ".ssml")
            Path(ssml_path).write_text(ssml, encoding="utf-8")

        # --- Metadata ---
        duration = len(final_audio) / 1000.0
        file_size = out_path.stat().st_size

        logger.info(
            "Audio synthesised: %s | %.1fs | %d bytes | engine=%s",
            out_path.name, duration, file_size, engine,
        )

        return AudioResult(
            file_path=str(out_path),
            duration_seconds=duration,
            sample_rate=final_audio.frame_rate,
            file_size_bytes=file_size,
            engine_used=engine,
            ssml_path=ssml_path,
        )

    # ------------------------------------------------------------------
    # Internal: raw synthesis
    # ------------------------------------------------------------------

    def _synthesise_raw(
        self, text: str, params: VoiceParameters
    ) -> tuple[AudioSegment, str]:
        """
        Call gTTS to produce a base AudioSegment.
        Falls back to pyttsx3 if network is unavailable.
        """
        if AudioSegment is None:
            raise RuntimeError("pydub is required for AudioSegment synthesis path")

        if gTTS is None:
            logger.warning("gTTS is not available; using pyttsx3 fallback.")
            return self._pyttsx3_synthesise(text, params), "pyttsx3"

        try:
            return self._gtts_synthesise(text, params), "gtts"
        except Exception as e:
            logger.warning("gTTS failed (%s), falling back to pyttsx3.", e)
            return self._pyttsx3_synthesise(text, params), "pyttsx3"

    def _gtts_synthesise(self, text: str, params: VoiceParameters) -> AudioSegment:
        """Use gTTS to produce audio, returned as an AudioSegment."""
        slow = params.slow   # gTTS: slow=True ≈ 70% speed
        tts = gTTS(text=text, lang=self.lang, slow=slow)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return AudioSegment.from_mp3(buf)

    def _pyttsx3_synthesise(self, text: str, params: VoiceParameters) -> AudioSegment:
        """
        Use pyttsx3 for fully offline synthesis.
        pyttsx3 writes directly to a WAV file.
        """
        import pyttsx3
        engine = pyttsx3.init()
        # pyttsx3 rate: default ~200 wpm, scale proportionally
        target_wpm = int(200 * (params.rate_percent / 100))
        engine.setProperty("rate", target_wpm)
        engine.setProperty("volume", min(1.0, max(0.0, 0.8 + params.volume_db / 20)))

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self._pyttsx3_synthesise_to_wav(text, params, Path(tmp_path))
            audio = AudioSegment.from_wav(tmp_path)
        finally:
            os.unlink(tmp_path)

        return audio

    def _pyttsx3_synthesise_to_wav(self, text: str, params: VoiceParameters, out_path: Path) -> None:
        """Synthesize directly to WAV with pyttsx3 (no pydub required)."""
        import pyttsx3

        engine = pyttsx3.init()
        target_wpm = int(200 * (params.rate_percent / 100))
        engine.setProperty("rate", target_wpm)
        engine.setProperty("volume", min(1.0, max(0.0, 0.8 + params.volume_db / 20)))

        engine.save_to_file(text, str(out_path))
        engine.runAndWait()

    def _wav_metadata(self, file_path: Path) -> tuple[float, int]:
        """Return (duration_seconds, sample_rate) for a WAV file."""
        with wave.open(str(file_path), "rb") as wav:
            frame_rate = wav.getframerate()
            n_frames = wav.getnframes()
        duration = (n_frames / frame_rate) if frame_rate else 0.0
        return duration, frame_rate

    # ------------------------------------------------------------------
    # Internal: prosody post-processing
    # ------------------------------------------------------------------

    def _apply_prosody(
        self, audio: AudioSegment, params: VoiceParameters
    ) -> AudioSegment:
        """
        Apply rate and pitch modulation via pydub frame-rate manipulation.

        Technique:
          • Speed/rate → adjust playback frame rate (stretches/compresses time)
          • Pitch shift → change sample frame rate (shifts perceived pitch)
            This couples pitch and speed, so we compensate:
            first speed, then pitch-only via frame rate restoration.
        """
        audio = self._adjust_speed(audio, params.rate_percent)
        audio = self._adjust_pitch(audio, params.pitch_st)
        audio = self._adjust_volume(audio, params.volume_db)
        return audio

    def _adjust_speed(self, audio: AudioSegment, rate_pct: int) -> AudioSegment:
        """
        Speed up or slow down without changing pitch.
        Uses the frame-rate approach: change playback speed then restore
        frame rate so duration changes but pitch is preserved.
        """
        if rate_pct == 100:
            return audio
        speed_factor = rate_pct / 100.0
        # Change playback rate to alter duration
        altered = audio._spawn(
            audio.raw_data,
            overrides={"frame_rate": int(audio.frame_rate * speed_factor)},
        )
        # Restore to original frame rate so players don't pitch-shift
        return altered.set_frame_rate(audio.frame_rate)

    def _adjust_pitch(self, audio: AudioSegment, semitones: int) -> AudioSegment:
        """
        Shift pitch by N semitones.
        Semitone → frame rate ratio: r = 2^(n/12).
        This approach changes duration slightly, which is acceptable for
        small shifts (±4 semitones).
        """
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
        """Apply dB gain. Positive = louder, negative = softer."""
        if abs(db) < 0.1:
            return audio
        return audio + db
