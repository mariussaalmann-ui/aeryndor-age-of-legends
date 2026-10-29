# Zusammenarbeit an Aeryndor – Age of Legends

## Überblick

| Branch    | Zweck                           | Server                                       |
|-----------|---------------------------------|----------------------------------------------|
| `main`    | Live-Spiel                      | `207.180.239.190:8090` (`/opt/aeryndor`)          |
| `develop` | Testen / gemeinsame Entwicklung | `207.180.239.190:8091` (`/opt/aeryndor-staging`)  |
| `feature/*` | eigene Arbeitszweige          | –                                            |

Jeder Push auf `develop` bzw. `main` wird per GitHub Actions automatisch auf den passenden Server deployt
(`.github/workflows/deploy.yml` -> `tools/deploy.sh`). Jeder Push/PR wird zusätzlich syntaxgeprüft (`ci.yml`).

## Einrichtung (einmalig, Windows)

```powershell
winget install Git.Git
winget install Python.Python.3.12
winget install OpenJS.NodeJS.LTS
git config --global user.name  "Dein Name"
git config --global user.email "deine@mail.de"
git clone git@github.com:mariussaalmann-ui/aeryndor-age-of-legends.git "D:\Aeryndor Age of Legends"
```

Große Dateien (`aeryndor_data.pak`, `runtimes/`) sind **nicht** in Git – sie werden separat geteilt.

## Lokal starten

```powershell
cd "D:\Aeryndor Age of Legends\server"
py -3 server.py          # lokaler Server auf http://localhost:8090 (eigene lokale DB in data/)
```

## Täglicher Ablauf

```powershell
git checkout develop
git pull
git checkout -b feature/mein-thema
# ... arbeiten ...
git add -A
git commit -m "Kurze Beschreibung"
git push -u origin feature/mein-thema
```

Dann auf GitHub einen **Pull Request nach `develop`** öffnen -> testen auf Port 8091 ->
wenn alles passt: Pull Request `develop` -> `main` (= Live).

## Regeln

- Niemals direkt auf dem Server Dateien bearbeiten – nur über Git.
- Keine Datenbanken, Tokens oder Passwörter committen (`.gitignore` regelt das).
- Vor größeren Änderungen kurz absprechen, wer an welcher Datei arbeitet (v. a. `public/src/ui/app.js`).
