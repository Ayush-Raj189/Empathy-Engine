"""
app.py
------
Streamlit web interface for the Empathy Engine.

Design philosophy: Dark-mode neural aesthetic — deep navy/slate backdrop,
electric accent colours keyed to each emotion, glassmorphism cards,
animated waveform visualisations, and a radical left-panel architecture.
"""

import sys
import os
import time
import base64
import logging
from pathlib import Path
from dotenv import load_dotenv

# ── Make local modules importable ──────────────────────────────────────────
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from core.pipeline import EmpathyPipeline, PipelineResult
from utils.samples import SAMPLES, get_all_labels

logging.basicConfig(level=logging.INFO)

# ── Page configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Empathy Engine",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Emotion palette (mirrors voice_mapper.py) ───────────────────────────────
EMOTION_META = {
    "joy":         {"color": "#F59E0B", "bg": "#1a1500", "icon": "😊", "label": "Joy"},
    "excitement":  {"color": "#EF4444", "bg": "#1a0000", "icon": "🎉", "label": "Excitement"},
    "gratitude":   {"color": "#10B981", "bg": "#001a0d", "icon": "🙏", "label": "Gratitude"},
    "sadness":     {"color": "#6366F1", "bg": "#05051a", "icon": "😢", "label": "Sadness"},
    "frustration": {"color": "#F97316", "bg": "#1a0800", "icon": "😤", "label": "Frustration"},
    "anger":       {"color": "#DC2626", "bg": "#1a0000", "icon": "😠", "label": "Anger"},
    "fear":        {"color": "#7C3AED", "bg": "#0d0019", "icon": "😨", "label": "Fear"},
    "surprise":    {"color": "#0EA5E9", "bg": "#00111a", "icon": "😲", "label": "Surprise"},
    "curiosity":   {"color": "#14B8A6", "bg": "#00141a", "icon": "🤔", "label": "Curiosity"},
    "neutral":     {"color": "#94A3B8", "bg": "#0d0d0d", "icon": "😐", "label": "Neutral"},
}


# ── CSS ─────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&family=Playfair+Display:ital,wght@0,700;1,500&display=swap');

/* ── Root Variables ── */
:root {
  --bg-primary: #09090f;
  --bg-secondary: #0f0f1a;
  --bg-card: rgba(255,255,255,0.04);
  --bg-card-hover: rgba(255,255,255,0.07);
  --border: rgba(255,255,255,0.08);
  --border-accent: rgba(255,255,255,0.15);
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted: #475569;
  --accent: #6366f1;
  --accent-glow: rgba(99,102,241,0.3);
  --font-body: 'Space Grotesk', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --font-display: 'Playfair Display', serif;
  --radius-sm: 8px;
  --radius-md: 14px;
  --radius-lg: 20px;
  --radius-xl: 28px;
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.4);
  --shadow-md: 0 8px 32px rgba(0,0,0,0.5);
  --shadow-lg: 0 20px 60px rgba(0,0,0,0.6);
  --transition: 0.22s cubic-bezier(0.4,0,0.2,1);
}

/* ── Global Reset ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, .stApp {
  background: var(--bg-primary) !important;
  font-family: var(--font-body) !important;
  color: var(--text-primary) !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0b0b18 0%, #0d0d20 100%) !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * {
  color: var(--text-primary) !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stRadio label {
  color: var(--text-secondary) !important;
  font-size: 0.78rem !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }

/* ── Main container ── */
.main .block-container {
  padding: 2rem 2.5rem !important;
  max-width: 1400px !important;
}

