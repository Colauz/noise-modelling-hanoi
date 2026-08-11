"""Count vehicles on the traffic videos by computer vision (YOLOv8 + ByteTrack).

V2 (August 2026) - FROM DENSITY TO FLOW
---------------------------------------
V1 sampled ~1 frame/s and measured a DENSITY (mean number of vehicles visible per
frame). That choice produced the negative result documented in section 5.x of
docs/negative-results.md: density is a STOCK, whereas acoustic emission is governed
by a FLOW (rate Q, veh/h) and by speed. The two decouple exactly where it matters:
in congestion density is maximal and flow collapses. All three emission coefficients
came out null under the non-negativity constraint.

This version applies the recommendation we made ourselves: count LINE-CROSSING EVENTS
by object tracking.

  - sampling at SAMPLE_FPS (10 fps): tracking requires consecutive frames; at 1 fps no
    tracker can associate detections;
  - detection + ByteTrack tracking (identifiers persistent across frames);
  - a VIRTUAL CROSSING LINE at the CENTRE of the image, whose ORIENTATION is chosen
    per video (see guard 3): a vehicle is counted when the trajectory of its centre
    crosses the line;
  - flow = crossings / observed duration, expressed in vehicles per MINUTE, per class;
  - a trajectory's class is the majority vote of its detections (more robust than
    frame-by-frame classification).

THREE GUARDS, ESTABLISHED BY CALIBRATING ON OUR OWN VIDEOS
(full reasoning, parameters and limitations: docs/methodology.md section 2b)
---------------------------------------------------------
1. RELATIVE DEAD BAND (DEADBAND_FRAC = 5 % of the image height, not a fixed pixel
   count). Our videos do not all share a resolution: 1080x1920 for the IMG_*,
   1280x720 for the TC_*. A dead band in absolute pixels is 4 % of the height in one
   case and 13 % in the other - it let all the jitter through on one side and blocked
   every crossing on the other.
2. AT MOST ONE CROSSING PER DIRECTION PER TRAJECTORY (MAX_CROSS_PER_DIR). ByteTrack
   keeps few long-lived identifiers on our sparsely populated scenes and reassigns them
   to new vehicles: counting every side change gave 109 veh/min on a video where 0.6
   vehicles are visible per frame. Little's law (L = lambda x W) then implies a
   residence time of 0.3 s, i.e. 60-90 m/s: absurd. Counting once per direction brings
   it to 12 veh/min, a residence time of 3.0 s, physically coherent. The script checks
   and prints this diagnostic at the end.
3. LINE ORIENTATION CHOSEN PER VIDEO. A horizontal line only counts VERTICAL movement
   in the image. Our VID_* videos are filmed across the street: vehicles cross the
   field from left to right and never cross a median horizontal line. Result of the
   first pass: 14 of the 19 VID_* videos reported ZERO flow although they show 2.1
   vehicles per frame and 9 trajectories on average. A whole site came out at zero flow
   for a purely geometric reason. We therefore measure, per video, the horizontal and
   vertical displacement amplitude of the trajectories, and place the line
   PERPENDICULAR to the dominant motion. The chosen axis is recorded in the `line_axis`
   column of the CSV so that it can be checked.

WHAT THE SCRIPT STILL DOES NOT DO (to be documented in the paper):
  - no ground homography: SPEED is not estimated, only flow is;
  - the detector is still NOT validated against a reference manual count.
    The modal shares remain lower bounds on the two-wheeler share.

OUTPUT COLUMNS (data/processed/vehicle_counts.csv)
  video, video_start, duration_s, n_frames, sample_fps
  {class}_mean        density: mean vehicles visible per frame   (v1 backward-compatible)
  vehicles_mean       sum of the densities                        (v1 backward-compatible)
  {class}_flow        FLOW: line crossings per minute
  vehicles_flow       total flow excluding bicycles (moto + car + bus + truck)
  n_tracks            number of distinct trajectories seen
  matched_timestamp, matched_dB, match_gap_s   match to the nearest Kobo measurement

Usage: python3 scripts/02_count_vehicles.py [--limit N] [--force]
  ~10 s per video, i.e. ~26 min for the 147 videos. Resumes automatically (--force to
  recompute everything: mandatory when moving from v1 to v2, since the flow columns do
  not exist in v1). Reads the videos from data/raw/videos/, which are not published.
"""
import argparse
import glob
import os
import re
from collections import Counter, defaultdict

