#!/usr/bin/env bash
# Legt einen Entwickler mit vollem Server-Zugriff (sudo) an.
# Nutzung: bash tools/add_developer.sh <linux-user> "<ssh-public-key>"
set -euo pipefail
U="$1"; KEY="$2"
id "$U" &>/dev/null || adduser --disabled-password --gecos "" "$U"
usermod -aG sudo "$U"
echo "$U ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-$U && chmod 440 /etc/sudoers.d/90-$U
install -d -m 700 -o "$U" -g "$U" /home/$U/.ssh
echo "$KEY" >> /home/$U/.ssh/authorized_keys
chown "$U:$U" /home/$U/.ssh/authorized_keys && chmod 600 /home/$U/.ssh/authorized_keys
groupadd -f aeryndor-dev && usermod -aG aeryndor-dev "$U"
chgrp -R aeryndor-dev /opt/aeryndor /opt/aeryndor-staging && chmod -R g+rwX /opt/aeryndor /opt/aeryndor-staging
git config --system --add safe.directory /opt/aeryndor
git config --system --add safe.directory /opt/aeryndor-staging
echo "OK: ssh $U@$(hostname -I | awk '{print $1}')  (sudo ohne Passwort)"