/* ── Hero banner ── */
.hero-banner {
  position: relative;
  padding: 3.5rem 3rem;
  border-radius: var(--radius-xl);
  background: linear-gradient(135deg,
    rgba(99,102,241,0.12) 0%,
    rgba(139,92,246,0.08) 40%,
    rgba(14,165,233,0.06) 100%
  );
  border: 1px solid rgba(99,102,241,0.25);
  margin-bottom: 2.5rem;
  overflow: hidden;
}
.hero-banner::before {
  content: '';
  position: absolute;
  top: -60%;
  left: -20%;
  width: 60%;
  height: 200%;
  background: radial-gradient(ellipse, rgba(99,102,241,0.08) 0%, transparent 70%);
  pointer-events: none;
}
.hero-banner::after {
  content: '';
  position: absolute;
  bottom: -40%;
  right: -10%;
  width: 50%;
  height: 150%;
  background: radial-gradient(ellipse, rgba(14,165,233,0.06) 0%, transparent 70%);
  pointer-events: none;
}
.hero-title {
  font-family: var(--font-display) !important;
  font-size: 3.2rem !important;
  font-weight: 700 !important;
  line-height: 1.1 !important;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #f1f5f9 0%, #94a3b8 60%, #6366f1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0 0 0.6rem 0;
}
.hero-subtitle {
  font-size: 1.1rem;
  color: var(--text-secondary);
  font-weight: 300;
  letter-spacing: 0.02em;
  max-width: 580px;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 100px;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.3);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #818cf8;
  font-family: var(--font-mono);
  margin-bottom: 1.2rem;
}

/* ── Glass cards ── */
.glass-card {
  background: var(--bg-card);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1.8rem;
  transition: border-color var(--transition), background var(--transition);
}
.glass-card:hover {
  border-color: var(--border-accent);
  background: var(--bg-card-hover);
}

/* ── Emotion indicator pill ── */
.emotion-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: 100px;
  font-weight: 600;
  font-size: 0.95rem;
  letter-spacing: 0.02em;
  border: 1px solid;
}

/* ── Parameter row ── */
.param-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.param-row:last-child { border-bottom: none; }
.param-label {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.param-value {
  font-family: var(--font-mono);
  font-size: 0.88rem;
  color: var(--text-primary);
  font-weight: 500;
}

/* ── Progress bar override ── */
.stProgress > div > div > div > div {
  background: linear-gradient(90deg, #6366f1, #8b5cf6) !important;
  border-radius: 4px !important;
}

/* ── Textarea ── */
.stTextArea textarea {
  background: rgba(15,15,35,0.8) !important;
  border: 1px solid var(--border-accent) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text-primary) !important;
  font-family: var(--font-body) !important;
  font-size: 1rem !important;
  line-height: 1.65 !important;
  transition: border-color var(--transition), box-shadow var(--transition);
}
.stTextArea textarea:focus {
  border-color: #6366f1 !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}

/* ── Button overrides ── */
.stButton > button {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
  color: white !important;
  border: none !important;
  border-radius: var(--radius-md) !important;
  font-family: var(--font-body) !important;
  font-size: 0.95rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.04em !important;
  padding: 0.7rem 2rem !important;
  transition: opacity var(--transition), transform var(--transition), box-shadow var(--transition) !important;
  box-shadow: 0 4px 20px rgba(99,102,241,0.35) !important;
}
.stButton > button:hover {
  opacity: 0.88 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 8px 30px rgba(99,102,241,0.45) !important;
}
.stButton > button:active {
  transform: translateY(0) !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
  background: rgba(15,15,35,0.9) !important;
  border: 1px solid var(--border-accent) !important;
  border-radius: var(--radius-sm) !important;
  color: var(--text-primary) !important;
}

/* ── Audio player ── */
audio {
  width: 100%;
  border-radius: var(--radius-md);
  filter: invert(1) hue-rotate(180deg) brightness(0.85);
}

/* ── Section headers ── */
.section-header {
  font-size: 0.7rem;
  font-family: var(--font-mono);
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 0.8rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}

/* ── Metric boxes ── */
.metric-box {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 1.2rem 1.4rem;
  text-align: center;
}
.metric-box .metric-value {
  font-size: 2rem;
  font-weight: 700;
  font-family: var(--font-mono);
  line-height: 1;
  margin-bottom: 0.3rem;
}
.metric-box .metric-label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}

/* ── SSML code block ── */
.ssml-block {
  background: #080810;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 1.2rem;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #7dd3fc;
  overflow-x: auto;
  max-height: 280px;
  overflow-y: auto;
  line-height: 1.7;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #6366f1 !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: transparent !important;
  gap: 4px;
  border-bottom: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text-muted) !important;
  font-family: var(--font-body) !important;
  font-size: 0.85rem !important;
  padding: 8px 16px !important;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
  border: none !important;
  transition: color var(--transition) !important;
}
.stTabs [aria-selected="true"] {
  background: rgba(99,102,241,0.12) !important;
  color: #818cf8 !important;
  border-bottom: 2px solid #6366f1 !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Sidebar logo ── */
.sidebar-logo {
  text-align: center;
  padding: 1.5rem 1rem;
  border-bottom: 1px solid var(--border);
  margin-bottom: 1rem;
}
.sidebar-logo-icon {
  font-size: 2.5rem;
  display: block;
  margin-bottom: 0.4rem;
}
.sidebar-logo-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.05em;
}
.sidebar-logo-version {
  font-size: 0.7rem;
  font-family: var(--font-mono);
  color: var(--text-muted);
  letter-spacing: 0.1em;
}

