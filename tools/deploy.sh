#!/usr/bin/env bash
# Aeryndor Deploy-Skript
#   Live    : bash tools/deploy.sh            (Verzeichnis /opt/aeryndor, Branch main)
#   Staging : bash tools/deploy.sh staging    (Verzeichnis /opt/aeryndor-staging, Branch develop)
# Ablauf: git pull -> Syntax-Check -> DB-Backup -> Dienste neu starten -> Health-Check
set -euo pipefail

TARGET="${1:-live}"
if [[ "$TARGET" == "staging" ]]; then
  APP_DIR="/opt/aeryndor-staging"; BRANCH="develop"; PORT=8091
  SERVICES=("aeryndor-staging.service")
else
  APP_DIR="/opt/aeryndor"; BRANCH="main"; PORT=8090
  SERVICES=("aeryndor.service" "aeryndor-bots.service")
fi

cd "$APP_DIR"
echo "==> [$TARGET] $APP_DIR @ $BRANCH"

OLD_REV="$(git rev-parse HEAD)"
git fetch --quiet origin "$BRANCH"
git reset --hard "origin/$BRANCH"
NEW_REV="$(git rev-parse HEAD)"
echo "==> $OLD_REV -> $NEW_REV"

echo "==> Syntax-Check"
if ! python3 -m py_compile server/*.py; then
  echo "!! Python-Syntaxfehler – Rollback auf $OLD_REV"
  git reset --hard "$OLD_REV"; exit 1
fi
if command -v node >/dev/null 2>&1; then
  node --check public/src/ui/app.js || { echo "!! JS-Syntaxfehler – Rollback"; git reset --hard "$OLD_REV"; exit 1; }
fi

if [[ -f data/aeryndor_mmo.db ]]; then
  STAMP="$(date +%Y%m%d_%H%M%S)"
  mkdir -p backups_deploy/db
  sqlite3 data/aeryndor_mmo.db ".backup backups_deploy/db/aeryndor_mmo_${STAMP}.db" 2>/dev/null \
    || cp data/aeryndor_mmo.db "backups_deploy/db/aeryndor_mmo_${STAMP}.db"
  ls -1t backups_deploy/db/*.db | tail -n +21 | xargs -r rm -f   # nur die letzten 20 behalten
  echo "==> DB-Backup: backups_deploy/db/aeryndor_mmo_${STAMP}.db"
fi

echo "==> Neustart: ${SERVICES[*]}"
systemctl restart "${SERVICES[@]}"
sleep 4
for s in "${SERVICES[@]}"; do echo "    $s: $(systemctl is-active "$s")"; done

if curl -fsS -o /dev/null "http://127.0.0.1:${PORT}/api/config"; then
  echo "==> OK – /api/config antwortet auf Port ${PORT}"
else
  echo "!! Health-Check fehlgeschlagen auf Port ${PORT}"; exit 1
fi
