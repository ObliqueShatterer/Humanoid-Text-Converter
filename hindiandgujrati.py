#!/usr/bin/env python3
"""
translit_both.py

Simple CLI to transliterate romanized Hindi or Gujarati to native script
(using ai4bharat.transliteration).

Usage:
    python translit_both.py              # interactive: choose language
    python translit_both.py --lang hi    # start with Hindi
    python translit_both.py --lang gu    # start with Gujarati
    python translit_both.py --file in.txt --lang hi   # transliterate file lines
"""

import argparse
import sys
from pathlib import Path

try:
    from ai4bharat.transliteration import XlitEngine
except Exception as e:
    print("Error: Unable to import ai4bharat.transliteration.", file=sys.stderr)
    print("Make sure you installed ai4bharat-transliteration in the active venv.", file=sys.stderr)
    print("Install with: python -m pip install ai4bharat-transliteration", file=sys.stderr)
    raise

SUPPORTED = {
    "hi": "Hindi (Devanagari)",
    "gu": "Gujarati (ગુજરાતી)",
    "guj": "Gujarati (alias for 'gu')",
}

def make_engine(lang):
    # try canonical code; allow guj alias
    code = "gu" if lang == "guj" else lang
    return XlitEngine(code, beam_width=6, rescore=True)

def translit_line(engine, text):
    # engine.translit_sentence typically returns dict if multiple langs supported;
    # but for single-lang engine it returns the string (or dict with key 'hi'/'gu').
    out = engine.translit_sentence(text)
    if isinstance(out, dict):
        # pick the first value
        val = next(iter(out.values()))
        return val
    return out

def interactive_run(default_lang=None):
    # create engines lazily (models are heavy, so only create used engine)
    engines = {}
    lang = default_lang

    while True:
        if not lang:
            print("Pick a language (type the code):")
            for k, desc in SUPPORTED.items():
                print(f"  {k}  -> {desc}")
            lang = input("lang> ").strip().lower()
            if not lang:
                print("No language selected. Exiting.")
                return
            if lang not in SUPPORTED:
                print(f"Unsupported language: {lang}. Try again.")
                lang = None
                continue

        if lang not in engines:
            print(f"Loading model for {SUPPORTED[lang]}... (this may take a few seconds)")
            try:
                engines[lang] = make_engine(lang)
            except Exception as e:
                print(f"Failed to load engine for {lang}: {e}", file=sys.stderr)
                return

        eng = engines[lang]
        print(f"Enter romanized text to transliterate to {SUPPORTED[lang]}. Empty line to quit.")
        try:
            while True:
                s = input("> ").strip()
                if s == "":
                    print("Returning to language selection (or exit).")
                    break
                try:
                    out = translit_line(eng, s)
                    print(out)
                except Exception as e:
                    print("Transliteration error:", e, file=sys.stderr)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            return

        # reset lang to ask for next action
        lang = None

def file_run(lang, infile, outfile=None):
    if lang not in SUPPORTED:
        raise SystemExit(f"Unsupported language code: {lang}")

    print(f"Preparing engine for {SUPPORTED[lang]}...")
    eng = make_engine(lang)

    infile = Path(infile)
    if not infile.exists():
        raise SystemExit(f"Input file not found: {infile}")

    out_lines = []
    with infile.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                out_lines.append("")
                continue
            try:
                out = translit_line(eng, line)
                out_lines.append(out)
            except Exception as e:
                out_lines.append(f"[ERROR: {e}]")

    if outfile:
        Path(outfile).write_text("\n".join(out_lines), encoding="utf-8")
        print(f"Wrote transliteration to {outfile}")
    else:
        print("\n--- Transliterated output ---")
        for ln in out_lines:
            print(ln)

def main():
    parser = argparse.ArgumentParser(description="Transliterate romanized Hindi/Gujarati to native script.")
    parser.add_argument("--lang", "-l", choices=list(SUPPORTED.keys()), help="language code (hi, gu, guj)")
    parser.add_argument("--file", "-f", help="input file (one sentence per line)")
    parser.add_argument("--out", "-o", help="output file (for --file mode)")
    args = parser.parse_args()

    if args.file:
        if not args.lang:
            raise SystemExit("When using --file you must pass --lang (hi or gu).")
        file_run(args.lang, args.file, args.out)
    else:
        interactive_run(args.lang)

if __name__ == "__main__":
    main()
