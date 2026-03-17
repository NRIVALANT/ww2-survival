#!/bin/bash
# deploy/setup.sh — Configuration initiale du Droplet DigitalOcean
# Usage : bash setup.sh <GIT_REPO_URL>
#   ex  : bash setup.sh https://github.com/ton-compte/ww2-survival.git
#
# À exécuter UNE seule fois après la création du Droplet (Ubuntu 22.04).
set -e

REPO_URL="${1:?Usage: bash setup.sh <git_repo_url>}"
APP_DIR="/opt/ww2survival"
SERVICE="ww2survival"
PYTHON="python3.11"

# ── 1. Paquets système ────────────────────────────────────────────────────────
echo "==> Installation des dépendances système …"
apt-get update -qq
apt-get install -y -qq \
    git \
    python3.11 python3.11-venv python3.11-dev \
    libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    libfreetype6-dev libportmidi-dev \
    ufw

# ── 2. Firewall ───────────────────────────────────────────────────────────────
echo "==> Configuration du firewall …"
ufw allow OpenSSH
ufw allow 8765/tcp    # WebSocket WW2 Survival
ufw --force enable

# ── 3. Cloner le dépôt ───────────────────────────────────────────────────────
echo "==> Clonage du dépôt …"
if [ -d "$APP_DIR" ]; then
    echo "    Dossier existant — git pull"
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

# ── 4. Environnement virtuel + dépendances ───────────────────────────────────
echo "==> Création du venv …"
cd "$APP_DIR"
$PYTHON -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

# ── 5. Service systemd ───────────────────────────────────────────────────────
echo "==> Installation du service systemd …"
cp deploy/ww2survival.service /etc/systemd/system/${SERVICE}.service
systemctl daemon-reload
systemctl enable $SERVICE
systemctl restart $SERVICE

echo ""
echo "✓ Serveur déployé et démarré."
echo "  Statut  : systemctl status $SERVICE"
echo "  Logs    : journalctl -u $SERVICE -f"
echo "  Port    : 8765 (WebSocket)"
