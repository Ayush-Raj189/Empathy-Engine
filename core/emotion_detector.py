"""
emotion_detector.py
-------------------
Core emotion detection engine for the Empathy Engine.
Uses a multi-layered approach:
  1. VADER for fast sentiment scoring
  2. TextBlob for subjectivity & polarity backup
  3. Keyword-heuristic rules for nuanced emotion tagging
  4. Intensity scaling based on punctuation, capitalization, and lexical cues

Supported Emotions (Granular, Bonus):
  joy, excitement, gratitude, sadness, frustration, anger,
  fear, surprise, curiosity, neutral
"""

import re
import math
import logging
from dataclasses import dataclass, field
from typing import Dict, Tuple

try:
    from textblob import TextBlob
except ModuleNotFoundError:
    TextBlob = None

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ModuleNotFoundError:
    SentimentIntensityAnalyzer = None


logger = logging.getLogger(__name__)


class _FallbackSentimentIntensityAnalyzer:
    """Minimal VADER-compatible fallback built from TextBlob polarity."""

    def polarity_scores(self, text: str) -> Dict[str, float]:
        polarity, _ = _get_textblob_sentiment(text)
        compound = max(-1.0, min(1.0, polarity))

        if compound >= 0:
            pos = compound
            neg = 0.0
        else:
            pos = 0.0
            neg = abs(compound)

        neu = max(0.0, 1.0 - (pos + neg))
        return {
            "neg": neg,
            "neu": neu,
            "pos": pos,
            "compound": compound,
        }


def _get_textblob_sentiment(text: str) -> Tuple[float, float]:
    """Return (polarity, subjectivity), with safe neutral fallback."""
    if TextBlob is None:
        return 0.0, 0.0
    blob = TextBlob(text)
    return float(blob.sentiment.polarity), float(blob.sentiment.subjectivity)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class EmotionResult:
    """Complete emotion analysis result for a piece of text."""
    primary_emotion: str
    emotion_scores: Dict[str, float]
    intensity: float            # 0.0 (mild) → 1.0 (extreme)
    valence: float              # -1.0 (negative) → +1.0 (positive)
    subjectivity: float         # 0.0 (objective) → 1.0 (subjective)
    raw_vader: Dict[str, float] = field(default_factory=dict)
    explanation: str = ""


# ---------------------------------------------------------------------------
# Emotion lexicons & patterns
# ---------------------------------------------------------------------------

EMOTION_KEYWORDS: Dict[str, list] = {
    "joy": [
        "happy", "joyful", "delighted", "wonderful", "great", "love",
        "amazing", "beautiful", "fantastic", "pleased", "glad", "yay",
        "hooray", "cheers", "blessed", "thankful", "proud", "thrilled",
    ],
    "excitement": [
        "excited", "thrilled", "can't wait", "awesome", "incredible",
        "unbelievable", "wow", "omg", "oh my", "pumped", "stoked",
        "ecstatic", "overjoyed", "elated", "euphoric", "best ever",
    ],
    "gratitude": [
        "thank you", "thanks", "grateful", "appreciate", "thankful",
        "much obliged", "bless you", "gratitude", "deeply thankful",
    ],
    "sadness": [
        "sad", "unhappy", "depressed", "down", "upset", "cry", "crying",
        "tears", "heartbroken", "grief", "loss", "miss", "lonely",
        "miserable", "devastated", "sorrowful", "disappointed",
    ],
    "frustration": [
        "frustrated", "annoying", "annoyed", "irritated", "fed up",
        "can't stand", "this is ridiculous", "not working", "broken",
        "terrible service", "awful", "hate this", "ugh", "argh",
    ],
    "anger": [
        "angry", "furious", "enraged", "livid", "outraged", "furious",
        "rage", "mad", "infuriated", "disgusted", "unacceptable",
        "ridiculous", "absurd", "terrible", "never again",
    ],
    "fear": [
        "scared", "afraid", "terrified", "nervous", "anxious", "worried",
        "fear", "dread", "panic", "frightened", "horrified", "uneasy",
    ],
    "surprise": [
        "surprised", "shocked", "astonished", "astounded", "stunned",
        "can't believe", "unbelievable", "no way", "what?!", "really?",
        "seriously?", "unexpected", "out of nowhere",
    ],
    "curiosity": [
        "wondering", "curious", "interesting", "fascinating", "how does",
        "why does", "what if", "i wonder", "tell me more", "could you explain",
        "i'd like to know", "question", "explain",
    ],
}

