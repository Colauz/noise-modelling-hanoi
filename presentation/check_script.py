#!/usr/bin/env python3
"""Keep the speaker scripts' slide headers tied to main.tex's frame titles.

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
    python3 presentation/check_script.py --fix    # rewrite the headers

It covers every file in SCRIPTS -- the full script and the 30-seconds-a-slide
one -- because two scripts drift twice as fast as one.

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
# Which script is held against which deck. main.tex builds two: the full one,
# and the fifteen-minute one that drops every frame wrapped in \onlyfull.
SCRIPTS = {
    HERE / "script.tex":       False,   # full deck
    HERE / "script-short.tex": False,   # full deck, said faster
    HERE / "script-15.tex":    True,    # the short deck
}

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


def onlyfull_spans(body: str) -> list[tuple[int, int]]:
    r"""Character ranges of every \onlyfull{...}: the frames the short deck drops."""
    spans = []
    for m in re.finditer(r"\\onlyfull\{", body):
        spans.append((m.start(), balanced(body, m.end() - 1)[1]))
    return spans


def deck_slides(short: bool = False) -> list[str]:
    r"""Every slide, in order, as its title. '' for a slide with no frame title.

    With short=True this is the deck main-short.tex builds: the frames inside
    \onlyfull are not emitted, so they do not take a slide number either. That
    is the whole reason the numbering has to be derived rather than typed.
    """
    src = MAIN.read_text()
    body = src[src.index(r"\begin{document}"):]
    dropped = onlyfull_spans(body) if short else []

    def cut(pos: int) -> bool:
        return any(a <= pos < b for a, b in dropped)

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
    return [t.strip() for pos, _, t in events if not cut(pos)]


def tex_to_plain(t: str) -> str:
    """Just enough de-TeXing to compare two titles for equality."""
    t = re.sub(r"\\(?:textbf|emph|texttt|up|down|wn|rr|LA)\s*\{([^}]*)\}", r"\1", t)
    t = t.replace(r"\dB", " dB").replace("$", "").replace("\\,", " ")
    t = re.sub(r"\\[a-zA-Z]+", "", t)
    t = t.replace("{", "").replace("}", "")
    return " ".join(t.split())


def script_headers(path: Path) -> list[tuple[int, str, int, int]]:
    """(number, title, span start, span end) for each \\slide{n}{title}{time}."""
    src = path.read_text()
    out = []
    # \slide{n}{title}{time} or \slide[fraction]{n}{title}{time}. The optional
    # argument was added later and this pattern silently stopped matching, so
    # the checker reported "2 headers, all match" and checked nothing. A checker
    # that can pass by finding nothing is worse than no checker.
    for m in re.finditer(r"\\slide(?:\[[^\]]*\])?\{(\d+)\}\{", src):
        title, end = balanced(src, m.end() - 1)
        out.append((int(m.group(1)), title, m.start(), end))
    return out


def check(path: Path, slides: list[str], fix: bool) -> int:
    """Compare one script's headers with the deck. Returns the number of problems."""
    headers = script_headers(path)
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

    if len(headers) < 5:
        print(f"  {path.name}: only {len(headers)} headers found -- the pattern "
              f"is probably out of step with the file. Refusing to call that a pass.")
        return 1

    if not drift and not missing:
        print(f"  {path.name}: {len(headers)} headers, all match")
        return 0

    print(f"  {path.name}:")
    for n, title in missing:
        print(f"    !! slide {n} does not exist: {title!r}")
    for n, title, want, _, _ in drift:
        print(f"    {n:>2}  script: {tex_to_plain(title)}")
        print(f"        deck:   {tex_to_plain(want)}")

    if fix and drift:
        src = path.read_text()
        # right to left, so earlier spans keep their offsets
        for n, _, want, a, b in sorted(drift, key=lambda d: -d[3]):
            head = src[a:b]
            src = src[:a] + head.replace(head[head.index("}{") + 2:], want + "}", 1) + src[b:]
        path.write_text(src)
        print(f"    rewrote {len(drift)} title(s)")
        return 0

    return len(drift) + len(missing)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true",
                    help="rewrite the scripts' titles to the deck's")
    args = ap.parse_args()

    full, short = deck_slides(False), deck_slides(True)
    print(f"main.tex: {len(full)} slides full, {len(short)} short")

    problems = 0
    for path, is_short in SCRIPTS.items():
        if not path.exists():
            print(f"  {path.name}: absent, skipped")
            continue
        problems += check(path, short if is_short else full, args.fix)

    if problems:
        print(f"\n{problems} problem(s). Run with --fix to take the deck's titles.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
