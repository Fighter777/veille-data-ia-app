# Veille Data & IA

## Contexte

Application de veille développée dans le cadre du projet P13 OpenClassrooms. Elle centralise les publications et notes de version d'outils Data et IA, puis aide à transformer un flux important en liste de travail priorisée.

## Objectif

Suivre les évolutions d'outils utilisés dans les projets Data/IA, conserver un historique des sources consultées et accélérer le premier tri des nouveautés, sans remplacer la validation humaine.

## Fonctionnalités

- Collecte de flux RSS et Atom configurables depuis l'interface.
- Archivage des sources, articles, décisions et journaux d'actualisation dans SQLite.
- Affichage sécurisé ou brut du HTML fourni par les flux.
- Pré-classification par Qwen local : statut, priorité, projets potentiellement concernés et résumé factuel.
- Traduction à la demande des extraits RSS par Qwen.
- Tri visuel par priorité et ancienneté des articles.
- Paramètres persistants hors base de veille : pré-classification automatique, affichage HTML brut et niveaux d'alerte e-mail.

## Architecture

```text
Flux RSS / Atom → Streamlit → SQLite
                       ├─ Qwen local (analyse et traduction)
                       └─ SMTP local (alertes configurables, à finaliser)
```

L'application Streamlit et les données sont prévues pour être hébergées sur un serveur dédié. Le modèle Qwen reste sur une machine distincte et n'est accessible qu'au travers du réseau privé.

## Technologies

Python, Streamlit, SQLite, feedparser, OpenAI SDK compatible llama.cpp, Qwen, Pandas et Nginx.

## Utilisation

1. Actualiser les flux.
2. Laisser la pré-classification automatique traiter les nouvelles entrées, ou lancer un lot manuel.
3. Consulter la liste de tri selon la priorité, le statut et l'ancienneté.
4. Lire la source originale, puis compléter ou corriger la décision humaine si nécessaire.

## Limites et décisions de conception

- Le contenu affiché dépend de ce que chaque flux RSS/Atom publie ; l'application ne récupère pas les articles complets.
- Les propositions Qwen servent au tri initial. Elles restent traçables et peuvent être corrigées.
- Les sources non-RSS (notes de version ou actualités éditeur) sont référencées, mais ne sont pas encore collectées automatiquement.
- Les secrets, données locales et réglages d'hébergement sont exclus du dépôt Git.

## Perspectives

- Planification quotidienne de la collecte sur le serveur dédié.
- Envoi d'alertes e-mail selon les priorités configurées.
- Ajout progressif de collecteurs fiables pour les pages de notes de version non exposées en RSS.
- Notifications Web Push hors ligne : abonnement navigateur, service worker et envoi serveur selon les priorités sélectionnées.
