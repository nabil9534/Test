"""Passeport Éco : génère la page animée d'un épisode à partir de sa fiche (specs/<pays>.json).

Usage : python3 builder.py specs/norvege.json   → build/norvege.html + build/norvege.events.json

Chaque scène a une durée calculée à partir du texte de la voix off (≈ 2,7 mots/s + 1 s de respiration),
ou fixée par "dur" (ms) une fois la vraie voix enregistrée.
"""
import json, sys, html, re, pathlib

WPS = 3.0          # débit visé, en mots par seconde (rythme nerveux de Short)
PAD = 900          # respiration ajoutée à chaque scène (ms)

FLAGS = {
    "norvege": '<svg viewBox="0 0 22 16"><rect width="22" height="16" fill="#ba0c2f"/><rect x="6" width="4" height="16" fill="#fff"/><rect y="6" width="22" height="4" fill="#fff"/><rect x="7" width="2" height="16" fill="#00205b"/><rect y="7" width="22" height="2" fill="#00205b"/></svg>',
    "argentine": '<svg viewBox="0 0 18 12"><rect width="18" height="12" fill="#74acdf"/><rect y="4" width="18" height="4" fill="#fff"/><circle cx="9" cy="6" r="1.4" fill="#f6b40e"/></svg>',
    "dubai": '<svg viewBox="0 0 24 12"><rect width="24" height="4" fill="#00732f"/><rect y="4" width="24" height="4" fill="#fff"/><rect y="8" width="24" height="4" fill="#000"/><rect width="6" height="12" fill="#c8102e"/></svg>',
    "coree": '<svg viewBox="0 0 18 12"><rect width="18" height="12" fill="#fff"/><g transform="rotate(-33.7 9 6)"><circle cx="9" cy="6" r="3" fill="#003478"/><path d="M6 6a3 3 0 0 1 6 0a1.5 1.5 0 0 1-3 0a1.5 1.5 0 0 0-3 0z" fill="#cd2e3a"/></g><g fill="#000"><g transform="rotate(-33.7 3.2 2.6)"><rect x="2" y="1.7" width="2.4" height=".4"/><rect x="2" y="2.4" width="2.4" height=".4"/><rect x="2" y="3.1" width="2.4" height=".4"/></g><g transform="rotate(33.7 14.8 2.6)"><rect x="13.6" y="1.7" width="2.4" height=".4"/><rect x="13.6" y="2.4" width="2.4" height=".4"/><rect x="13.6" y="3.1" width="2.4" height=".4"/></g><g transform="rotate(33.7 3.2 9.4)"><rect x="2" y="8.5" width="2.4" height=".4"/><rect x="2" y="9.2" width="2.4" height=".4"/><rect x="2" y="9.9" width="2.4" height=".4"/></g><g transform="rotate(-33.7 14.8 9.4)"><rect x="13.6" y="8.5" width="2.4" height=".4"/><rect x="13.6" y="9.2" width="2.4" height=".4"/><rect x="13.6" y="9.9" width="2.4" height=".4"/></g></g></svg>',
    "suisse": '<svg viewBox="0 0 16 16"><rect width="16" height="16" fill="#da291c"/><rect x="6.5" y="3" width="3" height="10" fill="#fff"/><rect x="3" y="6.5" width="10" height="3" fill="#fff"/></svg>',
    "japon": '<svg viewBox="0 0 18 12"><rect width="18" height="12" fill="#fff"/><circle cx="9" cy="6" r="3.6" fill="#bc002d"/></svg>',
}

def words(s): return len(re.findall(r"[\wÀ-ÿ'’%,.-]+", s))

def esc(s): return s  # les fiches contiennent du HTML volontaire (<em>, <b>, <s>)