import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO

from noise_hanoi import config as cfg

ROOT = cfg.ROOT
VID_DIR = cfg.VIDEO_DIR
OUT = cfg.VEHICLE_COUNTS
MEASURES = cfg.MEASUREMENTS

# COCO classes -> our categories
CLASSES = {1: 'bicycle', 2: 'car', 3: 'moto', 5: 'bus', 7: 'truck'}
FLOW_CLASSES = ['moto', 'car', 'bus', 'truck']   # a bicycle is not a motorised source
MATCH_MAX_S = 300        # video<->measurement matching: 5 min maximum
SAMPLE_FPS = 10.0        # sampling rate: a trade-off between tracking and CPU cost
DEADBAND_FRAC = 0.05     # dead band = 5 % of image HEIGHT (resolutions differ)
MAX_CROSS_PER_DIR = 1    # at most one crossing per direction per trajectory
TRACKER = 'bytetrack.yaml'


def video_start(path):
    m = re.search(r'(20\d{6})_(\d{6})', os.path.basename(path))
    if not m:
        return None
    return pd.to_datetime(m.group(1) + m.group(2), format='%Y%m%d%H%M%S')


def track_video(model, path, sample_fps=SAMPLE_FPS):
    """Track the vehicles and count crossings of a median line.

    Returns a dict of results. Crossings are counted in
    POST-PROCESSING over the stored trajectories (`count_crossings`), not frame by
    frame: that is what allows the line orientation to be chosen once the video has
    been seen in full, and it makes the counting rule testable without rerunning YOLO.
    """
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0.0
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0.0
    step = max(int(round(fps / sample_fps)), 1)

    per_frame = []                       # density: count per sampled frame
    traj = defaultdict(list)             # track_id -> [(cx, cy), ...]
    cls_votes = defaultdict(Counter)     # track_id -> votes de classe
    i = n_sampled = 0

    while True:
        if not cap.grab():
            break
        if i % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            # persist=False on the first frame: resets the tracker between videos,
            # otherwise the previous video's identifiers leak into this one.
            r = model.track(frame, imgsz=640, conf=0.3, tracker=TRACKER,
                            persist=(n_sampled > 0), verbose=False)[0]
            n_sampled += 1

            c = {v: 0 for v in CLASSES.values()}
            if r.boxes is not None and r.boxes.id is not None:
                for tid, cl, (cx, cy, _, _) in zip(r.boxes.id.tolist(),
                                                   r.boxes.cls.tolist(),
                                                   r.boxes.xywh.tolist()):
                    if int(cl) not in CLASSES:
                        continue
                    name = CLASSES[int(cl)]
                    c[name] += 1
                    tid = int(tid)
                    cls_votes[tid][name] += 1
                    traj[tid].append((cx, cy))
            elif r.boxes is not None:
                for cl in r.boxes.cls.tolist():   # frame without ids: density only
                    if int(cl) in CLASSES:
                        c[CLASSES[int(cl)]] += 1
            per_frame.append(c)
        i += 1
    cap.release()

    duration_s = i / fps if fps else 0.0
    flows, axis = count_crossings(traj, cls_votes, w, h)
    # mean residence time of a trajectory: used for the Little's law check
    dwell_s = (np.mean([len(v) for v in traj.values()]) / sample_fps) if traj else 0.0
    return {'density': pd.DataFrame(per_frame), 'flows': flows, 'n_frames': n_sampled,
            'duration_s': duration_s, 'n_tracks': len(traj), 'dwell_s': dwell_s,
            'axis': axis}


