# Journal d'amélioration continue — Passeport Éco

Objectif : que chaque épisode accroche dès la 1re seconde et soit regardé jusqu'au bout.

## Série 2 (Japon, Corée du Sud, Suisse) — 27/11/2026
- **Zoom lent** sur chaque scène (+4,5 %) : l'image n'est jamais figée.
- **« Punch »** sur chaque chiffre clé (zoom + flash) synchronisé avec l'impact sonore.
- **Numéro d'escale** sur le tampon d'entrée (N°1, N°2…) : donne envie de « collectionner » les pays.
- **Tampon d'idée reçue libre** : « FAUX », « PAS QUE », « PAS SI VITE »… plus nuancé, donc plus crédible.
- **Comparaison avec la France** dès que possible (dette, salaires) : le public français se projette.
- **Texte ElevenLabs généré automatiquement** (`scripts-voix/elevenlabs/<pays>.txt`) avec balises d'émotion.
- Améliorations appliquées aussi aux épisodes 1 à 3 (re-rendus avec leur voix).

## Série 1 (Norvège, Argentine, Dubaï)
- Tampon de passeport en ouverture + phrase choc dans la 1re seconde.
- Question ouverte au début, réponse scène par scène.
- Changement visuel toutes les 5 à 8 s, barres de progression.
- Silence + tampon « FAUX » sur l'idée reçue.
- Fin « Prochaine escale » + carillon d'aéroport → enchaînement vers l'épisode suivant.

## Pistes pour la suite
- Voix : ElevenLabs v4 ne respecte pas toujours `[long pause]` → je recale à la main (outil `tools/align.py`).
- Tester des accroches encore plus courtes (≤ 8 mots) et mesurer la rétention à 3 s dans YouTube Studio.
- Ajouter une mini-carte du pays dans le tampon d'entrée.
- Varier la musique selon l'ambiance du pays (déjà transposée par épisode).
