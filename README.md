# Projet de veille automatisée

Application Streamlit de veille technologique et méthodologique, conçue dans le cadre du P13.

La présentation synthétique du projet est disponible dans [fiche_projet.md](fiche_projet.md).

Objectif : récupérer des sources sélectionnées, conserver un historique daté et aider à trier les éléments utiles à la pratique data/IA.

Le périmètre initial est défini dans [outils_cibles.md](outils_cibles.md). La configuration exploitable par l'application est dans [sources_versions.csv](sources_versions.csv) : les versions et notes de version sont suivies en priorité, via flux Atom GitHub, RSS ou pages officielles.

La stratégie de sauvegarde est décrite dans [architecture_donnees.md](architecture_donnees.md) : historique, décisions humaines et journaux d'actualisation seront conservés dans SQLite.

Le déploiement local, Windows et Ubuntu est détaillé dans [installation.md](installation.md).

## Lancer l'application

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

L'application collecte les flux Atom/RSS, archive les éléments dans `data/veille.db` et permet de les qualifier manuellement. Pour activer l'enrichissement par une IA locale compatible OpenAI, copier `.env.example` en `.env`, renseigner une clé non publiée puis relancer l'application.

Les alertes e-mail comportent deux circuits indépendants : les destinataires et priorités utilisateur sont configurables depuis l’interface ; ceux de l’administration ne sont accessibles qu’après déverrouillage de l’onglet Administration avec `ADMIN_PASSWORD`. Un même élément peut donc suivre l’un, l’autre, les deux circuits ou aucun.

Les données SQLite et les secrets sont ignorés par Git.
