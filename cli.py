"""
cli.py
------
Command-line interface for the Empathy Engine.

Usage:
  python cli.py "Your text here"
  python cli.py --sample joy
  python cli.py --batch samples.txt
  python cli.py --interactive
"""

import sys
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Make local modules importable
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
load_dotenv(BASE_DIR / ".env")

from core.pipeline import EmpathyPipeline
from utils.samples import SAMPLES


BANNER = r"""
  ███████╗███╗   ███╗██████╗  █████╗ ████████╗██╗  ██╗██╗   ██╗
  ██╔════╝████╗ ████║██╔══██╗██╔══██╗╚══██╔══╝██║  ██║╚██╗ ██╔╝
  █████╗  ██╔████╔██║██████╔╝███████║   ██║   ███████║ ╚████╔╝
  ██╔══╝  ██║╚██╔╝██║██╔═══╝ ██╔══██║   ██║   ██╔══██║  ╚██╔╝
  ███████╗██║ ╚═╝ ██║██║     ██║  ██║   ██║   ██║  ██║   ██║
  ╚══════╝╚═╝     ╚═╝╚═╝     ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝   ╚═╝

  ███████╗███╗   ██╗ ██████╗ ██╗███╗   ██╗███████╗
  ██╔════╝████╗  ██║██╔════╝ ██║████╗  ██║██╔════╝
  █████╗  ██╔██╗ ██║██║  ███╗██║██╔██╗ ██║█████╗
  ██╔══╝  ██║╚██╗██║██║   ██║██║██║╚██╗██║██╔══╝
  ███████╗██║ ╚████║╚██████╔╝██║██║ ╚████║███████╗
  ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝╚═╝  ╚═══╝╚══════╝

  AI Voice · Emotional Intelligence · v1.0
"""

EMOTION_ICONS = {
    "joy": "😊", "excitement": "🎉", "gratitude": "🙏",
    "sadness": "😢", "frustration": "😤", "anger": "😠",
    "fear": "😨", "surprise": "😲", "curiosity": "🤔", "neutral": "😐",
}


def print_result(result, verbose: bool = False):
    er = result.emotion_result
    vp = result.voice_params
    ar = result.audio_result

    icon = EMOTION_ICONS.get(er.primary_emotion, "🎙")
    intensity_label = (
        "mild" if er.intensity < 0.35 else
        "moderate" if er.intensity < 0.65 else
        "strong" if er.intensity < 0.85 else "very intense"
    )

    print("\n" + "─" * 60)
    print(f"  {icon}  DETECTED EMOTION:  {er.primary_emotion.upper()}")
    print(f"  📊  INTENSITY:        {er.intensity:.2f}  ({intensity_label})")
    print(f"  💬  VALENCE:          {er.valence:+.2f}")
    print("─" * 60)
    print(result.parameter_description)
    print("─" * 60)
    print(f"  🎵  AUDIO OUTPUT:  {ar.file_path}")
    print(f"  ⏱  DURATION:      {ar.duration_seconds:.1f}s")
    print(f"  🔧  ENGINE:        {ar.engine_used}")
    print("─" * 60)

    if verbose:
        print("\n📊 All emotion scores:")
        for emo, score in sorted(er.emotion_scores.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * int(score * 30)
            print(f"   {EMOTION_ICONS.get(emo, ' ')} {emo:<14} {bar:<30} {score:.2%}")

        print("\n📄 SSML Preview (first 400 chars):")
        print("   " + result.ssml[:400].replace("\n", "\n   ") + "…")


def run_single(text: str, pipeline: EmpathyPipeline, verbose: bool):
    print(f"\n📝 Processing: {text[:80]}{'…' if len(text) > 80 else ''}")
    result = pipeline.process(text)
    print_result(result, verbose)
    return result


def run_interactive(pipeline: EmpathyPipeline):
    print(BANNER)
    print("Interactive mode. Type 'quit' to exit, 'samples' to list demos.\n")
    while True:
        try:
            text = input("🎙  Enter text > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break
        if not text:
            continue
        if text.lower() == "quit":
            break
        if text.lower() == "samples":
            print("\nAvailable samples:")
            for s in SAMPLES:
                print(f"  {s.label}")
            print()
            continue
        run_single(text, pipeline, verbose=True)


def main():
    default_output_dir = os.getenv("EMPATHY_OUTPUT_DIR", "audio_output")
    default_lang = os.getenv("EMPATHY_LANG", "en")

    parser = argparse.ArgumentParser(
        description="Empathy Engine CLI — Emotionally expressive TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("text", nargs="?", help="Text to synthesise")
    parser.add_argument("--sample", choices=[s.expected_emotion for s in SAMPLES],
                        help="Use a built-in demo text for the given emotion")
    parser.add_argument("--batch", metavar="FILE",
                        help="Process each line of a text file")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Enter interactive REPL mode")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed output including all emotion scores")
    parser.add_argument("--output-dir", default=default_output_dir,
                        help="Directory for generated audio files (default: EMPATHY_OUTPUT_DIR or audio_output)")
    parser.add_argument("--lang", default=default_lang,
                        help="TTS language code (default: EMPATHY_LANG or en)")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON (useful for piping)")

    args = parser.parse_args()

    if not any([args.text, args.sample, args.batch, args.interactive]):
        parser.print_help()
        return

    output_dir_path = Path(args.output_dir)
    if not output_dir_path.is_absolute():
        output_dir_path = BASE_DIR / output_dir_path

    pipeline = EmpathyPipeline(output_dir=str(output_dir_path), lang=args.lang)

    if args.interactive:
        run_interactive(pipeline)
        return

    texts = []
    if args.text:
        texts.append(args.text)
    if args.sample:
        sample = next((s for s in SAMPLES if s.expected_emotion == args.sample), None)
        if sample:
            texts.append(sample.text)
    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.exists():
            print(f"Error: file not found: {args.batch}")
            sys.exit(1)
        texts.extend(batch_path.read_text().strip().splitlines())

    if not args.json:
        print(BANNER)

    results = []
    for text in texts:
        if text.strip():
            result = pipeline.process(text.strip())
            results.append(result)
            if not args.json:
                print_result(result, args.verbose)

    if args.json:
        output = []
        for r in results:
            output.append({
                "text": r.text,
                "emotion": r.emotion_result.primary_emotion,
                "intensity": r.emotion_result.intensity,
                "valence": r.emotion_result.valence,
                "emotion_scores": r.emotion_result.emotion_scores,
                "voice_params": {
                    "rate_percent": r.voice_params.rate_percent,
                    "pitch_st": r.voice_params.pitch_st,
                    "volume_db": r.voice_params.volume_db,
                    "pause_factor": r.voice_params.pause_factor,
                    "emphasis": r.voice_params.emphasis,
                },
                "audio_file": r.audio_result.file_path,
                "duration_seconds": r.audio_result.duration_seconds,
            })
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
