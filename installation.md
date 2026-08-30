# Installation — Veille Data & IA

Ce guide installe l'application Streamlit sur Ubuntu ou Windows. Les secrets et réglages d'infrastructure restent dans des fichiers locaux non versionnés.

## Fichiers à transférer

Transférer le code et les fichiers de configuration fonctionnelle :

```text
app.py
src/
requirements.txt
sources_versions.csv
.env.example
outils_cibles.md
architecture_donnees.md
```

Pour reprendre l'historique existant, transférer aussi `data/veille.db` et `data/app_settings.json`.

Ne pas transférer `.venv/`, `.tmp_install/`, `.env` ni `config/`.

---

## Ubuntu — déploiement sur serveur

### 1. Installer Python

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

### 2. Créer le répertoire du projet

Exemple dans `/opt/veille-data-ia` :

```bash
sudo mkdir -p /opt/veille-data-ia
cd /opt/veille-data-ia
```

#### Option : compte système dédié

Par défaut, le guide utilise `www-data`, déjà employé par Nginx sur Ubuntu. Pour isoler davantage l'application, créer le compte dédié avant de déposer les fichiers :

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin streamlit
```

### 3. Déposer les fichiers du projet

Copier le contenu de `envoi_dedie/` dans `/opt/veille-data-ia`.

Après le transfert, appliquer les droits au compte qui exécutera le service :

```bash
sudo chown -R www-data:www-data /opt/veille-data-ia
```

Si un compte `streamlit` dédié est utilisé, remplacer `www-data:www-data` par `streamlit:streamlit`.

### 4. Créer l'environnement Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Créer la configuration locale

```bash
cp .env.example .env
nano .env
```

Renseigner l'accès au serveur Qwen et au SMTP. Ne pas versionner ce fichier.

Exemple de variables à compléter :

```env
QWEN_BASE_URL=http://ADRESSE_PRIVEE_QWEN:PORT/v1
QWEN_API_KEY=cle_locale_qwen
QWEN_MODEL=nom_du_modele

SMTP_HOST=localhost
SMTP_PORT=25
SMTP_FROM="Veille Data & IA <noreply@exemple.fr>"
SMTP_TO="destinataire@exemple.fr"
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_STARTTLS=false
```

### 6. Tester l'application

```bash
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Depuis le serveur, vérifier :

```bash
curl http://127.0.0.1:8501
```

Arrêter ensuite avec `Ctrl+C`.

### 7. Créer le service systemd

Créer `/etc/systemd/system/veille-data-ia.service` :

```ini
[Unit]
Description=Veille Data et IA (Streamlit)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/veille-data-ia
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/veille-data-ia/.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Donner l'accès au dossier au compte du service, puis activer le service :

```bash
sudo chown -R www-data:www-data /opt/veille-data-ia
sudo systemctl daemon-reload
sudo systemctl enable --now veille-data-ia
sudo systemctl status veille-data-ia
```

Logs en direct :

```bash
sudo journalctl -u veille-data-ia -f
```

### 8. Nginx

La configuration Nginx doit transmettre le domaine HTTPS vers `http://127.0.0.1:8501`, avec les en-têtes WebSocket `Upgrade` et `Connection`.

Tester puis recharger après toute modification :

```bash
sudo nginx -t
sudo systemctl reload nginx
```

### 9. Activer la collecte planifiée

Copier les deux fichiers du dossier `deploy/` vers systemd :

```bash
sudo cp deploy/veille-data-ia-collect.service /etc/systemd/system/
sudo cp deploy/veille-data-ia-collect.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now veille-data-ia-collect.timer
systemctl list-timers veille-data-ia-collect.timer
```

Le timer exécute la collecte chaque jour à 08:00 (avec un décalage aléatoire maximal de 10 minutes). La première collecte remplit seulement la base ; les suivantes peuvent pré-classifier les nouvelles entrées et envoyer des alertes si ces options sont activées.

---

## Windows — lancement local

### 1. Installer Python

Installer Python 3.11 ou plus récent depuis python.org, en cochant **Add Python to PATH**.

### 2. Ouvrir PowerShell dans le projet

```powershell
cd D:\chemin\vers\projet_veille
```

### 3. Créer l'environnement et installer les dépendances

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si PowerShell bloque l'activation :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4. Créer `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

Renseigner les paramètres Qwen et SMTP, sans publier ce fichier.

### 5. Démarrer l'application

```powershell
python -m streamlit run app.py
```

Ouvrir ensuite `http://localhost:8501`.

---

## Mise à jour

Après avoir remplacé le code :

```bash
# Ubuntu
cd /opt/veille-data-ia
.venv/bin/pip install -r requirements.txt
sudo systemctl restart veille-data-ia
```

```powershell
# Windows
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m streamlit run app.py
```

La base SQLite et les réglages locaux sont conservés tant que le dossier `data/` n'est pas supprimé.
