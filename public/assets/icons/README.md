# Aeryndor Defense – Asset & Icon Struktur

Aktuell nutzt das Spiel eingebaute, detaillierte **Metin2-orientierte RPG/Pixel-Art Vektor-Icons & Sprites** (`src/systems/iconRenderer.js`), sodass alle Waffen (z.B. Mondsplitterklinge / VMS, Rotstahlbrecher / REK, Seuchenzahn, Sternenreißer), Rüstungen, Schmuckstücke, Truhen, Bonuswandler, Fertigkeitsbücher, Helden, Türme und Rissmonolithen sofort im Spiel sichtbar sind.

## Eigene Icons später einfügen
Du kannst jederzeit eigene Bilddateien (`.png`, `.webp` oder `.svg`) in folgende Unterordner legen:
- `assets/icons/items/<itemId>.png` (z.B. `msk.png`, `rsb.png`, `seuchenzahn.png`, `sternenreisser.png`, `bonuswandler.png`)
- `assets/icons/skills/<skillId>.png`
- `assets/icons/heroes/<heroId>.png`
- `assets/icons/towers/<towerId>.png`
- `assets/icons/monsters/<monsterId>.png`

Wenn in `src/data/items.js` (bzw. `heroes.js`, `towers.js`) das Feld `customIcon` gesetzt ist oder eine Datei unter `assets/icons/...` hinterlegt wird, lädt der `IconRenderer` automatisch deine Bilddatei statt des integrierten Icons.