def count_crossings(traj, cls_votes, w, h):
    """Count crossings of the median line, with the orientation chosen from the data.

    1. ORIENTATION. We sum the displacement amplitude of each trajectory along x and
       along y, each one NORMALISED BY THE CORRESPONDING IMAGE DIMENSION. If the
       dominant motion is horizontal, the line must be VERTICAL (at mid-width);
       otherwise horizontal. A line parallel to the flow would never be
       franchie — c'est le garde-fou n°3.

       The normalisation is not cosmetic. Comparing amplitudes in RAW PIXELS
       mechanically favours the larger image dimension: on our portrait videos
       (1080x1920, 2160x3840), a lateral movement crossing the whole field spans
       fewer pixels than a vertical movement crossing only a fraction of it.
       On IMG_20260622_062700 the raw test picks the y axis (span 5139 against
       3681) and the normalised test picks x (3.41 against 2.68) -- the second is the
       one that describes the real motion.
    2. COUNTING. For each trajectory we remember which side it was on the last time
       it was clearly on one side (beyond the dead band); a crossing is counted on a
       change of side, at most MAX_CROSS_PER_DIR times per DIRECTION (guard 2: the
       identifiers reused by the tracker
       produisent sinon des dizaines de faux franchissements).
    """
    span_x = sum(max(p[0] for p in t) - min(p[0] for p in t) for t in traj.values() if t)
    span_y = sum(max(p[1] for p in t) - min(p[1] for p in t) for t in traj.values() if t)
    # amplitudes normalised by the image dimension: comparing raw pixels
    # would mechanically favour the longer side (see docstring).
    axis = 0 if (span_x / (w or 1)) > (span_y / (h or 1)) else 1   # 0 = x (ligne verticale)
    extent = (w if axis == 0 else h) or 1.0
    line, deadband = extent / 2.0, DEADBAND_FRAC * extent

    flows = {v: 0 for v in CLASSES.values()}
    for tid, pts in traj.items():
        side, done = None, Counter()
        n = 0
        for p in pts:
            v = p[axis]
            if v > line + deadband:
                cur = 1
            elif v < line - deadband:
                cur = -1
            else:
                continue                        # dans la bande morte : on ne tranche pas
            if side is not None and side != cur and done[cur] < MAX_CROSS_PER_DIR:
                n += 1
                done[cur] += 1
            side = cur
        if n and cls_votes[tid]:
            flows[cls_votes[tid].most_common(1)[0][0]] += n
    return flows, ('x' if axis == 0 else 'y')


