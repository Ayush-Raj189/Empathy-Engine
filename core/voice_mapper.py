"""
voice_mapper.py
---------------
Maps detected emotions → concrete gTTS / SSML vocal parameters.

Each emotion has a BASE configuration. Intensity scaling (0–1) then
modulates each parameter proportionally within safe bounds.

Parameters exposed:
  • rate  : speaking speed expressed as a percentage string for gTTS-slow
  • pitch : semitone offset (+N higher, −N lower) — injected via SSML
  • volume : amplitude multiplier (applied via pydub)
  • pause_factor : multiplier on sentence-boundary pauses (SSML <break>)
  • emphasis : word-level emphasis strength ("none"|"reduced"|"moderate"|"strong")

SSML tags are constructed here and passed to the TTS engine.
"""

from dataclasses import dataclass
from typing import Dict


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class VoiceParameters:
    """Fully resolved vocal configuration for TTS synthesis."""
    emotion: str
    intensity: float
    # gTTS-level
    slow: bool          # gTTS only supports normal vs slow
    # SSML prosody
    rate_percent: int   # e.g. 120 → <prosody rate="120%">
    pitch_st: int       # semitones, applied as pitch="Nst"
    volume_db: float    # dB gain (pydub), positive = louder
    # Pacing
    pause_factor: float # multiplier on inter-sentence breaks (ms)
    sentence_break_ms: int
    # Emphasis
    emphasis: str       # "none" | "reduced" | "moderate" | "strong"
    # Colour / mood label for UI
    mood_color: str
    mood_icon: str


# ---------------------------------------------------------------------------
# Emotion → base parameter table
# ---------------------------------------------------------------------------

# Each entry: (rate_pct, pitch_st, volume_db, pause_factor, emphasis, color, icon)
_BASE: Dict[str, tuple] = {
    #            rate  pitch  vol  pause  emph          color        icon
    "joy":       (115, +2,    1.5,  0.85, "moderate",  "#F59E0B",   "😊"),
    "excitement":(135, +4,    3.0,  0.6,  "strong",    "#EF4444",   "🎉"),
    "gratitude": (100, +1,    1.0,  1.1,  "moderate",  "#10B981",   "🙏"),
    "sadness":   (78, -3,    -2.0,  1.5,  "reduced",   "#6366F1",   "😢"),
    "frustration":(108, -1,   2.5,  0.75, "strong",    "#F97316",   "😤"),
    "anger":     (118, -2,    4.0,  0.55, "strong",    "#DC2626",   "😠"),
    "fear":      (90,  -1,   -1.0,  1.2,  "moderate",  "#7C3AED",   "😨"),
    "surprise":  (128, +3,    2.0,  0.65, "strong",    "#0EA5E9",   "😲"),
    "curiosity": (103, +1,    0.5,  1.15, "moderate",  "#14B8A6",   "🤔"),
    "neutral":   (100,  0,    0.0,  1.0,  "none",      "#6B7280",   "😐"),
}

# Intensity scaling — how much each param can shift at max intensity
_INTENSITY_RANGE: Dict[str, tuple] = {
    #              Δrate  Δpitch  Δvol  Δpause
    "joy":         (+15,  +2,    +1.5,  -0.2),
    "excitement":  (+20,  +3,    +2.5,  -0.25),
    "gratitude":   (+5,   +1,    +0.5,  -0.1),
    "sadness":     (-15,  -3,    -1.5,  +0.4),
    "frustration": (+12,  -2,    +2.0,  -0.2),
    "anger":       (+18,  -3,    +3.0,  -0.25),
    "fear":        (-12,  -2,    -1.0,  +0.3),
    "surprise":    (+18,  +4,    +2.0,  -0.2),
    "curiosity":   (+8,   +2,    +0.5,  +0.1),
    "neutral":     (0,    0,     0.0,   0.0),
}


# ---------------------------------------------------------------------------
# Mapper
# ---------------------------------------------------------------------------

class VoiceMapper:
    """
    Converts an EmotionResult into fully resolved VoiceParameters.

    The mapping uses base values + intensity-proportional deltas so that
    "This is good" and "This is LITERALLY THE BEST NEWS EVER!!! 🎉" both
    map to 'joy' but with very different vocal output.
    """

    def map(self, emotion: str, intensity: float) -> VoiceParameters:
        """
        emotion   : primary emotion string (must be a key in _BASE)
        intensity : float in [0.0, 1.0]
        """
        emotion = emotion if emotion in _BASE else "neutral"
        base = _BASE[emotion]
        delta = _INTENSITY_RANGE[emotion]

        t = intensity  # shorthand

        rate   = int(base[0] + delta[0] * t)
        pitch  = int(base[1] + delta[1] * t)
        vol    = base[2] + delta[2] * t
        pause  = base[3] + delta[3] * t
        emph   = base[4]
        color  = base[5]
        icon   = base[6]

        # Clamp to sensible bounds
        rate   = max(60, min(rate, 180))
        pitch  = max(-8, min(pitch, +8))
        vol    = max(-6.0, min(vol, +8.0))
        pause  = max(0.3, min(pause, 2.5))

        # Escalate emphasis at high intensity
        if t > 0.75 and emph == "moderate":
            emph = "strong"
        elif t < 0.25 and emph == "strong":
            emph = "moderate"

        # Determine sentence break in ms
        sentence_break = int(400 * pause)

        return VoiceParameters(
            emotion=emotion,
            intensity=intensity,
            slow=(rate < 90),
            rate_percent=rate,
            pitch_st=pitch,
            volume_db=vol,
            pause_factor=pause,
            sentence_break_ms=sentence_break,
            emphasis=emph,
            mood_color=color,
            mood_icon=icon,
        )

    def describe(self, params: VoiceParameters) -> str:
        """Human-readable summary of what the voice will do."""
        lines = [
            f"🎙  Emotion    : {params.emotion.title()} (intensity {params.intensity:.0%})",
            f"⏱  Rate       : {params.rate_percent}% of normal speed",
            f"🎵  Pitch      : {'+'if params.pitch_st >= 0 else ''}{params.pitch_st} semitones",
            f"🔊  Volume     : {'+'if params.volume_db >= 0 else ''}{params.volume_db:.1f} dB",
            f"⏸  Pauses     : {params.pause_factor:.2f}× normal",
            f"💬  Emphasis   : {params.emphasis}",
        ]
        return "\n".join(lines)
