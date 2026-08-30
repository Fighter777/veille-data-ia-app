# Architecture de sauvegarde — projet de veille

## Décision

L'application utilisera une base **SQLite** locale. Elle permet de conserver l'historique sans dépendance à un service externe et reste adaptée au volume attendu d'une veille personnelle.

La base sera placée dans `data/veille.db` et ignorée par Git. Les fichiers versionnés restent : configuration des sources, code, schéma de base et éventuelles données de démonstration anonymes.

## Données à conserver

| Table | Rôle | Exemples de champs |
| --- | --- | --- |
| `sources` | Configuration et suivi des sources | outil/modèle, catégorie, URL, type de flux, fréquence, actif, dernière récupération |
| `items` | Élément récupéré par la veille | source, titre, URL, date de publication, date de récupération, version détectée, résumé brut, empreinte anti-doublon |
| `evaluations` | Décision humaine sur un élément | statut, priorité, projet impacté, note personnelle, décision, date de décision |
| `runs` | Traçabilité des actualisations | date/heure, nombre de sources consultées, éléments récupérés, erreurs éventuelles |

## Statuts de tri

`à trier` → `à lire` → `à tester` → `retenu` / `écarté` / `à surveiller`

Un élément ne devient pas « retenu » automatiquement : l'application enregistre une proposition issue de la source, puis une validation humaine.

## Règles de fonctionnement

1. Lors d'une actualisation, l'application interroge les sources actives de `sources_versions.csv`.
2. Chaque élément est dédoublonné par source et URL, ou par une empreinte stable si l'URL manque.
3. Les nouveautés sont insérées avec le statut `à trier`.
4. Le tri, les commentaires et les décisions sont écrits dans `evaluations` sans modifier l'élément source.
5. Chaque actualisation est inscrite dans `runs`, y compris en cas d'erreur de flux.

## Hébergement et persistance

| Contexte | Solution |
| --- | --- |
| Local | Fichier `data/veille.db` dans le dossier du projet |
| Serveur dédié | Conteneur Docker avec volume persistant monté sur `/app/data` |
| Streamlit Community Cloud | Ne pas compter sur le disque local pour l'historique : utiliser une base externe ou publier l'application en lecture seule |

Le serveur dédié est donc l'option la plus adaptée si l'objectif est de conserver durablement l'historique et d'exécuter une récupération planifiée.
