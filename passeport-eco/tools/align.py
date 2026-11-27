"""Cale les scènes d'un épisode sur une voix off (ElevenLabs ou enregistrée), sans transcription.

Usage : python3 tools/align.py <slug> <voix.(mp3|wav|m4a)> [coupures en s, ex. 5.1,9.4,…]
(les coupures forcées remplacent le calcul automatique, en secondes sur la voix nettoyée)

1. nettoie la voix (mono 48 kHz, volume normalisé, démarrage à 0,3 s) → build/<slug>.voice.wav
2. repère toutes les pauses (seuil adapté au bruit de fond du fichier)
3. choisit, parmi ces pauses, les N-1 coupures qui collent le mieux à la longueur de texte de
   chaque scène (programmation dynamique : pause longue = bonus, écart à la position attendue = malus)
4. écrit la durée de chaque scène ("dur") dans specs/<slug>.json
"""
import json, re, subprocess, sys, pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
SR = 48000
slug, src = sys.argv[1], sys.argv[2]
spec_p = ROOT / f"specs/{slug}.json"
spec = json.load(open(spec_p, encoding="utf-8"))
scenes = spec["scenes"]; n = len(scenes)
clean = ROOT / f"build/{slug}.voice.wav"
LEAD = 0.30

def load(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(float)

# 1. nettoyage
x = load(src)
hop = int(SR * 0.01)
rms = np.sqrt(np.convolve(x ** 2, np.ones(hop * 3) / (hop * 3), "same"))[::hop] + 1e-9
db = 20 * np.log10(rms)
floor, peak = np.percentile(db, 8), np.percentile(db, 95)
thr = floor + 0.32 * (peak - floor)                  # seuil « silence » adapté au fichier
speech = db > thr
first = np.argmax(speech); last = len(speech) - np.argmax(speech[::-1])
start_s = max(0, first * 0.01 - 0.05); end_s = last * 0.01 + 0.15
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{start_s:.3f}", "-to", f"{end_s:.3f}", "-i", str(src),
                "-ac", "1", "-ar", str(SR), "-af", f"adelay={int(LEAD*1000)},loudnorm=I=-15:TP=-1.5:LRA=9", str(clean)], check=True)

# 2. pauses sur la voix nettoyée
y = load(clean)
rms = np.sqrt(np.convolve(y ** 2, np.ones(hop * 3) / (hop * 3), "same"))[::hop] + 1e-9
db = 20 * np.log10(rms)
floor, peak = np.percentile(db, 8), np.percentile(db, 95)
quiet = db < floor + 0.32 * (peak - floor)
dur = len(y) / SR
pauses = []; i = 0
while i < len(quiet):
    if quiet[i]:
        j = i
        while j < len(quiet) and quiet[j]: j += 1
        a, b = i * 0.01, j * 0.01
        if b - a >= 0.18 and a > LEAD + 0.5 and b < dur - 0.3: pauses.append((a, b))
        i = j
    else: i += 1

# 3. coupures attendues d'après le nombre de mots de chaque scène
def words(s): return len(re.findall(r"[\wÀ-ÿ'’%,.-]+", s))
w = np.array([words(s["vo"]) for s in scenes], float)
talk = dur - LEAD - 0.2 - 0.9 * (n - 1)                # temps de parole hors pauses entre scènes
expected = [LEAD + talk * w[:k].sum() / w.sum() + 0.9 * (k - 0.5) for k in range(1, n)]

P = len(pauses)
if P < n - 1: sys.exit(f"{slug} : seulement {P} pauses trouvées pour {n} scènes.")
centers = [(a + b) / 2 for a, b in pauses]; lens = [b - a for a, b in pauses]
def score(k, p): return 4.0 * min(lens[p], 1.5) - abs(centers[p] - expected[k]) / 1.2
NEG = -1e9
best = np.full((n - 1, P), NEG); back = np.zeros((n - 1, P), int)
for p in range(P): best[0, p] = score(0, p)
for k in range(1, n - 1):
    run, arg = NEG, -1
    for p in range(P):
        if p - 1 >= 0 and best[k - 1, p - 1] > run: run, arg = best[k - 1, p - 1], p - 1
        if arg >= 0: best[k, p] = run + score(k, p); back[k, p] = arg
p = int(np.argmax(best[n - 2])); chosen = [p]
for k in range(n - 2, 0, -1): p = back[k, p]; chosen.append(p)
chosen = chosen[::-1]
cuts = [centers[p] for p in chosen]
if len(sys.argv) > 3:
    cuts = [float(c) for c in sys.argv[3].split(",")]
    assert len(cuts) == n - 1, f"il faut {n-1} coupures"

# 4. durées des scènes
bounds = [0.0] + cuts + [dur]
for k, sc in enumerate(scenes):
    d = (bounds[k + 1] - bounds[k]) * 1000
    if k == n - 1: d += 1800
    sc["dur"] = int(d)
json.dump(spec, open(spec_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"{slug} : voix {dur:.1f} s · {P} pauses · coupures", [round(c, 2) for c in cuts],
      "| attendues", [round(e, 1) for e in expected], "| pauses choisies", [round(lens[p], 2) for p in chosen])
