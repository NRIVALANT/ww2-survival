# launch_local.py - Lance serveur + client(s) pour un test réseau en local
#
# Usage :
#   python launch_local.py                         # 1 client (Joueur1)
#   python launch_local.py --clients 2             # 2 clients (Joueur1, Joueur2)
#   python launch_local.py --host-name Moi --clients 3
#
# Chaque mode est dans son propre processus → fenêtre séparée.
# Fermer n'importe quelle fenêtre n'arrête pas les autres.
# Ctrl+C dans ce terminal arrête tous les processus.

import subprocess
import sys
import time
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Lance une session locale serveur + N clients"
    )
    parser.add_argument(
        "--clients", type=int, default=1,
        help="Nombre de clients à lancer (défaut: 1)",
    )
    parser.add_argument(
        "--host-name", default="Host",
        help="Nom du joueur hôte (défaut: Host)",
    )
    args = parser.parse_args()

    procs: list[subprocess.Popen] = []

    # ── Serveur ──────────────────────────────────────────────────────────
    print(f"[launch] Démarrage serveur (host: {args.host_name})...")
    srv = subprocess.Popen(
        [sys.executable, "main_server.py", args.host_name],
        cwd=None,   # même répertoire que ce script
    )
    procs.append(srv)

    # Laisser le serveur s'initialiser et binder le port
    time.sleep(1.5)

    # ── Clients ──────────────────────────────────────────────────────────
    for i in range(args.clients):
        name = f"Joueur{i + 1}"
        print(f"[launch] Démarrage client {i + 1} / {args.clients} ({name})...")
        cli = subprocess.Popen(
            [sys.executable, "main_client.py", "127.0.0.1", name],
        )
        procs.append(cli)
        if i < args.clients - 1:
            time.sleep(0.4)   # léger écart pour éviter la saturation du serveur

    total = 1 + args.clients
    print(f"\n[launch] {total} processus actifs.")
    print("[launch] Fermez les fenêtres individuellement, ou Ctrl+C ici pour tout arrêter.\n")

    # ── Attente ──────────────────────────────────────────────────────────
    try:
        for proc in procs:
            proc.wait()
    except KeyboardInterrupt:
        print("\n[launch] Arrêt demandé, fermeture des processus...")
        for proc in procs:
            proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("[launch] Terminé.")


if __name__ == "__main__":
    main()
