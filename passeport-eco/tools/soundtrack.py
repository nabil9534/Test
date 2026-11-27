"""Bande-son Passeport Éco : musique synthétisée + effets calés sur l'animation (+ voix off si fournie).

Usage : python3 tools/soundtrack.py <slug> [voix.wav]
Lit build/<slug>.sfx.json (écrit par record.js) et écrit build/<slug>.wav.
Avec une voix : la musique baisse automatiquement sous la voix (ducking) et les effets restent présents.
Aucun échantillon externe : tout est généré, donc pas de problème de droits.
"""
import json, sys, wave, subprocess, pathlib
import numpy as np
from scipy.signal import butter, sosfilt

ROOT = pathlib.Path(__file__).resolve().parent.parent
SR = 48000
slug = sys.argv[1]
voice_path = sys.argv[2] if len(sys.argv) > 2 else None
info = json.load(open(ROOT / f"build/{slug}.sfx.json"))
spec = json.load(open(ROOT / f"specs/{slug}.json", encoding="utf-8"))
TOTAL = info["total"]
DUR = TOTAL / 1000 + 1.0
N = int(SR * DUR)
rng = np.random.default_rng(abs(hash(slug)) % 2**32)
KEY = 2 ** (spec.get("key", 0) / 12)          # transposition de la musique par épisode

BUS = {"m": np.zeros((N, 2)), "s": np.zeros((N, 2))}
IMPACTS = []

def at(ms): return int(ms / 1000 * SR)
def lp(x, f, o=2): return sosfilt(butter(o, f, "low", fs=SR, output="sos"), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, "high", fs=SR, output="sos"), x)
def bp(x, lo, hi): return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)
def env(n, tau): return np.exp(-np.arange(n) / SR / tau)
def noise(n): return rng.standard_normal(n)
def saw(f, n, d=0.0): return 2 * ((np.arange(n) / SR * f * (1 + d)) % 1) - 1
def put(bus, sig, ms, g=1.0, pan=0.0):
    i = at(ms)
    if i >= N or i < 0: return
    s = sig[: N - i] * g
    BUS[bus][i:i + len(s), 0] += s * np.sqrt((1 - pan) / 2) * 1.414
    BUS[bus][i:i + len(s), 1] += s * np.sqrt((1 + pan) / 2) * 1.414

# ---------- instruments ----------
def kick():
    n = at(450); t = np.arange(n) / SR; f = 45 + 95 * np.exp(-t / 0.035)
    return np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.16))
def hat(o=False):
    n = at(260 if o else 60); return hp(noise(n), 7000) * env(n, 0.09 if o else 0.018) * 0.5
def clap():
    n = at(300); e = env(n, 0.07)
    for d in (0, 12, 24): k = at(d); e[k:k + at(8)] += 0.6
    return bp(noise(n), 900, 4000) * e * 0.6
def bass(f, ms):
    n = at(ms); x = saw(f, n) + 0.6 * saw(f / 2, n)
    return lp(x, 380) * np.minimum(1, np.arange(n) / at(6)) * env(n, 0.22) * 0.55
def pad(fs, ms):
    n = at(ms); x = sum(saw(f, n, d) for f in fs for d in (-0.004, 0.004))
    x = lp(x, 1500) / (2 * len(fs))
    return x * np.minimum(1, np.arange(n) / at(400)) * np.minimum(1, (n - np.arange(n)) / at(400)) * 0.35
def pluck(f, ms=220):
    n = at(ms); t = np.arange(n) / SR
    x = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sin(4 * np.pi * f * t) * 0.3
    return lp(x, 2600) * env(n, 0.08) * 0.22

# ---------- effets ----------
def whoosh(ms=560):
    n = at(ms); x = noise(n); tt = np.linspace(0, 1, n); out = np.zeros(n)
    for i in range(0, n, 1024):
        fc = 400 + 5000 * tt[i] ** 2; out[i:i + 1024] = bp(x[i:i + 1024], fc * 0.6, min(fc * 1.6, 23000))
    return out * np.sin(np.pi * tt) ** 1.5 * 0.5