NEGATION_WORDS = {"not", "no", "never", "neither", "nothing", "nobody", "nowhere",
                  "don't", "doesn't", "didn't", "won't", "wouldn't", "can't",
                  "couldn't", "shouldn't", "isn't", "aren't", "wasn't", "weren't"}

INTENSIFIERS = {"very", "extremely", "incredibly", "absolutely", "totally",
                "completely", "utterly", "so", "really", "truly", "deeply",
                "seriously", "quite", "rather", "awfully", "terribly"}


# ---------------------------------------------------------------------------
# Intensity analysers
# ---------------------------------------------------------------------------

def _caps_ratio(text: str) -> float:
    """Fraction of alphabetic characters that are uppercase."""
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return 0.0
    return sum(1 for c in alpha if c.isupper()) / len(alpha)


def _punctuation_intensity(text: str) -> float:
    """Score from exclamation marks, question marks, ellipsis, etc."""
    score = 0.0
    score += min(text.count("!") * 0.15, 0.45)
    score += min(text.count("?") * 0.08, 0.24)
    score += min(text.count("...") * 0.05, 0.15)
    return min(score, 0.6)


def _intensifier_count(tokens: list) -> float:
    """Fraction of tokens that are intensifiers, capped."""
    count = sum(1 for t in tokens if t.lower() in INTENSIFIERS)
    return min(count * 0.12, 0.36)


def _keyword_scores(text: str) -> Dict[str, float]:
    """
    Score each emotion category based on keyword presence.
    Handles basic negation by flipping polarity.
    """
    lower_text = text.lower()
    tokens = re.findall(r"\b\w+\b", lower_text)
    scores: Dict[str, float] = {e: 0.0 for e in EMOTION_KEYWORDS}

    for i, token in enumerate(tokens):
        # Simple 2-word negation window
        negated = any(tokens[max(0, i - 2): i].count(n) > 0 for n in NEGATION_WORDS)
        for emotion, keywords in EMOTION_KEYWORDS.items():
            for kw in keywords:
                if kw in lower_text:
                    base = 0.3 if " " in kw else 0.2   # phrase hits score more
                    scores[emotion] += -base if negated else base

    # Normalise so highest possible raw score ~ 1.0
    for e in scores:
        scores[e] = max(0.0, min(scores[e], 1.0))

    return scores


# ---------------------------------------------------------------------------
# Main detector class
# ---------------------------------------------------------------------------

