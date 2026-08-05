"""Comptage de véhicules sur les vidéos trafic par computer vision (YOLO).

Pour chaque vidéo de data/raw/hanoi/videos/Videos/ (nom horodaté, ex.
TC_20260708_174500.mov) :
  - échantillonne ~1 image/seconde
  - détecte motorbike / car / bus / truck avec YOLOv8 (COCO)
  - agrège en moyenne de véhicules visibles par image ("densité de trafic",
    robuste : pas besoin de tracking pour comparer des points entre eux)
  - apparie la vidéo à la mesure Kobo la plus proche dans le temps (< 5 min)

Sortie : data/processed/hanoi/vehicle_counts.csv
  video, video_start, n_frames, moto_mean, car_mean, bus_mean, truck_mean,
  vehicles_mean, matched_timestamp, matched_dB, match_gap_s

Usage : python3 scripts/experiments/count_vehicles.py [--limit N]  (~10-20 s/vidéo)
"""
import argparse
import glob
import os
import re
import sys

import cv2
import numpy as np
import pandas as pd
from ultralytics import YOLO

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VID_DIR = os.path.join(ROOT, 'data', 'raw', 'hanoi', 'videos', 'Videos')
OUT = os.path.join(ROOT, 'data', 'processed', 'hanoi', 'vehicle_counts.csv')
MEASURES = os.path.join(ROOT, 'data', 'raw', 'hanoi', 'measurements.csv')

# classes COCO -> nos catégories
CLASSES = {1: 'bicycle', 2: 'car', 3: 'moto', 5: 'bus', 7: 'truck'}
MATCH_MAX_S = 300  # appariement vidéo<->mesure : 5 min max


def video_start(path):
    m = re.search(r'(20\d{6})_(\d{6})', os.path.basename(path))
    if not m:
        return None
    return pd.to_datetime(m.group(1) + m.group(2), format='%Y%m%d%H%M%S')


def count_video(model, path, sample_fps=1.0):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    step = max(int(round(fps / sample_fps)), 1)
    counts, i = [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            r = model(frame, imgsz=640, conf=0.3, verbose=False)[0]
            c = {v: 0 for v in CLASSES.values()}
            for cls in r.boxes.cls.tolist():
                if int(cls) in CLASSES:
                    c[CLASSES[int(cls)]] += 1
            counts.append(c)
        i += 1
    cap.release()
    return pd.DataFrame(counts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=None, help='ne traiter que N vidéos (test)')
    args = ap.parse_args()

    # Recherche RÉCURSIVE sous data/raw/hanoi/ : selon la façon dont les vidéos ont été
    # rapatriées (Drive, téléphone, clé USB) elles atterrissent dans des sous-dossiers
    # variés (ex. drive-download-2026.../). On ne déplace pas les fichiers de l'utilisateur.
    roots = [VID_DIR, os.path.join(ROOT, 'data', 'raw', 'hanoi')]
    seen, videos = set(), []
    for r in roots:
        for ext in ('mov', 'mp4', 'MOV', 'MP4'):
            for f in glob.glob(f'{r}/**/*.{ext}', recursive=True):
                key = os.path.basename(f)
                if key not in seen:          # un même nom = une même vidéo
                    seen.add(key); videos.append(f)
    videos = sorted(videos, key=os.path.basename)
    if args.limit:
        videos = videos[:args.limit]
    meas = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    model = YOLO('yolov8n.pt')  # nano : bon compromis vitesse/qualité pour compter

    # reprise : on repart de l'existant et on ne refait pas les vidéos déjà traitées
    prev = pd.read_csv(OUT) if os.path.exists(OUT) else pd.DataFrame(columns=['video'])
    rows = prev.to_dict('records')
    done = set(prev['video'])

    for k, v in enumerate(videos):
        name = os.path.basename(v)
        if name in done:
            continue
        start = video_start(v)
        df = count_video(model, v)
        if df.empty:
            print(f'  [{k+1}/{len(videos)}] {name} : illisible, ignorée', flush=True)
            continue
        row = {'video': name, 'video_start': start, 'n_frames': len(df)}
        for c in df.columns:
            row[f'{c}_mean'] = round(df[c].mean(), 2)
        row['vehicles_mean'] = round(df[list(df.columns)].sum(axis=1).mean(), 2)
        # appariement à la mesure la plus proche
        if start is not None:
            gaps = (meas.timestamp - start).abs()
            j = gaps.idxmin()
            if gaps[j].total_seconds() <= MATCH_MAX_S:
                row['matched_timestamp'] = meas.loc[j, 'timestamp']
                row['matched_dB'] = meas.loc[j, 'noise_dB']
                row['match_gap_s'] = int(gaps[j].total_seconds())
        rows.append(row)
        print(f'  [{k+1}/{len(videos)}] {name} : {row["vehicles_mean"]} véh/image'
              + (f' <-> {row.get("matched_dB", "?")} dB' if 'matched_dB' in row else ' (pas de mesure appariée)'),
              flush=True)
        pd.DataFrame(rows).to_csv(OUT, index=False)  # sauvegarde incrémentale

    print(f'\nOK -> {OUT}')
    final = pd.read_csv(OUT)
    print(f'{len(final)} vidéos traitées, {final["matched_dB"].notna().sum()} appariées à une mesure')
    if final['matched_dB'].notna().sum() > 5:
        m = final.dropna(subset=['matched_dB'])
        print(f'corrélation véhicules/image <-> dB : r = {m.vehicles_mean.corr(m.matched_dB):+.2f}')


if __name__ == '__main__':
    main()