def riser(ms, f0=200, f1=1600):
    n = at(ms); tt = np.linspace(0, 1, n); f = f0 * (f1 / f0) ** tt; ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * 0.5 + 0.5 * np.sin(ph * 1.005 + 1) + hp(noise(n), 3000) * 0.25 * tt) * tt ** 2 * 0.35
def impact(low=50):
    n = at(1400); t = np.arange(n) / SR; f = low + 70 * np.exp(-t / 0.05)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.45)
    return np.tanh(1.6 * (boom + lp(noise(n), 3500) * env(n, 0.03) * 0.8 + lp(noise(n), 900) * env(n, 0.5) * 0.15)) * 0.9
def blip(f, ms=90, g=0.3):
    n = at(ms); return np.sin(2 * np.pi * f * np.arange(n) / SR) * env(n, 0.03) * g
def sonar(f=1320):
    n = at(1400); return np.sin(2 * np.pi * f * np.arange(n) / SR) * env(n, 0.35) * 0.22
def buzzer():
    n = at(420); return lp(saw(110, n) + saw(116.5, n), 1800) * np.minimum(1, (n - np.arange(n)) / at(60)) * 0.28
def typekey():
    n = at(40); return bp(noise(n), 1500, 6000) * env(n, 0.006) * 0.5
def thud():  # coup de tampon : grave mat + claquement de bois
    n = at(500); t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (70 + 60 * np.exp(-t / 0.02)) * t) * env(n, 0.09)
    click = bp(noise(n), 600, 2500) * env(n, 0.012)
    return np.tanh(2 * (body + click)) * 0.9
def chime():  # carillon d'annonce d'aéroport : trois notes descendantes
    out = np.zeros(at(2200))
    for i, f in enumerate((784.0, 659.25, 523.25)):
        n = at(1500); t = np.arange(n) / SR
        x = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2 * t) + 0.12 * np.sin(2 * np.pi * f * 3.01 * t)) * env(n, 0.5)
        k = at(i * 330); out[k:k + n] += x[: len(out) - k]
    return out * 0.22
def cash():
    n = at(900); t = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * f * t) * a for f, a in ((2093, .5), (2637, .35), (4186, .2))) * env(n, 0.25) * 0.2

# ---------- placement des effets ----------
final_t = TOTAL; gaps = []
for e in info["sfx"]:
    t, k, d = e["t"], e["k"], e.get("d", 0)
    if k == "whoosh": put("s", whoosh(), t - 300, 0.9)
    elif k == "stamp":
        put("s", riser(500, 300, 1400), t - 500, 0.6); put("s", thud(), t + 150, 1.3); put("s", impact(55), t + 150, 0.8)
        IMPACTS.append(t + 150)
    elif k == "count":
        steps = max(8, int(d / 70))
        for i, ms in enumerate(np.linspace(t, t + d - 50, steps)):
            put("s", blip(600 + i * 900 / steps, 45, 0.18), ms, 1, 0.2 if i % 2 else -0.2)
        put("s", riser(d, 150, 900), t, 0.6)
    elif k == "impact": put("s", impact(), t, 0.85); IMPACTS.append(t)
    elif k == "riser": put("s", riser(d or 1500, 250, 1800), t, 0.75)
    elif k == "blip": put("s", blip(330, 160, 0.25), t)
    elif k == "sonar":
        for i in range(3): put("s", sonar(1320 if i % 2 == 0 else 1100), t + i * 1000)
    elif k == "hit":
        put("s", impact(65), t, 0.55); IMPACTS.append(t)
        for j in range(6): put("s", typekey(), t + 250 + j * 70, 0.9, float(rng.uniform(-.4, .4)))
    elif k == "faux":
        gaps.append((t - 700, t)); put("s", riser(900, 200, 2400), t - 900, 0.7)
        put("s", impact(40), t, 1.25); put("s", buzzer(), t, 0.9); IMPACTS.append(t)
    elif k == "final":
        final_t = t; put("s", impact(45), t, 1.0); IMPACTS.append(t)
    elif k == "next": put("s", chime(), t, 1.0)
