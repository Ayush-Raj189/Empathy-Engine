"""
pipeline.py
-----------
Orchestrates the full Empathy Engine pipeline:

  Text → EmotionDetector → VoiceMapper → SSMLBuilder → TTSEngine → AudioResult

This is the single public entry-point used by the Streamlit app and
any future API layer.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from .emotion_detector import EmotionDetector, EmotionResult
from .voice_mapper import VoiceMapper, VoiceParameters
from .ssml_builder import SSMLBuilder
from .tts_engine import TTSEngine, AudioResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pipeline result
# ---------------------------------------------------------------------------

@dataclass
class PipelineResult:
    """
    Complete result from one pipeline run, bundling all intermediate
    outputs so the UI can display every stage.
    """
    text: str
    emotion_result: EmotionResult
    voice_params: VoiceParameters
    ssml: str
    audio_result: AudioResult
    parameter_description: str


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class EmpathyPipeline:
    """
    Full Empathy Engine pipeline.

    Initialise once and call `process(text)` for each input.
    All components are lazily initialised on first use.
    """

    def __init__(self, output_dir: str = "audio_output", lang: str = "en"):
        self._output_dir = output_dir
        self._lang = lang

        self._detector: EmotionDetector | None = None
        self._mapper: VoiceMapper | None = None
        self._ssml_builder: SSMLBuilder | None = None
        self._tts: TTSEngine | None = None

    # ------------------------------------------------------------------
    # Lazy initialisation
    # ------------------------------------------------------------------

    @property
    def detector(self) -> EmotionDetector:
        if self._detector is None:
            self._detector = EmotionDetector()
        return self._detector

    @property
    def mapper(self) -> VoiceMapper:
        if self._mapper is None:
            self._mapper = VoiceMapper()
        return self._mapper

    @property
    def ssml_builder(self) -> SSMLBuilder:
        if self._ssml_builder is None:
            self._ssml_builder = SSMLBuilder()
        return self._ssml_builder

    @property
    def tts(self) -> TTSEngine:
        if self._tts is None:
            self._tts = TTSEngine(output_dir=self._output_dir, lang=self._lang)
        return self._tts

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, text: str, filename: str = "") -> PipelineResult:
        """
        Run the full pipeline on input text.

        Steps:
          1. Detect emotion + intensity
          2. Map to voice parameters
          3. Build SSML
          4. Synthesise audio
          5. Return bundled PipelineResult
        """
        logger.info("Pipeline: processing %d chars", len(text))

        # Step 1 — Emotion detection
        emotion_result: EmotionResult = self.detector.analyze(text)
        logger.info("Detected: %s @ %.2f intensity", emotion_result.primary_emotion, emotion_result.intensity)

        # Step 2 — Voice mapping
        voice_params: VoiceParameters = self.mapper.map(
            emotion_result.primary_emotion,
            emotion_result.intensity,
        )

        # Step 3 — SSML construction
        ssml: str = self.ssml_builder.build(text, voice_params)

        # Step 4 — TTS synthesis
        audio_result: AudioResult = self.tts.synthesise(
            text=text,
            params=voice_params,
            ssml=ssml,
            filename=filename,
        )

        # Step 5 — Human-readable parameter description
        param_desc = self.mapper.describe(voice_params)

        return PipelineResult(
            text=text,
            emotion_result=emotion_result,
            voice_params=voice_params,
            ssml=ssml,
            audio_result=audio_result,
            parameter_description=param_desc,
        )

    def process_batch(self, texts: list[str]) -> list[PipelineResult]:
        """Process multiple texts sequentially, returning a list of results."""
        return [self.process(t) for t in texts]
