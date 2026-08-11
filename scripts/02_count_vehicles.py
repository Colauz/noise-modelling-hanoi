"""Comptage de véhicules sur les vidéos trafic par computer vision (YOLOv8 + ByteTrack).

V2 (août 2026) — DE LA DENSITÉ AU DÉBIT
---------------------------------------
La v1 échantillonnait ~1 image/s et mesurait une DENSITÉ (nombre moyen de véhicules
visibles par image). Ce choix a produit le résultat négatif documenté en §5.x de
paper/sections/negative_results.md : la densité est un STOCK, l'émission sonore est
gouvernée par un FLUX (débit Q, véh/h) et par la vitesse. Les deux se découplent
exactement là où ça compte : en congestion, la densité est maximale et le débit s'effondre.
Les trois coefficients d'émission ressortaient nuls sous contrainte de non-négativité.

Cette version applique la recommandation que nous formulions nous-mêmes : compter des
ÉVÉNEMENTS DE FRANCHISSEMENT DE LIGNE par suivi d'objets.

  - échantillonnage à SAMPLE_FPS (10 img/s) : le suivi exige des images consécutives,
    à 1 img/s aucun tracker ne peut associer les détections ;
  - détection + suivi ByteTrack (identifiants persistants entre images) ;
  - LIGNE DE FRANCHISSEMENT VIRTUELLE au CENTRE de l'image, dont l'ORIENTATION est
    choisie par vidéo (voir garde-fou n°3) : un véhicule est compté quand la
    trajectoire de son centre traverse la ligne ;
  - débit = franchissements / durée observée, exprimé en véhicules par MINUTE, par classe ;
  - la classe d'une trajectoire est le vote majoritaire de ses détections (plus robuste
    qu'une classification image par image).

TROIS GARDE-FOUS, ÉTABLIS EN CALIBRANT SUR NOS PROPRES VIDÉOS
-------------------------------------------------------------
1. BANDE MORTE RELATIVE (DEADBAND_FRAC = 5 % de la hauteur d'image, et non un nombre de
   pixels fixe). Nos vidéos n'ont pas toutes la même résolution : 1080x1920 pour les
   IMG_*, 1280x720 pour les TC_*. Une bande morte en pixels absolus vaut 4 % de la
   hauteur dans un cas et 13 % dans l'autre — elle laissait passer tout le jitter d'un
   côté et bloquait tous les franchissements de l'autre.
2. UN FRANCHISSEMENT AU PLUS PAR SENS ET PAR TRAJECTOIRE (MAX_CROSS_PER_DIR). ByteTrack
   maintient peu d'identifiants longue durée sur nos scènes peu peuplées et leur
   ré-associe les nouveaux véhicules : compter tous les changements de côté donnait
   109 véh/min sur une vidéo où 0,6 véhicule est visible par image. Or la loi de Little
   (L = lambda x W) impose alors un temps de présence de 0,3 s, soit 60-90 m/s : absurde.
   Compter une fois par sens ramène à 12 véh/min, soit un temps de présence de 3,0 s,
   physiquement cohérent. Le script vérifie et affiche ce diagnostic à la fin.
3. ORIENTATION DE LA LIGNE CHOISIE PAR VIDÉO. Une ligne horizontale ne compte que les
   mouvements VERTICAUX dans l'image. Nos vidéos VID_* sont filmées en travers de la
   rue : les véhicules y traversent le champ de gauche à droite et ne franchissent
   jamais une ligne horizontale médiane. Résultat de la première passe : 14 des 19
   vidéos VID_* affichaient un débit NUL alors qu'elles montrent 2,1 véhicules par
   image et 9 trajectoires en moyenne. Un site entier se retrouvait à débit zéro pour
   une raison purement géométrique. On mesure donc, sur chaque vidéo, l'amplitude de
   déplacement horizontale et verticale des trajectoires, et on place la ligne
   PERPENDICULAIREMENT au mouvement dominant. L'axe retenu est enregistré dans la
   colonne `line_axis` du CSV pour être vérifiable.

CE QUE LE SCRIPT NE FAIT TOUJOURS PAS (à documenter dans le papier) :
  - pas d'homographie sol : la VITESSE n'est pas estimée, seul le débit l'est ;
  - le détecteur n'est toujours PAS validé contre un comptage manuel de référence.
    Les parts modales restent des bornes inférieures sur la part de deux-roues.

COLONNES DE SORTIE (data/processed/hanoi/vehicle_counts.csv)
  video, video_start, duration_s, n_frames, sample_fps
  {classe}_mean       densité : moyenne de véhicules visibles par image  (rétro-compatible v1)
  vehicles_mean       somme des densités                                  (rétro-compatible v1)
  {classe}_flow       DÉBIT : franchissements de ligne par minute
  vehicles_flow       débit total hors vélos (moto + car + bus + truck)
  n_tracks            nombre de trajectoires distinctes vues
  matched_timestamp, matched_dB, match_gap_s   appariement à la mesure Kobo la plus proche

Usage : python3 scripts/experiments/count_vehicles.py [--limit N] [--force]
  ~10 s/vidéo, soit ~26 min pour les 147 vidéos. Reprise automatique (--force pour tout
  recalculer : obligatoire au passage v1 -> v2, les colonnes de débit n'existent pas en v1).
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

# classes COCO -> nos catégories
CLASSES = {1: 'bicycle', 2: 'car', 3: 'moto', 5: 'bus', 7: 'truck'}
FLOW_CLASSES = ['moto', 'car', 'bus', 'truck']   # le vélo n'est pas une source motorisée
MATCH_MAX_S = 300        # appariement vidéo<->mesure : 5 min max
SAMPLE_FPS = 10.0        # cadence d'échantillonnage : compromis suivi/coût CPU
DEADBAND_FRAC = 0.05     # bande morte = 5 % de la HAUTEUR d'image (résolutions hétérogènes)
MAX_CROSS_PER_DIR = 1    # au plus un franchissement par sens et par trajectoire
TRACKER = 'bytetrack.yaml'


def video_start(path):
    m = re.search(r'(20\d{6})_(\d{6})', os.path.basename(path))
    if not m:
        return None
    return pd.to_datetime(m.group(1) + m.group(2), format='%Y%m%d%H%M%S')


def track_video(model, path, sample_fps=SAMPLE_FPS):
    """Suit les véhicules et compte les franchissements d'une ligne horizontale médiane.

    Retourne un dict de résultats. Le comptage de franchissements est fait en
    POST-TRAITEMENT sur les trajectoires stockées (`count_crossings`), et non au fil des
    images : c'est ce qui permet de choisir l'orientation de la ligne une fois la vidéo
    entièrement vue, et cela rend la règle de comptage testable sans relancer YOLO.
    """
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0.0
    w = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0.0
    step = max(int(round(fps / sample_fps)), 1)

    per_frame = []                       # densité : comptage par image échantillonnée
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
            # persist=False sur la 1re image : réinitialise le tracker entre deux vidéos,
            # sinon les identifiants de la vidéo précédente fuient dans celle-ci.
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
                for cl in r.boxes.cls.tolist():   # image sans identifiants : densité seule
                    if int(cl) in CLASSES:
                        c[CLASSES[int(cl)]] += 1
            per_frame.append(c)
        i += 1
    cap.release()

    duration_s = i / fps if fps else 0.0
    flows, axis = count_crossings(traj, cls_votes, w, h)
    # temps de présence moyen d'une trajectoire : sert au contrôle par la loi de Little
    dwell_s = (np.mean([len(v) for v in traj.values()]) / sample_fps) if traj else 0.0
    return {'density': pd.DataFrame(per_frame), 'flows': flows, 'n_frames': n_sampled,
            'duration_s': duration_s, 'n_tracks': len(traj), 'dwell_s': dwell_s,
            'axis': axis}


def count_crossings(traj, cls_votes, w, h):
    """Compte les franchissements de la ligne médiane, orientation choisie sur les données.

    1. ORIENTATION. On somme l'amplitude de déplacement de chaque trajectoire selon x et
       selon y, chacune RAPPORTÉE À LA DIMENSION CORRESPONDANTE DE L'IMAGE. Si le
       mouvement dominant est horizontal, la ligne doit être VERTICALE (au milieu de la
       largeur) ; sinon horizontale. Une ligne parallèle au flux ne serait jamais
       franchie — c'est le garde-fou n°3.

       La normalisation n'est pas cosmétique. Comparer des amplitudes en PIXELS BRUTS
       favorise mécaniquement la plus grande dimension de l'image : sur nos vidéos
       portrait (1080x1920, 2160x3840), un déplacement latéral traversant tout le champ
       compte moins de pixels qu'un déplacement vertical qui n'en traverse qu'une
       fraction. Sur IMG_20260622_062700 le test brut désigne l'axe y (span 5139 contre
       3681) et le test normalisé désigne x (3,41 contre 2,68) — c'est le second qui
       décrit le mouvement réel.
    2. COMPTAGE. Pour chaque trajectoire on mémorise de quel côté elle se trouvait la
       dernière fois qu'elle était franchement d'un côté (au-delà de la bande morte) ;
       un franchissement est compté au changement de côté, au plus MAX_CROSS_PER_DIR
       fois par SENS (garde-fou n°2 : les identifiants ré-utilisés par le tracker
       produisent sinon des dizaines de faux franchissements).
    """
    span_x = sum(max(p[0] for p in t) - min(p[0] for p in t) for t in traj.values() if t)
    span_y = sum(max(p[1] for p in t) - min(p[1] for p in t) for t in traj.values() if t)
    # amplitudes rapportées à la dimension de l'image : comparer des pixels bruts
    # favoriserait mécaniquement le côté le plus long (cf. docstring).
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
    """Recherche RÉCURSIVE sous data/raw/hanoi/ : selon la façon dont les vidéos ont été
    rapatriées (Drive, téléphone, clé USB) elles atterrissent dans des sous-dossiers
    variés (ex. drive-download-2026.../). On ne déplace pas les fichiers de l'utilisateur."""
    roots = [VID_DIR]
    seen, videos = set(), []
    for r in roots:
        for ext in ('mov', 'mp4', 'MOV', 'MP4'):
            for f in glob.glob(f'{r}/**/*.{ext}', recursive=True):
                key = os.path.basename(f)
                if key not in seen:          # un même nom = une même vidéo
                    seen.add(key)
                    videos.append(f)
    return sorted(videos, key=os.path.basename)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=None, help='ne traiter que N vidéos (test)')
    ap.add_argument('--force', action='store_true',
                    help='ignorer le CSV existant et tout recalculer (requis v1 -> v2)')
    args = ap.parse_args()

    videos = find_videos()
    if args.limit:
        videos = videos[:args.limit]
    meas = pd.read_csv(MEASURES, parse_dates=['timestamp'])
    model = YOLO('yolov8n.pt')  # nano : bon compromis vitesse/qualité

    # reprise : on repart de l'existant et on ne refait pas les vidéos déjà traitées.
    # Un CSV v1 (sans colonne de débit) est rejeté : ses lignes ne sont pas comparables.
    prev = pd.DataFrame(columns=['video'])
    if os.path.exists(OUT) and not args.force:
        prev = pd.read_csv(OUT)
        if 'vehicles_flow' not in prev.columns:
            raise SystemExit(
                f'{OUT} est au format v1 (densité seule, pas de colonne de débit).\n'
                '  -> relancer avec --force pour recalculer les 147 vidéos en v2.')
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
            print(f'  [{k+1}/{len(videos)}] {name} : illisible, ignorée', flush=True)
            continue
        minutes = duration_s / 60.0
        row = {'video': name, 'video_start': start, 'duration_s': round(duration_s, 1),
               'n_frames': R['n_frames'], 'sample_fps': SAMPLE_FPS,
               'n_tracks': R['n_tracks'], 'dwell_s': round(R['dwell_s'], 2),
               'line_axis': R['axis']}
        for c in df.columns:                              # densité (rétro-compatible v1)
            row[f'{c}_mean'] = round(df[c].mean(), 2)
        row['vehicles_mean'] = round(df.sum(axis=1).mean(), 2)
        for c, n in flows.items():                        # débit (nouveau)
            row[f'{c}_flow'] = round(n / minutes, 2)
        row['vehicles_flow'] = round(sum(flows[c] for c in FLOW_CLASSES) / minutes, 2)
        # appariement à la mesure la plus proche
        if start is not None:
            gaps = (meas.timestamp - start).abs()
            j = gaps.idxmin()
            if gaps[j].total_seconds() <= MATCH_MAX_S:
                row['matched_timestamp'] = meas.loc[j, 'timestamp']
                row['matched_dB'] = meas.loc[j, 'noise_dB']
                row['match_gap_s'] = int(gaps[j].total_seconds())
        rows.append(row)
        print(f'  [{k+1}/{len(videos)}] {name} : {row["vehicles_flow"]:6.1f} véh/min '
              f'({row["vehicles_mean"]:5.2f} véh/image, {R["n_tracks"]:3d} traj., '
              f'ligne {"|" if R["axis"] == "x" else "-"})'
              + (f' <-> {row.get("matched_dB", "?")} dB' if 'matched_dB' in row else ' (non appariée)'),
              flush=True)
        pd.DataFrame(rows).to_csv(OUT, index=False)  # sauvegarde incrémentale

    print(f'\nOK -> {OUT}')
    final = pd.read_csv(OUT)
    print(f'{len(final)} vidéos traitées, {final["matched_dB"].notna().sum()} appariées à une mesure')
    m = final.dropna(subset=['matched_dB'])
    if len(m) > 5:
        print('\ncorrélation avec le niveau mesuré :')
        print(f'  densité (v1, véh/image) : r = {m.vehicles_mean.corr(m.matched_dB):+.3f}')
        print(f'  DÉBIT   (v2, véh/min)   : r = {m.vehicles_flow.corr(m.matched_dB):+.3f}')
        print(f'  débit motos             : r = {m.moto_flow.corr(m.matched_dB):+.3f}')
        print(f'\ndébit moyen : {m.vehicles_flow.mean():.1f} véh/min '
              f'(médiane {m.vehicles_flow.median():.1f}, max {m.vehicles_flow.max():.1f})')

        # --- contrôle de cohérence physique par la loi de Little : L = lambda x W ---
        # Le temps de présence impliqué par (densité, débit) doit être du même ordre que
        # le temps de présence RÉELLEMENT observé sur les trajectoires. Un écart d'un
        # ordre de grandeur signale un sur-comptage de franchissements.
        ok = final[(final.vehicles_flow > 0) & (final.vehicles_mean > 0)]
        if len(ok):
            implied = ok.vehicles_mean / (ok.vehicles_flow / 60.0)
            ratio = (implied / ok.dwell_s.replace(0, np.nan)).median()
            print(f'\ncontrôle loi de Little (L = lambda x W) :')
            print(f'  temps de présence impliqué par densité/débit : médiane {implied.median():.1f} s')
            print(f'  temps de présence observé sur les trajectoires : médiane {ok.dwell_s.median():.1f} s')
            print(f'  rapport impliqué/observé : {ratio:.2f}  '
                  + ('OK (meme ordre de grandeur)' if 0.3 < ratio < 3
                     else 'INCOHERENT -> revoir le comptage de franchissements'))


if __name__ == '__main__':
    main()
