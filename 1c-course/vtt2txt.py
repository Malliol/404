#!/usr/bin/env python3
"""Convert YouTube auto-caption VTT to clean paragraph text (drops rolling duplicates)."""
import re, sys

def convert(path):
    # Auto-captions are "rolling": every cue repeats the previous line and adds a new one
    # whose words carry <00:00:01.000><c> timing tags. Keep only the tagged (new) lines.
    out = []
    for raw in open(path, encoding="utf-8"):
        if "<c>" not in raw and not re.search(r"<\d\d:\d\d:\d\d\.\d+>", raw):
            continue
        s = re.sub(r"<[^>]+>", "", raw)
        s = re.sub(r"\s+", " ", s).strip()
        if s:
            out.append(s)
    text = re.sub(r"\s+", " ", " ".join(out))
    sents = re.split(r"(?<=[.!?])\s+", text)
    # captions have no punctuation: chunk by ~90 words instead
    words = text.split()
    return "\n\n".join(" ".join(words[i:i + 90]) for i in range(0, len(words), 90))

if __name__ == "__main__":
    print(convert(sys.argv[1]))
