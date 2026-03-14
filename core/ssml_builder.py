"""
ssml_builder.py
---------------
Constructs SSML (Speech Synthesis Markup Language) from plain text
and VoiceParameters. SSML gives us fine-grained control over:

  • <prosody rate="…%" pitch="…st" volume="…dB">  – global envelope
  • <break time="…ms"/>                            – inter-sentence pauses
  • <emphasis level="…">                           – word-level stress
  • <say-as interpret-as="…">                      – dates, numbers, etc.

The resulting SSML is consumed by gTTS (basic) or any SSML-capable
TTS engine (Google Cloud TTS, ElevenLabs, etc.).

Note: gTTS v2 does NOT natively parse SSML. The SSML string produced
here is saved alongside the audio for reference / future use with
a full SSML-capable engine. We apply prosody at the pydub post-
processing stage instead.
"""

import re
from .voice_mapper import VoiceParameters


# ---------------------------------------------------------------------------
# Sentence splitter
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentences preserving terminal punctuation.
    Handles common abbreviations to avoid over-splitting.
    """
    abbrevs = r"\b(?:Mr|Ms|Mrs|Dr|Prof|Sr|Jr|vs|etc|approx|e\.g|i\.e)\."
    # Temporarily mask abbreviations
    masked = re.sub(abbrevs, lambda m: m.group().replace(".", "@@"), text)
    # Split on ., ! or ? followed by space + capital (or end of string)
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'])', masked)
    # Restore dots
    return [p.replace("@@", ".").strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# SSML builder
# ---------------------------------------------------------------------------

class SSMLBuilder:
    """
    Builds SSML markup from plain text and VoiceParameters.

    Usage:
        builder = SSMLBuilder()
        ssml = builder.build("Hello world!", params)
    """

    def build(self, text: str, params: VoiceParameters) -> str:
        """
        Construct full SSML document.

        Applies:
          1. Global prosody envelope (rate, pitch, volume)
          2. Per-sentence <break> tags scaled by pause_factor
          3. Emphasis wrapping for high-intensity emotions
        """
        sentences = _split_sentences(text)
        inner = self._build_inner(sentences, params)

        rate_str   = f"{params.rate_percent}%"
        pitch_str  = f"{'+' if params.pitch_st >= 0 else ''}{params.pitch_st}st"
        volume_str = f"{'+' if params.volume_db >= 0 else ''}{params.volume_db:.1f}dB"

        ssml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<speak xmlns="http://www.w3.org/2001/10/synthesis" version="1.1" '
            'xml:lang="en-US">\n'
            f'  <prosody rate="{rate_str}" pitch="{pitch_str}" volume="{volume_str}">\n'
            f'{inner}'
            "  </prosody>\n"
            "</speak>"
        )
        return ssml

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_inner(self, sentences: list[str], params: VoiceParameters) -> str:
        """Build the inner SSML content for a list of sentences."""
        parts = []
        break_ms = params.sentence_break_ms

        for i, sentence in enumerate(sentences):
            processed = self._apply_emphasis(sentence, params)
            processed = self._apply_say_as(processed)
            parts.append(f"    {processed}")
            # Add inter-sentence break except after the last sentence
            if i < len(sentences) - 1:
                parts.append(f'    <break time="{break_ms}ms"/>')
            # Excitement / anger: shorter pauses → already baked into break_ms
            # Sadness: longer pauses → already baked in

        return "\n".join(parts) + "\n"

    def _apply_emphasis(self, sentence: str, params: VoiceParameters) -> str:
        """
        Wrap high-intensity or naturally stressed words with <emphasis>.
        Only applies when emphasis level is 'strong' or 'moderate'.
        """
        if params.emphasis in ("none", "reduced"):
            return sentence

        level = params.emphasis  # "moderate" or "strong"

        # Identify capitalised words (implied stress by author) + exclamations
        def emphasise_match(m: re.Match) -> str:
            word = m.group(0)
            # Only emphasise if fully uppercase (intentional caps) or after !
            if word.isupper() and len(word) > 1:
                return f'<emphasis level="{level}">{word}</emphasis>'
            return word

        sentence = re.sub(r'\b[A-Z]{2,}\b', emphasise_match, sentence)
        return sentence

    def _apply_say_as(self, text: str) -> str:
        """
        Auto-wrap common patterns in <say-as> for natural pronunciation.
        Covers: dates (12/25/2024), times (3:30pm), currencies ($99.99).
        """
        # Currency
        text = re.sub(
            r'\$(\d[\d,]*\.?\d*)',
            lambda m: f'<say-as interpret-as="currency" language="en-US">${m.group(1)}</say-as>',
            text,
        )
        # Time
        text = re.sub(
            r'\b(\d{1,2}:\d{2}(?:\s?[aApP][mM])?)\b',
            lambda m: f'<say-as interpret-as="time" format="hms12">{m.group(1)}</say-as>',
            text,
        )
        # Date mm/dd/yyyy
        text = re.sub(
            r'\b(\d{1,2}/\d{1,2}/\d{2,4})\b',
            lambda m: f'<say-as interpret-as="date" format="mdy">{m.group(1)}</say-as>',
            text,
        )
        return text

    def plain_text_preview(self, ssml: str) -> str:
        """Strip SSML tags to produce readable plain text for debugging."""
        return re.sub(r'<[^>]+>', '', ssml).strip()