def scene_html(sc, flag):
    t = sc["type"]; k = sc.get("kick", "")
    out = []
    if k: out.append(f'<div class="kick" data-t="0">{k}</div>')
    if t == "stamp":
        out.append(f'''<div class="pstamp" data-t="150" data-sfx="stamp"><div class="pflag">{flag}</div>
          <div class="pname{" long" if len(sc["country"]) > 9 else ""}">{sc["country"]}</div><div class="pmeta">{("ESCALE N°" + str(sc["num"])) if sc.get("num") else "ENTRÉE"} · {sc["date"]}</div></div>''')
        out.append(f'<div class="hook big" data-t="1100">{sc["hook"]}</div>')
    elif t == "count":
        dec = sc.get("dec", 0)
        long = len(f'{sc["to"]}{sc.get("suffix","")}{sc.get("prefix","")}') > 6
        out.append(f'<div class="huge{" long" if long else ""}" data-t="100" data-sfx="count" data-sfx-dur="{sc.get("countDur",1600)}">{sc.get("prefix","")}<span data-count="{sc["to"]}" data-dec="{dec}" data-dur="{sc.get("countDur",1600)}">0</span><small>{sc.get("suffix","")}</small></div>')
        out.append(f'<div class="unit" data-t="{sc.get("countDur",1600)+150}" data-sfx="impact">{sc["unit"]}</div>')
        if sc.get("hook"): out.append(f'<div class="hook" data-t="{sc.get("countDur",1600)+900}">{sc["hook"]}</div>')
    elif t == "bars":
        out.append(f'<div class="h" data-t="100">{sc["h"]}</div><div class="cmp">')
        for i, r in enumerate(sc["rows"]):
            cls = "row hot" if r.get("hot") else ("row amb" if r.get("amber") else "row")
            out.append(f'<div class="{cls}" data-t="{700+i*600}" data-sfx="{"riser" if i==0 else "blip"}" style="--w:{r["w"]}%"><div class="l">{r["label"]} <b>{r["value"]}</b></div><div class="track"><div class="fill"></div></div></div>')
        out.append('</div>')
        out.append(f'<div class="pct {sc.get("bigColor","red")}" data-t="{700+len(sc["rows"])*600+700}" data-sfx="impact">{sc["big"]}<small>{sc.get("bigSmall","")}</small></div>')
    elif t == "line":
        d = ("M0 32 L10 31 L20 32 L30 29 L40 30 L50 24 L60 25 L70 16 L80 13 L90 7 L100 3" if sc.get("dir","up")=="up"
             else "M0 6 L10 7 L20 5 L30 9 L40 8 L50 14 L60 13 L70 22 L80 26 L90 31 L100 36")
        col = sc.get("color", "red")
        out.append(f'<div class="h" data-t="100">{sc["h"]}</div>')
        out.append(f'<div class="chart {col}" data-t="600" data-sfx="riser" data-sfx-dur="2000"><svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true"><path class="base" d="M0 20 H100"/><path class="l" d="{d}"/></svg></div>')
        out.append(f'<div class="who" data-t="1600">{sc["who"]}</div>')
        out.append(f'<div class="loss {col}" data-t="2500" data-sfx="impact">{sc["big"]}</div>')
    elif t == "big":
        out.append(f'<div class="h" data-t="100">{sc["h"]}</div>')
        if sc.get("visual") == "grid":
            out.append(f'<div class="grid" data-lit="{sc.get("lit",1)}" data-t="500"></div>')
            out.append(f'<div class="mid low" data-t="2200" data-sfx="impact">{sc["mid"]}<small>{sc.get("midSmall","")}</small></div>')
        else:
            out.append(f'<div class="target" data-t="500" data-sfx="sonar"></div>')
            out.append(f'<div class="mid" data-t="1900" data-sfx="impact">{sc["mid"]}<small>{sc.get("midSmall","")}</small></div>')
    elif t == "timeline":
        out.append('<div class="tl">')
        for i, it in enumerate(sc["items"]):
            out.append(f'<div data-t="{it.get("at", 300+i*1300)}" data-sfx="hit"><div class="y">{it["y"]}</div><p>{it["t"]}</p></div>')
        out.append('</div>')
    elif t == "myth":
        out.append(f'<div class="myth" data-t="100">{sc["myth"]}</div>')
        stxt = sc.get("stamp","FAUX")
        out.append(f'<div class="stamp{" long" if len(stxt) > 6 else ""}" data-t="{sc.get("stampAt",1700)}" data-sfx="faux">{stxt}</div>')
    elif t == "end":
        out.append(f'<div class="end" data-t="200" data-sfx="final">{sc["end"]}</div>')
        out.append(f'<div class="next" data-t="{sc.get("nextAt",2600)}" data-sfx="next"><span>PROCHAINE ESCALE</span><b>{sc["next"]}</b><i>{sc.get("nextHint","")}</i></div>')
        out.append(f'<div class="src" data-t="900">{sc["src"]}</div>')
    if sc.get("cap"):
        out.append(f'<div class="cap" data-t="{sc.get("capAt",3000)}">{sc["cap"]}</div>')
    return "\n    ".join(out)

def build(spec_path):
    spec = json.load(open(spec_path, encoding="utf-8"))
    slug = pathlib.Path(spec_path).stem
    flag = FLAGS.get(spec["flag"], "")
    tpl = open(pathlib.Path(__file__).with_name("template.html"), encoding="utf-8").read()
    start = 0; parts = []; timing = []
    for sc in spec["scenes"]:
        dur = sc.get("dur") or int(words(sc["vo"]) / WPS * 1000 + PAD)
        dur = max(dur, sc.get("minDur", 4200))
        parts.append(f'<section class="sc" data-start="{start}" data-dur="{dur}">\n    {scene_html(sc, flag)}\n  </section>')
        timing.append((start, dur, sc["vo"]))
        start += dur
    page = (tpl.replace("{{TITLE}}", spec["title"]).replace("{{TICKER}}", spec["ticker"])
               .replace("{{SCENES}}", "\n  ".join(parts)).replace("{{ARIA}}", html.escape(spec["title"])))
    out = pathlib.Path(spec_path).parent.parent / "build"; out.mkdir(exist_ok=True)
    (out / f"{slug}.html").write_text(page, encoding="utf-8")
    json.dump({"slug": slug, "total": start, "scenes": [{"start": s, "dur": d} for s, d, _ in timing],
               "key": spec.get("key", 0)}, open(out / f"{slug}.timing.json", "w"))
    # script de voix off avec minutage
    lines = [f"# {spec['title']} — script voix off", "",
             f"Durée totale visée : {start/1000:.0f} s · débit ≈ {WPS} mots/s (rythme dynamique de Short).", ""]
    for i, (s, d, vo) in enumerate(timing, 1):
        lines.append(f"**[{s/1000:05.1f} s → {(s+d)/1000:05.1f} s] Scène {i}**  ")
        lines.append(f"{vo}")
        lines.append("")
    vdir = pathlib.Path(spec_path).parent.parent / "scripts-voix"; vdir.mkdir(exist_ok=True)
    (vdir / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")
    el = []
    for sc in spec["scenes"]:
        say = sc.get("say", sc["vo"])
        el.append((f'[{sc["tag"]}] ' if sc.get("tag") else "") + say)
    edir = vdir / "elevenlabs"; edir.mkdir(exist_ok=True)
    (edir / f"{slug}.txt").write_text(" [long pause]\n".join(el) + "\n", encoding="utf-8")
    print(slug, f"{start/1000:.1f}s", [round(d/1000,1) for _, d, _ in timing])

if __name__ == "__main__":
    for p in sys.argv[1:]: build(p)
