#!/usr/bin/env python3
"""Keep script.tex's slide headers tied to main.tex's frame titles.

WHY. The speaker script names each slide by number and title. Both are typed by
hand, and both drift: insert one frame and every number after it is wrong, and a
title paraphrased "to read better in the script" is a title the presenter cannot
match to the screen. Slide 9 was headed "Metrology --- the spine of the talk" in
the script and "Metrology --- the constraint everything else is built around" on
the slide, which is exactly the kind of small mismatch that makes a script feel
untrustworthy in the room.

So the titles are not the script's to invent. This walks main.tex in document
order, works out what lands on which slide, and compares.

    python3 presentation/check_script.py          # report drift, exit 1 if any
    python3 presentation/check_script.py --fix    # rewrite script.tex's headers

WHAT COUNTS AS A SLIDE, and why it is parsed rather than read out of the PDF:
\\maketitle is one; each \\section{} is one, because the metropolis theme draws a
section page; each \\begin{frame} is one. The PDF would be authoritative but its
text layer gives you the title with unicode dashes and quotes already applied,
which then has to be turned back into LaTeX to be written into script.tex. The
source has it in the form we need.

A frame in the appendix still counts -- the backup slides are numbered in the
script the same way the presenter finds them with the arrow keys.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.tex"
SCRIPT = HERE / "script.tex"

# \begin{frame}, optionally [opts], optionally {Title}. A frame with no braced
# argument -- [plain], [standout] -- is a slide with no title of its own.
FRAME = re.compile(r"\\begin\{frame\}(\[[^\]]*\])?\s*(\{)?")
SECTION = re.compile(r"^\\section\{(.*)\}\s*$", re.M)


def balanced(text: str, start: int) -> tuple[str, int]:
    """Read a braced group starting at `start` (which is the opening brace)."""
    depth, i = 0, start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    raise ValueError("unbalanced brace in main.tex")


def deck_slides() -> list[str]:
    """Every slide, in order, as its title. '' for a slide with no frame title."""
    src = MAIN.read_text()
    body = src[src.index(r"\begin{document}"):]

    events: list[tuple[int, str, str]] = []
    for m in re.finditer(r"\\maketitle\b", body):
        events.append((m.start(), "title", ""))
    for m in SECTION.finditer(body):
        events.append((m.start(), "section", m.group(1)))
    for m in FRAME.finditer(body):
        if m.group(2):                      # a braced title follows
            title, _ = balanced(body, m.end() - 1)
        else:
            title = ""
        events.append((m.start(), "frame", title))

    events.sort(key=lambda e: e[0])
    return [t.strip() for _, _, t in events]


def tex_to_plain(t: str) -> str:
    """Just enough de-TeXing to compare two titles for equality."""
    t = re.sub(r"\\(?:textbf|emph|texttt|up|down|wn|rr|LA)\s*\{([^}]*)\}", r"\1", t)
    t = t.replace(r"\dB", " dB").replace("$", "").replace("\\,", " ")
    t = re.sub(r"\\[a-zA-Z]+", "", t)
    t = t.replace("{", "").replace("}", "")
    return " ".join(t.split())


def script_headers() -> list[tuple[int, str, int, int]]:
    """(number, title, span start, span end) for each \\slide{n}{title}{time}."""
    src = SCRIPT.read_text()
    out = []
    for m in re.finditer(r"\\slide\{(\d+)\}\{", src):
        title, end = balanced(src, m.end() - 1)
        out.append((int(m.group(1)), title, m.start(), end))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true",
                    help="rewrite script.tex's titles to the deck's")
    args = ap.parse_args()

    slides = deck_slides()
    print(f"main.tex: {len(slides)} slides")

    headers = script_headers()
    drift, missing = [], []
    for n, title, a, b in headers:
        if not 1 <= n <= len(slides):
            missing.append((n, title))
            continue
        want = slides[n - 1]
        if not want:                        # title page, standout, plain
            continue
        if tex_to_plain(want) != tex_to_plain(title):
            drift.append((n, title, want, a, b))

    for n, title in missing:
        print(f"  !! slide {n} does not exist: {title!r}")
    for n, title, want, _, _ in drift:
        print(f"  {n:>2}  script: {tex_to_plain(title)}")
        print(f"      deck:   {tex_to_plain(want)}")

    if args.fix and drift:
        src = SCRIPT.read_text()
        for n, _, want, a, b in sorted(drift, key=lambda d: -d[3]):
            head = src[a:b]
            src = src[:a] + head.replace(head[head.index("}{") + 2:], want + "}", 1) + src[b:]
        SCRIPT.write_text(src)
        print(f"\nrewrote {len(drift)} title(s) in script.tex")
        return 0

    if drift or missing:
        print(f"\n{len(drift)} drifted, {len(missing)} missing. "
              f"Run with --fix to take the deck's titles.")
        return 1
    print("script.tex titles match main.tex.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
