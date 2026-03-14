# 🎙️ The Empathy Engine
### *Giving AI a Human Voice — Emotionally Expressive Speech Synthesis*

---

## ✨ Overview

The **Empathy Engine** is a full-stack AI service that dynamically modulates the vocal characteristics of synthesised speech based on the detected emotion of input text. It bridges the gap between text-based sentiment and expressive, human-like audio output — moving far beyond monotonic delivery to achieve genuine emotional resonance.

> **"This is good"** → slight pitch lift, +5% speed  
> **"This is LITERALLY THE BEST NEWS EVER!!!"** → +35% speed, +4 semitones, +3dB volume

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EMPATHY ENGINE                           │
│                                                                 │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────────┐ │
│  │    INPUT    │──▶│    DETECT    │──▶│   MAP PARAMETERS     │ │
│  │  Text/API   │   │  Emotion +   │   │  rate / pitch /      │ │
│  │  CLI/Web    │   │  Intensity   │   │  volume / pauses     │ │
│  └─────────────┘   │  VADER +     │   │  + emphasis          │ │
│                    │  TextBlob +  │   └──────────┬───────────┘ │
│                    │  Keywords    │              │             │
│                    └──────────────┘   ┌──────────▼───────────┐ │
│                                       │    BUILD SSML        │ │
│                                       │  prosody + breaks    │ │
│                                       │  + say-as + emphasis │ │
│                                       └──────────┬───────────┘ │
│                                                  │             │
│  ┌──────────────────────────────────────────────▼───────────┐ │
│  │                     TTS ENGINE                            │ │
│  │  gTTS (online)  ──▶  raw audio  ──▶  pydub post-proc    │ │
│  │  pyttsx3 (offline fallback)          rate / pitch / vol  │ │
│  │                                      ──▶  MP3 output     │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
empathy_engine/
│
├── app.py                   # 🌐 Streamlit web interface
├── cli.py                   # 💻 Command-line interface
├── requirements.txt         # 📦 Python dependencies
│
├── core/                    # 🧠 Core processing modules
│   ├── __init__.py
│   ├── emotion_detector.py  # Multi-model emotion detection
│   ├── voice_mapper.py      # Emotion → vocal parameters
│   ├── ssml_builder.py      # SSML markup generation
│   ├── tts_engine.py        # TTS synthesis + pydub post-proc
│   └── pipeline.py          # Orchestration & public API
│
├── utils/                   # 🛠 Utilities
│   ├── __init__.py
│   └── samples.py           # Curated demo texts
│
└── audio_output/            # 🎵 Generated audio files
```

---

## 🎭 Supported Emotions (10 categories)

| Emotion | Icon | Rate | Pitch | Volume | Emphasis |
|---------|------|------|-------|--------|----------|
| Joy | 😊 | +15% | +2st | +1.5dB | Moderate |
| **Excitement** | 🎉 | **+35%** | **+4st** | **+3dB** | **Strong** |
| Gratitude | 🙏 | Normal | +1st | +1dB | Moderate |
| Sadness | 😢 | −22% | −3st | −2dB | Reduced |
| Frustration | 😤 | +8% | −1st | +2.5dB | Strong |
| **Anger** | 😠 | **+18%** | **−2st** | **+4dB** | **Strong** |
| Fear | 😨 | −10% | −1st | −1dB | Moderate |
| Surprise | 😲 | +28% | +3st | +2dB | Strong |
| Curiosity | 🤔 | +3% | +1st | +0.5dB | Moderate |
| Neutral | 😐 | Normal | 0st | 0dB | None |

Values shown are at **maximum intensity (1.0)**. At lower intensities, parameters scale proportionally — this is the **intensity scaling bonus feature**.

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
cd empathy_engine
pip install -r requirements.txt
```

### 2. Launch the web UI

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

### 3. Use the CLI