put("s", cash(), 1400, 0.6, 0.3)  # petite cloche après le tampon d'entrée

# ---------- musique : 120 BPM, progression mineure, transposée par épisode ----------
BEAT = 500
chords = [(110.0, [220.0, 261.63, 329.63]), (87.31, [174.61, 220.0, 261.63]),
          (130.81, [261.63, 329.63, 392.0]), (98.0, [196.0, 246.94, 293.66])]
arps = [[440, 523.25, 659.25, 523.25], [349.23, 440, 523.25, 440], [523.25, 659.25, 783.99, 659.25], [392, 493.88, 587.33, 493.88]]
START_FULL = 1300
def in_gap(ms): return any(a <= ms < b for a, b in gaps)
bar = 0
for b0 in range(0, int(final_t), BEAT * 4):
    root, ch = chords[bar % 4]
    if b0 + BEAT * 4 > START_FULL: put("m", pad([f * KEY for f in ch], BEAT * 4 + 300), b0, 0.9)
    for beat in range(4):
        ms = b0 + beat * BEAT
        if ms >= final_t or in_gap(ms): continue
        full = ms >= START_FULL
        if full:
            put("m", kick(), ms, 0.45)
            if beat % 2: put("m", clap(), ms, 0.4, 0.1)
            put("m", bass(root * KEY, BEAT * .45), ms); put("m", bass(root * KEY, BEAT * .4), ms + BEAT / 2, 0.8)
            put("m", pluck(arps[bar % 4][beat] * KEY * (2 if bar % 2 else 1)), ms + BEAT / 4, 1, -0.35 + 0.7 * (beat % 2))
        for s in range(2 if full else 1):
            put("m", hat(s == 1 and beat == 3), ms + s * BEAT / 2 + (0 if full else BEAT / 4), 0.7 if full else 0.45, 0.3)
    bar += 1
put("m", pad([f * KEY for f in (220.0, 261.63, 329.63, 440.0)], int(DUR * 1000 - final_t)), final_t, 1.6)

# ---------- mixage ----------
duck = np.ones(N)
for ms in IMPACTS:
    i = at(ms); k = min(at(900), N - i)
    if k > 0: duck[i:i + k] = np.minimum(duck[i:i + k], 1 - 0.6 * np.exp(-np.arange(k) / SR / 0.35))
music_gain, sfx_gain = 0.75, 1.3
mix_voice = None
if voice_path:
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", voice_path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    v = np.frombuffer(raw, dtype=np.float32).astype(float)[:N]
    v = np.pad(v, (0, N - len(v)))
    v = hp(v, 80); v /= np.max(np.abs(v)) + 1e-9
    # enveloppe de la voix → la musique descend quand on parle
    e = np.abs(v); k = at(30); e = np.convolve(e, np.ones(k) / k, "same"); e = e / (np.max(e) + 1e-9)
    speaking = np.clip(e * 8, 0, 1); speaking = np.convolve(speaking, np.ones(at(250)) / at(250), "same")
    duck *= 1 - 0.65 * np.clip(speaking, 0, 1)
    music_gain, sfx_gain = 0.55, 0.9
    mix_voice = np.stack([v, v], 1) * 1.6
mix = BUS["m"] * duck[:, None] * music_gain + BUS["s"] * sfx_gain
if mix_voice is not None: mix += mix_voice
fade = np.ones(N); fo = at(1200); fade[-fo:] = np.linspace(1, 0, fo); mix *= fade[:, None]
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.6) / np.tanh(1.6) * 0.92
w = wave.open(str(ROOT / f"build/{slug}.wav"), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((mix * 32767).astype("<i2").tobytes()); w.close()
print(slug, "bande-son", f"{DUR:.1f}s", "avec voix" if voice_path else "sans voix")