class EmotionDetector:
    """
    Multi-model emotion detector with intensity scaling.

    Pipeline:
        text → VADER sentiment → TextBlob polarity/subjectivity
             → keyword heuristic scores
             → fusion & ranking
             → intensity calculation
    """

    def __init__(self):
        if SentimentIntensityAnalyzer is None:
            logger.warning(
                "vaderSentiment is not available; using TextBlob fallback sentiment analyzer."
            )
            self.vader = _FallbackSentimentIntensityAnalyzer()
        else:
            self.vader = SentimentIntensityAnalyzer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, text: str) -> EmotionResult:
        """
        Full emotion analysis. Returns an EmotionResult with primary
        emotion, all scores, intensity (0-1), and valence.
        """
        text = text.strip()
        if not text:
            return self._neutral_result()

        # --- Layer 1: VADER ---
        vader_scores = self.vader.polarity_scores(text)
        compound = vader_scores["compound"]  # -1.0 to +1.0

        # --- Layer 2: TextBlob ---
        tb_polarity, tb_subjectivity = _get_textblob_sentiment(text)

        # --- Layer 3: Keyword heuristics ---
        kw_scores = _keyword_scores(text)

        # --- Layer 4: Fuse signals ---
        emotion_scores = self._fuse_scores(vader_scores, tb_polarity, kw_scores)

        # --- Intensity ---
        tokens = re.findall(r"\b\w+\b", text)
        intensity = self._compute_intensity(text, tokens, vader_scores)

        # --- Primary emotion ---
        primary = max(emotion_scores, key=emotion_scores.get)

        # --- Explanation ---
        explanation = self._build_explanation(
            primary, emotion_scores, vader_scores, intensity
        )

        return EmotionResult(
            primary_emotion=primary,
            emotion_scores=emotion_scores,
            intensity=intensity,
            valence=float(compound),
            subjectivity=float(tb_subjectivity),
            raw_vader=vader_scores,
            explanation=explanation,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fuse_scores(
        self,
        vader: Dict[str, float],
        tb_polarity: float,
        kw: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Combine VADER compound, TextBlob polarity, and keyword scores.
        Weights: keyword 50%, VADER-derived 35%, TextBlob 15%.
        """
        compound = vader["compound"]
        neg = vader["neg"]
        pos = vader["pos"]
        neu = vader["neu"]

        scores = dict(kw)

        # VADER boosts
        if compound >= 0.6:
            scores["excitement"] += 0.3
            scores["joy"] += 0.2
        elif compound >= 0.3:
            scores["joy"] += 0.25
            scores["gratitude"] += 0.1
        elif compound <= -0.6:
            scores["anger"] += 0.2
            scores["frustration"] += 0.3
        elif compound <= -0.3:
            scores["sadness"] += 0.2
            scores["frustration"] += 0.15
        elif abs(compound) < 0.1 and neu > 0.7:
            scores["neutral"] = scores.get("neutral", 0.0) + 0.35

        # TextBlob polarity refinements
        if tb_polarity > 0.5:
            scores["joy"] += 0.1
        elif tb_polarity < -0.5:
            scores["frustration"] += 0.1

        # Guarantee neutral has a floor so it can win when nothing else fires
        scores.setdefault("neutral", 0.0)
        if all(v < 0.15 for e, v in scores.items() if e != "neutral"):
            scores["neutral"] = max(scores["neutral"], 0.4)

        # Clip all to [0, 1]
        for e in scores:
            scores[e] = max(0.0, min(scores[e], 1.0))

        # Normalise to sum = 1 for probability-like display
        total = sum(scores.values()) or 1.0
        scores = {e: v / total for e, v in scores.items()}

        return scores

    def _compute_intensity(
        self, text: str, tokens: list, vader: Dict[str, float]
    ) -> float:
        """
        Intensity combines:
          • VADER compound magnitude
          • Caps ratio
          • Punctuation density
          • Intensifier count
        → scaled to [0.1, 1.0]
        """
        vader_mag = abs(vader["compound"])
        caps = _caps_ratio(text) * 0.4
        punct = _punctuation_intensity(text)
        intensify = _intensifier_count(tokens)

        raw = (vader_mag * 0.5) + (caps * 0.2) + (punct * 0.2) + (intensify * 0.1)
        return max(0.1, min(raw, 1.0))

    def _build_explanation(
        self,
        primary: str,
        scores: Dict[str, float],
        vader: Dict[str, float],
        intensity: float,
    ) -> str:
        top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        top3_str = ", ".join(f"{e} ({v:.0%})" for e, v in top3)
        intensity_label = (
            "mild" if intensity < 0.35 else
            "moderate" if intensity < 0.65 else
            "strong" if intensity < 0.85 else
            "very intense"
        )
        return (
            f"Primary emotion: {primary} | Intensity: {intensity_label} "
            f"({intensity:.2f}) | Top emotions: {top3_str} | "
            f"VADER compound: {vader['compound']:.2f}"
        )

    def _neutral_result(self) -> EmotionResult:
        return EmotionResult(
            primary_emotion="neutral",
            emotion_scores={"neutral": 1.0},
            intensity=0.1,
            valence=0.0,
            subjectivity=0.0,
            explanation="Empty input — defaulting to neutral.",
        )
