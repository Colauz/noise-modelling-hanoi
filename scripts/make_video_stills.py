#!/usr/bin/env python3
"""Redacted stills from the traffic videos, for the report.

WHY REDACTION IS NOT OPTIONAL. data/raw/videos/ is 6 GB of street footage
carrying identifiable faces and readable licence plates. It is not distributed
and it is not in the repository (docs/data-sources.md). A still lifted from it
and committed would publish, in one image, exactly what the whole of that
policy exists to keep unpublished -- and this repository is public. So no raw
frame is ever written to disk here.

WHAT THE REDACTION DOES, and what it does not promise. Each frame is passed
through the same detector the counting pipeline uses (yolov8n). Every `person`
box is dilated and mosaicked. Every vehicle box is mosaicked over its lower
portion, where plates sit, and blurred over the whole box, because a plate that
the detector framed loosely would otherwise survive at the edge. The mosaic
block size is a fraction of the box, so a small distant person is destroyed as
thoroughly as a large near one.

This is a machine pass and it is not a guarantee. A person the detector misses
is a person the mosaic misses. Every still this script writes must be looked at
by a human before it goes anywhere, and that is the point of writing them to a
review directory rather than straight into the figures the report includes.

    python scripts/make_video_stills.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / "data" / "raw" / "videos"
OUT = ROOT / "deliverables" / "figures" / "stills"

PERSON = {"person"}
VEHICLE = {"car", "motorcycle", "bus", "truck", "bicycle"}

# Deliberately low, and run at full resolution rather than the 640 px default.
# A false positive costs a mosaicked patch of road; a false negative costs
# someone's face in a published report. The default 640 px pass missed two
# pedestrians on a pavement 40 m from the camera -- small enough not to be
# identifiable, large enough to prove the point that this pass is not a
# guarantee.
CONF = 0.06
IMGSZ = 1280

# Drawn over the redaction, because the redaction destroys what makes the frame
# worth showing. The boxes are the information: what the detector found, where,
# and how much of it.
BOX_VEHICLE = (139, 92, 31)     # BGR -- the report's accent blue
BOX_PERSON = (110, 110, 110)

# The capture app ("TimeStamp Camera") burns a date and a reverse-geocoded
# place name into the top right corner. The date is right. The place name is
# NOT: it is cached from the last geocode the app made, so the 13 July
# recordings in Vinh Tuy all carry "Ocean Park Gia Lam", 8 km away, and the
# 14 July recordings in Hoan Kiem carry no place line at all. Only the GPS tag
# in the file metadata can be trusted to site a video. The overlay is masked
# out rather than published, because a caption that contradicts a legible
# label in its own figure is worse than no label. It is blurred rather than
# filled: a flat block reads as damage, a blurred patch of sky reads as sky.
OVERLAY = (0.55, 0.0, 1.0, 0.28)   # left, top, right, bottom, as fractions


def mosaic(image: np.ndarray, box: tuple[int, int, int, int], blocks: int = 6) -> None:
    """Replace a region with a coarse mosaic, in place."""
    x0, y0, x1, y1 = box
    h, w = image.shape[:2]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(w, x1), min(h, y1)
    if x1 - x0 < 2 or y1 - y0 < 2:
        return
    patch = image[y0:y1, x0:x1]
    small = cv2.resize(patch, (max(1, blocks), max(1, blocks)),
                       interpolation=cv2.INTER_AREA)
    image[y0:y1, x0:x1] = cv2.resize(small, (x1 - x0, y1 - y0),
                                     interpolation=cv2.INTER_NEAREST)


def redact(frame: np.ndarray, model: YOLO,
           draw_boxes: bool = True) -> tuple[np.ndarray, dict[str, int]]:
    result = model(frame, conf=CONF, imgsz=IMGSZ, verbose=False)[0]
    names = result.names
    out = frame.copy()
    counts: dict[str, int] = {}
    boxes = []

    for box in result.boxes:
        label = names[int(box.cls)]
        x0, y0, x1, y1 = (int(v) for v in box.xyxy[0])
        counts[label] = counts.get(label, 0) + 1
        boxes.append((label, x0, y0, x1, y1))

    for label, x0, y0, x1, y1 in boxes:
        if label in PERSON:
            # Dilate: the box frames the body, and a head often sits proud of it.
            pad_x = int((x1 - x0) * 0.28) + 6
            pad_y = int((y1 - y0) * 0.28) + 6
            mosaic(out, (x0 - pad_x, y0 - pad_y, x1 + pad_x, y1 + pad_y), blocks=4)
        elif label in VEHICLE:
            pad = int(max(x1 - x0, y1 - y0) * 0.10) + 4
            bx = (x0 - pad, y0 - pad, x1 + pad, y1 + pad)
            # A whole-box blur first, so text anywhere on the vehicle goes,
            # then a mosaic over the lower half where a plate actually sits.
            sub = out[max(0, bx[1]):bx[3], max(0, bx[0]):bx[2]]
            if sub.size:
                k = max(3, (min(sub.shape[:2]) // 6) | 1)
                out[max(0, bx[1]):bx[3], max(0, bx[0]):bx[2]] = cv2.GaussianBlur(
                    sub, (k, k), 0
                )
            mid = y0 + int((y1 - y0) * 0.45)
            mosaic(out, (x0 - pad, mid, x1 + pad, y1 + pad), blocks=5)

    if draw_boxes:
        for label, x0, y0, x1, y1 in boxes:
            if label not in VEHICLE | PERSON:
                continue
            colour = BOX_PERSON if label in PERSON else BOX_VEHICLE
            cv2.rectangle(out, (x0, y0), (x1, y1), colour, 2)
            text = label if label in PERSON else label
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(out, (x0, y0 - th - 6), (x0 + tw + 6, y0), colour, -1)
            cv2.putText(out, text, (x0 + 3, y0 - 4), cv2.FONT_HERSHEY_SIMPLEX,
                        0.45, (255, 255, 255), 1, cv2.LINE_AA)

    return out, counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stills", nargs="*", default=None,
        help="video:seconds[:left,top,right,bottom] -- the optional crop is "
             "given as fractions of the frame and is applied BEFORE detection, "
             "so an object close to the lens does not generate boxes that are "
             "then drawn over the street. e.g. TC_2026.mov:8:0,0,0.8,1")
    args = parser.parse_args()

    if not args.stills:
        raise SystemExit("nothing requested; pass --stills name.mov:seconds ...")

    OUT.mkdir(parents=True, exist_ok=True)
    model = YOLO(str(ROOT / "yolov8n.pt"))

    for spec in args.stills:
        parts = spec.split(":")
        name, seconds = parts[0], parts[1]
        crop = [float(v) for v in parts[2].split(",")] if len(parts) > 2 else None

        capture = cv2.VideoCapture(str(VIDEOS / name))
        fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(float(seconds) * fps))
        ok, frame = capture.read()
        capture.release()
        if not ok:
            print(f"  !! could not read {name} at {seconds}s")
            continue

        # Order matters: the overlay is killed in the ORIGINAL frame's
        # coordinates, before any crop moves them, and before detection, so
        # the burned-in text cannot be read and cannot be detected as an object.
        h, w = frame.shape[:2]
        l, t, r, b = OVERLAY
        x0, y0, x1, y1 = int(l * w), int(t * h), int(r * w), int(b * h)
        strip = frame[y0:y1, x0:x1]
        if strip.size:
            k = max(31, (min(strip.shape[:2]) // 3) | 1)
            frame[y0:y1, x0:x1] = cv2.GaussianBlur(strip, (k, k), 0)
        mosaic(frame, (x0, y0, x1, y1), blocks=7)

        if crop:
            h, w = frame.shape[:2]
            l, t, r, b = crop
            frame = frame[int(t * h):int(b * h), int(l * w):int(r * w)]

        redacted, counts = redact(frame, model)
        target = OUT / f"{Path(name).stem}_t{seconds}.jpg"
        cv2.imwrite(str(target), redacted, [cv2.IMWRITE_JPEG_QUALITY, 88])
        traffic = {k: v for k, v in sorted(counts.items()) if k in VEHICLE | PERSON}
        print(f"  {target.relative_to(ROOT)}  {traffic}")


if __name__ == "__main__":
    main()
