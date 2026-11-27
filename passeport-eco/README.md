# Passeport Éco

Fabrique des Shorts « Passeport Éco » : un pays, ses chiffres clés, en ~50 s, au format vertical 1080×1920.

- `specs/<pays>.json` : la fiche d'un épisode (texte à l'écran, voix off, sources).
- `template.html` + `builder.py` : génèrent la page animée de l'épisode.
- `tools/render.sh <pays> [voix]` : rendu complet en MP4 (`videos/<pays>.mp4`), musique et effets inclus.
- `tools/retime.py <pays> <voix>` : recale les scènes sur une voix off enregistrée (1 s de pause entre les scènes).
- `scripts-voix/SCRIPTS-VOIX.md` : les textes à enregistrer.

Avec la voix : `python3 tools/retime.py norvege voix.m4a && tools/render.sh norvege build/norvege.voice.wav`