def find_videos():
    """RECURSIVE search under the video directory: depending on how the videos were
    brought back (Drive, phone, USB stick) they land in assorted subfolders
    (e.g. drive-download-2026.../). We do not move the user's files."""
    roots = [VID_DIR]
    seen, videos = set(), []
    for r in roots:
        for ext in ('mov', 'mp4', 'MOV', 'MP4'):
            for f in glob.glob(f'{r}/**/*.{ext}', recursive=True):
                key = os.path.basename(f)
                if key not in seen:          # same filename = same video
                    seen.add(key)
                    videos.append(f)
    return sorted(videos, key=os.path.basename)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=None, help='process only N videos (test)')
    ap.add_argument('--force', action='store_true',
                    help='ignorer le CSV existant et tout recalculer (requis v1 -> v2)')
    args = ap.parse_args()

    videos = find_videos()
    if args.limit:
        videos = videos[:args.limit]
    meas = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    model = YOLO('yolov8n.pt')  # nano: a speed/quality trade-off -- NOT validated, see docstring

    # resume: we start from what exists and do not redo videos already processed.
    # A v1 CSV (no flow column) is rejected: its rows are not comparable.
    prev = pd.DataFrame(columns=['video'])
    if os.path.exists(OUT) and not args.force:
        prev = pd.read_csv(OUT)
        if 'vehicles_flow' not in prev.columns:
            raise SystemExit(
                f'{OUT} is in v1 format (density only, no flow column).\n'
                '  -> rerun with --force to recompute the 147 videos in v2.')
    rows = prev.to_dict('records')
    done = set(prev['video'])

    for k, v in enumerate(videos):
        name = os.path.basename(v)
        if name in done:
            continue
        start = video_start(v)
        R = track_video(model, v)
        df, flows, duration_s = R['density'], R['flows'], R['duration_s']
        if df.empty or duration_s <= 0:
            print(f'  [{k+1}/{len(videos)}] {name}: unreadable, skipped', flush=True)
            continue
        minutes = duration_s / 60.0
        row = {'video': name, 'video_start': start, 'duration_s': round(duration_s, 1),
               'n_frames': R['n_frames'], 'sample_fps': SAMPLE_FPS,
               'n_tracks': R['n_tracks'], 'dwell_s': round(R['dwell_s'], 2),
               'line_axis': R['axis']}
        for c in df.columns:                              # density (v1 backward-compatible)
            row[f'{c}_mean'] = round(df[c].mean(), 2)
        row['vehicles_mean'] = round(df.sum(axis=1).mean(), 2)
        for c, n in flows.items():                        # flow (new)
            row[f'{c}_flow'] = round(n / minutes, 2)
        row['vehicles_flow'] = round(sum(flows[c] for c in FLOW_CLASSES) / minutes, 2)
        # match to the nearest measurement
        if start is not None:
            gaps = (meas.timestamp - start).abs()
            j = gaps.idxmin()
            if gaps[j].total_seconds() <= MATCH_MAX_S:
                row['matched_timestamp'] = meas.loc[j, 'timestamp']
                row['matched_dB'] = meas.loc[j, 'noise_dB']
                row['match_gap_s'] = int(gaps[j].total_seconds())
        rows.append(row)
        print(f'  [{k+1}/{len(videos)}] {name}: {row["vehicles_flow"]:6.1f} veh/min '
              f'({row["vehicles_mean"]:5.2f} veh/frame, {R["n_tracks"]:3d} tracks, '
              f'ligne {"|" if R["axis"] == "x" else "-"})'
              + (f' <-> {row.get("matched_dB", "?")} dB' if 'matched_dB' in row else ' (unmatched)'),
              flush=True)
        pd.DataFrame(rows).to_csv(OUT, index=False)  # incremental save

    print(f'\nOK -> {OUT}')
    final = pd.read_csv(OUT)
    print(f'{len(final)} videos processed, {final["matched_dB"].notna().sum()} matched to a measurement')
    m = final.dropna(subset=['matched_dB'])
    if len(m) > 5:
        print('\ncorrelation with the measured level:')
        print(f'  density (v1, veh/frame): r = {m.vehicles_mean.corr(m.matched_dB):+.3f}')
        print(f'  FLOW    (v2, veh/min)  : r = {m.vehicles_flow.corr(m.matched_dB):+.3f}')
        print(f'  motorcycle flow        : r = {m.moto_flow.corr(m.matched_dB):+.3f}')
        print(f'\nmean flow: {m.vehicles_flow.mean():.1f} veh/min '
              f'(median {m.vehicles_flow.median():.1f}, max {m.vehicles_flow.max():.1f})')

        # --- physical consistency check via Little's law: L = lambda x W ---
        # The residence time implied by (density, flow) must be of the same order as
        # the residence time ACTUALLY observed on the trajectories. A gap of an
        # ordre de grandeur signale un sur-comptage de franchissements.
        ok = final[(final.vehicles_flow > 0) & (final.vehicles_mean > 0)]
        if len(ok):
            implied = ok.vehicles_mean / (ok.vehicles_flow / 60.0)
            ratio = (implied / ok.dwell_s.replace(0, np.nan)).median()
            print(f'\nLittle\'s law check (L = lambda x W):')
            print(f'  residence time implied by density/flow: median {implied.median():.1f} s')
            print(f'  residence time observed on trajectories: median {ok.dwell_s.median():.1f} s')
            print(f'  implied/observed ratio: {ratio:.2f}  '
                  + ('OK (meme ordre de grandeur)' if 0.3 < ratio < 3
                     else 'INCOHERENT -> revoir le comptage de franchissements'))


if __name__ == '__main__':
    main()
