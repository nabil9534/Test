"""Recale les scènes d'un épisode sur la voix off enregistrée.

Usage : python3 tools/retime.py <slug> <voix.(wav|mp3|m4a)>
- coupe le silence du début (la voix démarre à 0,3 s),
- repère les pauses entre les scènes (les N-1 plus longues pauses),
- écrit la durée de chaque scène ("dur") dans specs/<slug>.json,
- écrit la voix nettoyée dans build/<slug>.voice.wav.
Ensuite : tools/render.sh <slug> build/<slug>.voice.wav
"""
import json, re, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
slug, src = sys.argv[1], sys.argv[2]
spec_p = ROOT / f"specs/{slug}.json"
spec = json.load(open(spec_p, encoding="utf-8"))
n = len(spec["scenes"])
clean = ROOT / f"build/{slug}.voice.wav"

def silences(path, db=-38, d=0.35):
    err = subprocess.run(["ffmpeg", "-i", str(path), "-af", f"silencedetect=noise={db}dB:d={d}", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                               capture_output=True, text=True).stdout)
    return list(zip(st, en + [dur] * (len(st) - len(en)))), dur

# 1. nettoyage : mono 48 kHz, voix calée à 0,3 s, fin de silence coupée
sil, dur = silences(src)
lead = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{max(0, lead - 0.3):.3f}", "-i", src, "-ac", "1", "-ar", "48000",
                "-af", "areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,loudnorm=I=-16:TP=-1.5",
                str(clean)], check=True)

# 2. découpage en scènes sur les plus longues pauses
sil, dur = silences(clean)
inner = [(a, b) for a, b in sil if a > 0.5 and b < dur - 0.2]
if len(inner) < n - 1:
    sys.exit(f"Seulement {len(inner)} pauses trouvées pour {n} scènes : laisse ~1 s de silence entre chaque scène.")
cuts = sorted(sorted(inner, key=lambda p: p[1] - p[0], reverse=True)[: n - 1])
bounds = [0.0] + [round((a + b) / 2, 3) for a, b in cuts] + [dur]
for i, sc in enumerate(spec["scenes"]):
    d = (bounds[i + 1] - bounds[i]) * 1000
    if i == n - 1: d += 1500                      # on laisse respirer la fin
    sc["dur"] = int(max(d, 3200))
json.dump(spec, open(spec_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(slug, "voix", f"{dur:.1f}s", "scènes", [round(s["dur"] / 1000, 1) for s in spec["scenes"]])