/* ── History item ── */
.history-item {
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color var(--transition), background var(--transition);
  background: var(--bg-card);
}
.history-item:hover {
  border-color: var(--border-accent);
  background: var(--bg-card-hover);
}

/* ── Alert/info boxes ── */
.info-box {
  background: rgba(99,102,241,0.08);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: var(--radius-sm);
  padding: 0.8rem 1rem;
  font-size: 0.84rem;
  color: #c7d2fe;
  line-height: 1.6;
}

/* ── Pipeline steps ── */
.pipeline-step {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}
.pipeline-step:last-child { border-bottom: none; }
.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(99,102,241,0.15);
  border: 1px solid rgba(99,102,241,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-family: var(--font-mono);
  color: #818cf8;
  flex-shrink: 0;
}
.step-content { flex: 1; }
.step-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
}
.step-desc {
  font-size: 0.78rem;
  color: var(--text-muted);
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-accent); border-radius: 2px; }

/* ── Animations ── */
@keyframes pulse-glow {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
@keyframes slide-up {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-slide-up { animation: slide-up 0.4s ease-out both; }

</style>
""", unsafe_allow_html=True)


# ── Session state ───────────────────────────────────────────────────────────
def init_session():
    if "pipeline" not in st.session_state:
        output_dir_env = os.getenv("EMPATHY_OUTPUT_DIR", "audio_output")
        output_dir_path = Path(output_dir_env)
        if not output_dir_path.is_absolute():
            output_dir_path = BASE_DIR / output_dir_path

        lang = os.getenv("EMPATHY_LANG", "en")
        st.session_state.pipeline = EmpathyPipeline(
            output_dir=str(output_dir_path),
            lang=lang,
        )
    if "history" not in st.session_state:
        st.session_state.history = []
    if "last_result" not in st.session_state:
        st.session_state.last_result = None


# ── Helper: encode audio to base64 ─────────────────────────────────────────
def audio_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ── Plotly: radar chart for emotion scores ──────────────────────────────────
def emotion_radar(scores: dict, accent_color: str) -> go.Figure:
  def _to_rgba(color: str, alpha: float = 0.15) -> str:
    color = color.strip()
    if color.startswith("#") and len(color) == 7:
      r = int(color[1:3], 16)
      g = int(color[3:5], 16)
      b = int(color[5:7], 16)
      return f"rgba({r},{g},{b},{alpha})"
    if color.startswith("rgb(") and color.endswith(")"):
      return color.replace("rgb(", "rgba(").replace(")", f",{alpha})")
    if color.startswith("rgba(") and color.endswith(")"):
      parts = [p.strip() for p in color[5:-1].split(",")]
      if len(parts) >= 3:
        return f"rgba({parts[0]},{parts[1]},{parts[2]},{alpha})"
    return f"rgba(99,102,241,{alpha})"

  emotions = list(scores.keys())
  values = [round(v * 100, 1) for v in scores.values()]
  # Close the polygon
  emotions += [emotions[0]]
  values += [values[0]]

  fig = go.Figure(go.Scatterpolar(
    r=values,
    theta=emotions,
    fill='toself',
    fillcolor=_to_rgba(accent_color, 0.15),
    line=dict(color=accent_color, width=2),
    marker=dict(color=accent_color, size=5),
  ))
  fig.update_layout(
    polar=dict(
      bgcolor="rgba(0,0,0,0)",
      radialaxis=dict(
        visible=True,
        range=[0, 100],
        tickfont=dict(color="#475569", size=10, family="JetBrains Mono"),
        gridcolor="rgba(255,255,255,0.06)",
        linecolor="rgba(255,255,255,0.06)",
      ),
      angularaxis=dict(
        tickfont=dict(color="#94a3b8", size=11, family="Space Grotesk"),
        gridcolor="rgba(255,255,255,0.06)",
        linecolor="rgba(255,255,255,0.08)",
      ),
    ),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=20, b=20),
    height=300,
    showlegend=False,
  )
  return fig


# ── Plotly: intensity gauge ──────────────────────────────────────────────────
def intensity_gauge(intensity: float, color: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(intensity * 100, 1),
        number={"suffix": "%", "font": {"color": color, "size": 26, "family": "JetBrains Mono"}},
        gauge={
            "axis": {"range": [0, 100], "tickfont": {"color": "#475569", "size": 9}},
            "bar": {"color": color, "thickness": 0.25},
            "bgcolor": "rgba(255,255,255,0.03)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 35], "color": "rgba(255,255,255,0.04)"},
                {"range": [35, 70], "color": "rgba(255,255,255,0.06)"},
                {"range": [70, 100], "color": "rgba(255,255,255,0.08)"},
            ],
            "threshold": {
                "line": {"color": color, "width": 2},
                "thickness": 0.75,
                "value": round(intensity * 100, 1),
            },
        },
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=160,
        font=dict(family="Space Grotesk"),
    )
    return fig


# ── Plotly: bar chart for vocal parameters ──────────────────────────────────
def param_bar_chart(params, color: str) -> go.Figure:
    labels = ["Rate", "Pitch", "Volume", "Pause"]
    # Normalise each to 0–100 for display
    rate_norm  = ((params.rate_percent - 60) / (180 - 60)) * 100
    pitch_norm = ((params.pitch_st + 8) / 16) * 100
    vol_norm   = ((params.volume_db + 6) / 14) * 100
    pause_norm = ((params.pause_factor - 0.3) / (2.5 - 0.3)) * 100
    values = [rate_norm, pitch_norm, vol_norm, pause_norm]

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=[color] * 4,
        marker_line_width=0,
        opacity=0.8,
        text=[
            f"{params.rate_percent}%",
            f"{'+' if params.pitch_st >= 0 else ''}{params.pitch_st}st",
            f"{'+' if params.volume_db >= 0 else ''}{params.volume_db:.1f}dB",
            f"{params.pause_factor:.2f}×",
        ],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=11, family="JetBrains Mono"),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=30, b=0),
        height=200,
        yaxis=dict(
            range=[0, 115],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=False,
            showticklabels=False,
        ),
        xaxis=dict(
            tickfont=dict(color="#94a3b8", size=12, family="Space Grotesk"),
            showgrid=False,
        ),
        bargap=0.35,
    )
    return fig


# ── Sidebar ─────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div class="sidebar-logo">
          <span class="sidebar-logo-icon">🎙️</span>
          <div class="sidebar-logo-name">Empathy Engine</div>
          <div class="sidebar-logo-version">v1.0.0 · AI Voice Lab</div>
        </div>
        """, unsafe_allow_html=True)

        # Pipeline overview
        st.markdown('<div class="section-header">Pipeline Architecture</div>', unsafe_allow_html=True)
        steps = [
            ("01", "Emotion Detector", "VADER · TextBlob · Keyword fusion"),
            ("02", "Voice Mapper", "Emotion → Prosody parameters"),
            ("03", "SSML Builder", "Rich markup for TTS control"),
            ("04", "TTS Engine", "gTTS + pydub post-processing"),
        ]
        for num, title, desc in steps:
            st.markdown(f"""
            <div class="pipeline-step">
              <div class="step-number">{num}</div>
              <div class="step-content">
                <div class="step-title">{title}</div>
                <div class="step-desc">{desc}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Quick samples
        st.markdown('<div class="section-header">Quick Samples</div>', unsafe_allow_html=True)
        sample_label = st.selectbox(
            "Load demo text",
            options=["— select a sample —"] + get_all_labels(),
            label_visibility="collapsed",
        )
        if sample_label != "— select a sample —":
            chosen = next((s for s in SAMPLES if s.label == sample_label), None)
            if chosen:
                st.session_state["loaded_sample"] = chosen.text

        # Session history
        if st.session_state.get("history"):
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-header">Session History</div>', unsafe_allow_html=True)
            for i, h in enumerate(reversed(st.session_state.history[-5:])):
                meta = EMOTION_META.get(h["emotion"], EMOTION_META["neutral"])
                st.markdown(f"""
                <div class="history-item">
                  <span style="color:{meta['color']}">{meta['icon']}</span>
                  <span style="font-size:0.8rem;color:#94a3b8;margin-left:6px;font-family:var(--font-mono)">
                    {h['emotion'].title()} · {h['intensity']:.0%}
                  </span>
                  <div style="font-size:0.75rem;color:#475569;margin-top:3px;
                              white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                    {h['text'][:45]}{'…' if len(h['text'])>45 else ''}
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
        <div class="info-box">
          💡 <b>How it works:</b><br>
          Enter any text and the engine detects its emotion, maps it to vocal
          parameters (rate, pitch, volume, pacing), and synthesises expressive
          audio — all in one click.
        </div>
        """, unsafe_allow_html=True)


# ── Main UI ─────────────────────────────────────────────────────────────────
def render_main():
    # Hero
    st.markdown("""
    <div class="hero-banner animate-slide-up">
      <div class="hero-badge">🧠 AI · Emotional Intelligence · Voice Synthesis</div>
      <h1 class="hero-title">The Empathy Engine</h1>
      <p class="hero-subtitle">
        Transform text into emotionally expressive speech. Our multi-model pipeline
        detects nuanced emotions and dynamically sculpts the human voice.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Input section ────────────────────────────────────────────────────────
    default_text = st.session_state.pop("loaded_sample", "")
    user_text = st.text_area(
        "Enter your text",
        value=default_text,
        height=150,
        placeholder="Type or paste any sentence, message, or script here…\n\nTry something emotional! e.g. 'We just won the contract!! This is AMAZING!'",
        label_visibility="collapsed",
    )

    col_btn, col_char, col_lang = st.columns([2, 1, 1])
    with col_btn:
        run_btn = st.button("🎙  Generate Empathic Speech", use_container_width=True)
    with col_char:
        char_count = len(user_text)
        st.markdown(f"""
        <div style="text-align:center;padding:0.6rem;border-radius:8px;
                    background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06)">
          <div style="font-family:'JetBrains Mono',monospace;font-size:1.3rem;
                      color:{'#ef4444' if char_count>800 else '#94a3b8'}">{char_count}</div>
          <div style="font-size:0.65rem;color:#475569;text-transform:uppercase;
                      letter-spacing:0.1em">characters</div>
        </div>
        """, unsafe_allow_html=True)
    with col_lang:
        st.markdown("""
        <div style="text-align:center;padding:0.6rem;border-radius:8px;
                    background:rgba(99,102,241,0.06);border:1px solid rgba(99,102,241,0.15)">
          <div style="font-family:'JetBrains Mono',monospace;font-size:1.3rem;color:#818cf8">EN</div>
          <div style="font-size:0.65rem;color:#475569;text-transform:uppercase;
                      letter-spacing:0.1em">language</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Run pipeline ─────────────────────────────────────────────────────────
    if run_btn:
        if not user_text.strip():
            st.warning("Please enter some text first.")
            return

        with st.spinner("Analysing emotion and synthesising voice…"):
            start_t = time.time()
            try:
                result: PipelineResult = st.session_state.pipeline.process(user_text)
                elapsed = time.time() - start_t
                st.session_state.last_result = result
                # Save to history
                st.session_state.history.append({
                    "text": user_text,
                    "emotion": result.emotion_result.primary_emotion,
                    "intensity": result.emotion_result.intensity,
                    "file": result.audio_result.file_path,
                })
                st.session_state["elapsed"] = elapsed
            except Exception as e:
                st.error(f"Pipeline error: {e}")
                return

    # ── Display results ──────────────────────────────────────────────────────
    result: PipelineResult | None = st.session_state.last_result
    if result is None:
        # Onboarding state
        _render_onboarding()
        return

    er = result.emotion_result
    vp = result.voice_params
    ar = result.audio_result
    meta = EMOTION_META.get(er.primary_emotion, EMOTION_META["neutral"])
    color = meta["color"]
    elapsed = st.session_state.get("elapsed", 0)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Emotion headline ──────────────────────────────────────────────────────
    intensity_pct = int(er.intensity * 100)
    intensity_label = (
        "Mild" if intensity_pct < 35 else
        "Moderate" if intensity_pct < 65 else
        "Strong" if intensity_pct < 85 else "Intense"
    )
    st.markdown(f"""
    <div class="animate-slide-up" style="margin-bottom:2rem">
      <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
        <span style="font-size:3.5rem;line-height:1">{meta['icon']}</span>
        <div>
          <div style="font-size:0.7rem;font-family:'JetBrains Mono',monospace;
                      color:#475569;letter-spacing:0.12em;text-transform:uppercase;
                      margin-bottom:4px">Detected Emotion</div>
          <div style="font-size:2.2rem;font-weight:700;color:{color};
                      font-family:'Space Grotesk',sans-serif;line-height:1">
            {meta['label']}
          </div>
        </div>
        <div style="margin-left:auto">
          <div style="display:flex;gap:10px;align-items:center">
            <div style="text-align:right">
              <div style="font-size:0.7rem;color:#475569;text-transform:uppercase;
                          letter-spacing:0.1em;font-family:'JetBrains Mono',monospace">
                Intensity
              </div>
              <div style="font-size:1.8rem;font-weight:700;color:{color};
                          font-family:'JetBrains Mono',monospace;line-height:1">
                {intensity_pct}%
              </div>
              <div style="font-size:0.75rem;color:#94a3b8">{intensity_label}</div>
            </div>
            <div style="width:5px;height:60px;border-radius:3px;background:rgba(255,255,255,0.05);
                        overflow:hidden;position:relative">
              <div style="position:absolute;bottom:0;left:0;right:0;
                          height:{intensity_pct}%;background:{color};
                          border-radius:3px;transition:height 0.5s ease"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Three-column layout ───────────────────────────────────────────────────
    col_a, col_b, col_c = st.columns([1.2, 1, 1], gap="medium")

    with col_a:
        # Audio player
        st.markdown('<div class="section-header">🎵  Generated Audio</div>', unsafe_allow_html=True)
        if Path(ar.file_path).exists():
            audio_b64 = audio_to_base64(ar.file_path)
            st.markdown(f"""
            <div class="glass-card" style="border-color:rgba({_hex_to_rgb(color)},0.2);
                         background:rgba({_hex_to_rgb(color)},0.04)">
              <audio controls style="width:100%;margin-bottom:1rem">
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
              </audio>
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;
                          margin-top:0.5rem">
                <div class="metric-box">
                  <div class="metric-value" style="color:{color};font-size:1.3rem">
                    {ar.duration_seconds:.1f}s
                  </div>
                  <div class="metric-label">Duration</div>
                </div>
                <div class="metric-box">
                  <div class="metric-value" style="color:{color};font-size:1.3rem">
                    {ar.file_size_bytes // 1024}KB
                  </div>
                  <div class="metric-label">File Size</div>
                </div>
                <div class="metric-box">
                  <div class="metric-value" style="color:{color};font-size:1.3rem">
                    {elapsed:.1f}s
                  </div>
                  <div class="metric-label">Gen Time</div>
                </div>
              </div>
              <div style="margin-top:1rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,0.06)">
                <span style="font-size:0.7rem;font-family:'JetBrains Mono',monospace;
                             color:#475569">ENGINE:</span>
                <span style="font-size:0.75rem;color:#94a3b8;margin-left:6px">
                  {ar.engine_used.upper()}
                </span>
                <span style="font-size:0.7rem;font-family:'JetBrains Mono',monospace;
                             color:#475569;margin-left:12px">EMPHASIS:</span>
                <span style="font-size:0.75rem;color:#94a3b8;margin-left:6px">
                  {vp.emphasis.upper()}
                </span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Download button
            with open(ar.file_path, "rb") as f:
                st.download_button(
                    "⬇  Download Audio",
                    data=f.read(),
                    file_name=Path(ar.file_path).name,
                    mime="audio/mp3",
                    use_container_width=True,
                )

    with col_b:
        st.markdown('<div class="section-header">📊  Emotion Analysis</div>', unsafe_allow_html=True)
        # Radar chart
        fig_radar = emotion_radar(er.emotion_scores, color)
        st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

        # Top-3 emotions bar
        top3 = sorted(er.emotion_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        for emo, score in top3:
            m = EMOTION_META.get(emo, EMOTION_META["neutral"])
            bar_w = int(score * 100)
            st.markdown(f"""
            <div style="margin-bottom:8px">
              <div style="display:flex;justify-content:space-between;margin-bottom:3px">
                <span style="font-size:0.78rem;color:#94a3b8">{m['icon']} {emo.title()}</span>
                <span style="font-size:0.72rem;font-family:'JetBrains Mono',monospace;
                             color:{m['color']}">{bar_w}%</span>
              </div>
              <div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden">
                <div style="height:100%;width:{bar_w}%;background:{m['color']};
                            border-radius:2px;transition:width 0.6s ease"></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

        # Valence + Subjectivity
        st.markdown("<br>", unsafe_allow_html=True)
        v_col, s_col = st.columns(2)
        valence_pct = int((er.valence + 1) / 2 * 100)
        subj_pct = int(er.subjectivity * 100)
        with v_col:
            st.markdown(f"""
            <div class="metric-box">
              <div class="metric-value" style="color:{'#10b981' if er.valence>0 else '#ef4444'};
                                               font-size:1.4rem">
                {'+' if er.valence > 0 else ''}{er.valence:.2f}
              </div>
              <div class="metric-label">Valence</div>
            </div>
            """, unsafe_allow_html=True)
        with s_col:
            st.markdown(f"""
            <div class="metric-box">
              <div class="metric-value" style="color:#818cf8;font-size:1.4rem">
                {subj_pct}%
              </div>
              <div class="metric-label">Subjectivity</div>
            </div>
            """, unsafe_allow_html=True)

    with col_c:
        st.markdown('<div class="section-header">🎚  Voice Parameters</div>', unsafe_allow_html=True)

        # Intensity gauge
        fig_gauge = intensity_gauge(er.intensity, color)
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

        # Parameter chart
        fig_bar = param_bar_chart(vp, color)
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

        # Raw values
        params_data = [
            ("Rate",        f"{vp.rate_percent}%",     "Speaking speed"),
            ("Pitch",       f"{'+' if vp.pitch_st>=0 else ''}{vp.pitch_st} st", "Tonal height"),
            ("Volume",      f"{'+' if vp.volume_db>=0 else ''}{vp.volume_db:.1f} dB", "Amplitude"),
            ("Pauses",      f"{vp.pause_factor:.2f}×", "Sentence spacing"),
            ("Emphasis",    vp.emphasis.title(),       "Word stress level"),
            ("Break",       f"{vp.sentence_break_ms} ms", "Inter-sentence gap"),
        ]
        for label, value, desc in params_data:
            st.markdown(f"""
            <div class="param-row">
              <div>
                <div class="param-label">{label}</div>
                <div style="font-size:0.68rem;color:#334155;margin-top:1px">{desc}</div>
              </div>
              <div class="param-value" style="color:{color}">{value}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Tabs: SSML / Explanation / Raw ────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["📄  SSML Output", "🔍  Analysis Details", "🛠  Raw Debug"])

    with tab1:
        st.markdown("""
        <div class="info-box" style="margin-bottom:1rem">
          The SSML below is generated alongside each audio file. It can be fed directly
          into any SSML-capable engine (Google Cloud TTS, Amazon Polly, ElevenLabs)
          for even richer expressive synthesis.
        </div>
        """, unsafe_allow_html=True)
        ssml_display = result.ssml.replace("<", "&lt;").replace(">", "&gt;")
        st.markdown(f'<div class="ssml-block">{ssml_display}</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown(f"""
        <div class="glass-card">
          <div class="section-header">Detector Explanation</div>
          <p style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;
                    color:#94a3b8;line-height:1.8">
            {er.explanation}
          </p>
          <div class="section-header" style="margin-top:1.5rem">Voice Parameter Logic</div>
          <pre style="font-family:'JetBrains Mono',monospace;font-size:0.78rem;
                      color:#7dd3fc;background:#080810;padding:1rem;
                      border-radius:8px;overflow-x:auto">{result.parameter_description}</pre>
        </div>
        """, unsafe_allow_html=True)

    with tab3:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.markdown('<div class="section-header">Emotion Scores (raw)</div>', unsafe_allow_html=True)
            st.json({k: round(v, 4) for k, v in er.emotion_scores.items()})
        with col_d2:
            st.markdown('<div class="section-header">VADER Scores</div>', unsafe_allow_html=True)
            st.json(er.raw_vader)


# ── Onboarding ───────────────────────────────────────────────────────────────
def _render_onboarding():
    st.markdown("""
    <div style="text-align:center;padding:4rem 2rem" class="animate-slide-up">
      <div style="font-size:4rem;margin-bottom:1rem">🎙️</div>
      <h2 style="color:#94a3b8;font-size:1.4rem;font-weight:400;margin-bottom:0.5rem">
        Ready to synthesise
      </h2>
      <p style="color:#475569;font-size:0.9rem;max-width:400px;margin:0 auto 2rem">
        Type any text above and click <b style="color:#818cf8">Generate</b>,
        or load a sample from the sidebar.
      </p>
    </div>

    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
                gap:1rem;margin-top:2rem">
    """, unsafe_allow_html=True)

    examples = [
        ("🎉", "Excitement", "#EF4444", "Detected on highly energetic, ALL-CAPS, multi-exclamation text"),
        ("😢", "Sadness", "#6366F1", "Slower, lower, softer voice for empathetic support contexts"),
        ("😠", "Anger", "#DC2626", "Fast, forceful, high-volume for escalated complaint handling"),
        ("🤔", "Curiosity", "#14B8A6", "Measured, rising-inflection tone for inquisitive messages"),
    ]
    cols = st.columns(len(examples))
    for col, (icon, label, color, desc) in zip(cols, examples):
        with col:
            st.markdown(f"""
            <div class="glass-card" style="text-align:center;
                 border-color:rgba({_hex_to_rgb(color)},0.15)">
              <div style="font-size:2rem;margin-bottom:0.5rem">{icon}</div>
              <div style="font-size:0.95rem;font-weight:600;color:{color};margin-bottom:0.4rem">
                {label}
              </div>
              <div style="font-size:0.75rem;color:#475569;line-height:1.5">{desc}</div>
            </div>
            """, unsafe_allow_html=True)


# ── Utility ──────────────────────────────────────────────────────────────────
def _hex_to_rgb(hex_color: str) -> str:
    """Convert #RRGGBB to 'R,G,B' string."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r},{g},{b}"
    return "99,102,241"


# ── Entry point ──────────────────────────────────────────────────────────────
def main():
    inject_css()
    init_session()
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()