```bash
# Single text
python cli.py "We just got the contract! This is AMAZING!!!"

# Use a built-in sample
python cli.py --sample excitement

# Interactive mode
python cli.py --interactive

# Batch processing
python cli.py --batch my_texts.txt

# JSON output (for pipelines)
python cli.py "Hello world" --json

# Verbose output
python cli.py "I'm so frustrated!" --verbose
```

### 4. Use as a Python library

```python
from core import EmpathyPipeline

pipeline = EmpathyPipeline(output_dir="./audio_output")

result = pipeline.process("We just won the contract!!! This is AMAZING!")

print(result.emotion_result.primary_emotion)   # excitement
print(result.emotion_result.intensity)          # 0.87
print(result.voice_params.rate_percent)         # 152
print(result.audio_result.file_path)            # audio_output/empathy_excitement_...mp3
```

---

## 🎁 Bonus Features Implemented

| Feature | Status | Details |
|---------|--------|---------|
| ✅ Granular Emotions | Implemented | 10 categories vs. required 3 |
| ✅ Intensity Scaling | Implemented | Continuous 0.1→1.0 scale, proportional parameter modulation |
| ✅ Web Interface | Implemented | Streamlit with glassmorphism design + Plotly charts |
| ✅ SSML Integration | Implemented | Prosody, breaks, emphasis, say-as; saved alongside each audio |
| 🎁 Radar Chart | Extra | Full emotion probability radar chart |
| 🎁 Intensity Gauge | Extra | Real-time Plotly gauge |
| 🎁 Parameter Bars | Extra | Visual parameter comparison chart |
| 🎁 CLI REPL | Extra | Interactive command-line interface |
| 🎁 Session History | Extra | Sidebar tracks last 5 syntheses |
| 🎁 JSON API mode | Extra | `--json` flag for pipeline integration |
| 🎁 Batch processing | Extra | Process files of texts in one command |
| 🎁 Offline fallback | Extra | pyttsx3 fallback when network unavailable |
| 🎁 SSML download | Extra | SSML file saved alongside every audio |

---

## 🔬 Technical Deep-Dive

### Emotion Detection Pipeline

```
Text
  │
  ├─▶ VADER SentimentIntensityAnalyzer
  │     └─▶ compound, pos, neg, neu scores
  │
  ├─▶ TextBlob
  │     └─▶ polarity (-1→+1), subjectivity (0→1)
  │
  ├─▶ Keyword Heuristic Engine
  │     ├─▶ 10 emotion lexicons (~150 keywords)
  │     ├─▶ Negation detection (2-word window)
  │     └─▶ Phrase matching (higher weight)
  │
  └─▶ Fusion Layer (weights: keyword 50%, VADER 35%, TextBlob 15%)
        └─▶ Normalised probability distribution over 10 emotions
```

### Intensity Calculation

```
intensity = (|VADER compound| × 0.5)
          + (caps_ratio × 0.2)
          + (punctuation_density × 0.2)
          + (intensifier_fraction × 0.1)
```

### Audio Post-Processing

```
gTTS MP3 → AudioSegment
  │
  ├─▶ Speed adjustment (frame_rate × speed_factor → restore frame_rate)
  ├─▶ Pitch shift (frame_rate × 2^(n/12) → restore frame_rate)
  └─▶ Volume gain (pydub dB addition)
        └─▶ Export MP3 @ 128kbps
```

---

## 📋 Requirements

- Python 3.10+
- Internet connection for gTTS (falls back to pyttsx3 offline)
- ~500MB disk space for ML model downloads (first run only)

---

## 🛣️ Roadmap / Future Enhancements

- [ ] ElevenLabs API integration for hyper-realistic voices
- [ ] Real-time streaming synthesis
- [ ] REST API (FastAPI) for production deployment
- [ ] Multi-language emotion detection
- [ ] Fine-tuned transformer model for domain-specific emotion (customer service)
- [ ] Voice cloning support

---

*Built with ❤️ for the Empathy Engine Challenge*
