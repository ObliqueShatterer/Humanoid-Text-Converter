#!/usr/bin/env python3
# translit_cli.py
from ai4bharat.transliteration import XlitEngine

def main():
    # load Hindi model; beam_width/rescore can be tweaked
    engine = XlitEngine("hi", beam_width=6, rescore=True)

    print("Enter romanized Hindi (type blank line or Ctrl+D to quit):")
    try:
        while True:
            s = input("> ").strip()
            if not s:
                break
            # translit_sentence returns a dict like {'hi': 'देवनागरी output'}
            out = engine.translit_sentence(s)
            # for single language case, extract the hi result:
            result = out.get("hi") if isinstance(out, dict) else out
            print(result)
    except (EOFError, KeyboardInterrupt):
        print("\nBye.")
        
if __name__ == "__main__":
    main()
