# Outils cibles de la veille Data / IA

Cette liste est le périmètre initial de l'application de veille. Elle privilégie les sources primaires. L'application suit en priorité les **versions, correctifs et notes de version** ; la documentation officielle reste une référence, mais n'est pas le flux surveillé. La configuration exploitable se trouve dans [sources_versions.csv](sources_versions.csv).

## Noyau de veille

| Domaine | Outil | Pourquoi le suivre | Source principale |
| --- | --- | --- | --- |
| Manipulation de données | pandas | Base de nombreux notebooks d'analyse et traitements tabulaires | [Documentation](https://pandas.pydata.org/docs/) · [versions](https://github.com/pandas-dev/pandas/releases.atom) |
| Manipulation de données | Polars | Alternative performante à pandas pour des jeux plus volumineux | [Documentation](https://docs.pola.rs/) · [versions](https://github.com/pola-rs/polars/releases.atom) |
| SQL analytique local | DuckDB | Analyse SQL locale et intégration simple avec les fichiers Parquet/CSV | [Documentation](https://duckdb.org/docs/) · [versions](https://github.com/duckdb/duckdb/releases.atom) |
| Transformation de données | dbt Core | Traçabilité, tests et documentation des transformations SQL | [Documentation](https://docs.getdbt.com/) · [versions](https://github.com/dbt-labs/dbt-core/releases.atom) |
| Machine learning | scikit-learn | Modèles classiques, évaluation et clustering, dont le P13 | [Documentation](https://scikit-learn.org/stable/) · [versions](https://github.com/scikit-learn/scikit-learn/releases.atom) |
| Qualité des données | Pandera | Validation de schémas et contrôles de DataFrames | [Documentation](https://pandera.readthedocs.io/) · [versions](https://github.com/unionai-oss/pandera/releases.atom) |
| Qualité des données | Great Expectations | Règles de qualité, validation et documentation des attentes de données | [Documentation](https://docs.greatexpectations.io/) · [versions](https://github.com/great-expectations/great_expectations/releases.atom) |
| Visualisation / restitution | Streamlit | Applications data légères, notamment l'application de veille | [Documentation](https://docs.streamlit.io/) · [versions](https://github.com/streamlit/streamlit/releases.atom) |
| Visualisation / restitution | Plotly | Graphiques interactifs et restitution web | [Documentation](https://plotly.com/python/) · [versions](https://github.com/plotly/plotly.py/releases.atom) |
| IA locale | Ollama | Exécution locale de modèles, confidentialité et expérimentation assistée | [Documentation](https://docs.ollama.com/) · [versions](https://github.com/ollama/ollama/releases.atom) |
| IA locale | llama.cpp | Inférence locale légère et prise en charge de modèles quantifiés | [Documentation](https://github.com/ggml-org/llama.cpp) · [versions](https://github.com/ggml-org/llama.cpp/releases.atom) |
| Transcription locale | faster-whisper | Transcription rapide, réutilisable dans les projets audio | [Dépôt officiel](https://github.com/SYSTRAN/faster-whisper) · [versions](https://github.com/SYSTRAN/faster-whisper/releases.atom) |

## Outils déjà utilisés dans les projets OpenClassrooms

Cette section garantit que la veille couvre aussi la stack réellement pratiquée dans le parcours, et pas uniquement des outils envisagés pour de futurs projets.

| Domaine | Outil | Projets concernés | Source principale |
| --- | --- | --- | --- |
| Langage / environnement | Python | P4, P6, P8, P9, P11, P12, P13 | [Documentation](https://docs.python.org/3/) |
| Notebooks | Jupyter | P4, P6, P9, P11, P12, P13 | [Documentation](https://docs.jupyter.org/) · [versions](https://github.com/jupyter/notebook/releases.atom) |
| Analyse statistique | SciPy | P9, P11, P12 | [Documentation](https://docs.scipy.org/) · [versions](https://github.com/scipy/scipy/releases.atom) |
| Visualisation | Matplotlib | P4, P6, P11, P12 | [Documentation](https://matplotlib.org/stable/) · [versions](https://github.com/matplotlib/matplotlib/releases.atom) |
| Visualisation | Seaborn | P6, P11, P12 | [Documentation](https://seaborn.pydata.org/) · [versions](https://github.com/mwaskom/seaborn/releases.atom) |
| Base de données | SQL / MySQL | P3, P5, P8 | [Documentation MySQL](https://dev.mysql.com/doc/) |
| Business Intelligence | Power BI, Power Query et DAX | P7, P10 | [Documentation Power BI](https://learn.microsoft.com/power-bi/) · [mises à jour officielles](https://powerbi.microsoft.com/blog/) |
| Entrepôt de données | Snowflake | P8 | [Documentation](https://docs.snowflake.com/) · [notes de version](https://docs.snowflake.com/en/release-notes/overview) |

## Outils à suivre à la demande

Ils ne sont ajoutés à l'application que lorsqu'un projet en a besoin ; cela évite une veille inutilement large.

| Domaine | Outil | Déclencheur de suivi |
| --- | --- | --- |
| RAG / recherche sémantique | sentence-transformers, Qdrant | Projet de recherche documentaire ou assistant local sur les livrables |
| Suivi d'expériences ML | MLflow | Entraînements multiples à comparer ou modèle à maintenir |
| Versionnement de données | DVC | Jeux de données ou modèles trop volumineux pour Git |
| Orchestration | Prefect ou Dagster | Pipeline récurrent nécessitant planification, alertes ou dépendances |
| Interprétabilité | SHAP | Modèle prédictif nécessitant une explication détaillée des décisions |

## Modèles IA suivis

Le suivi porte sur les annonces de nouvelles générations, changements d'API, retraits de modèles, licences, tailles/quantifications disponibles et évolutions de capacités. Les modèles ne sont pas comparés automatiquement : l'application crée une entrée à examiner, puis une décision humaine est associée à chaque information utile.

| Famille | Type | Intérêt de veille | Source primaire |
| --- | --- | --- | --- |
| GPT | LLM et multimodal propriétaire | Évolutions de capacités, API, coûts et politiques de disponibilité | [Notes de version OpenAI](https://help.openai.com/en/articles/9624314-model-release-notes) |
| Claude | LLM et multimodal propriétaire | Comparaison de raisonnement, contexte et usages professionnels | [Notes de version Anthropic](https://docs.anthropic.com/en/release-notes/overview) |
| Gemini | LLM et multimodal propriétaire | Évolutions API et capacités multimodales | [Changelog Google AI](https://ai.google.dev/gemini-api/docs/changelog) |
| Llama | LLM open weights | Disponibilité locale, licences et écosystème open source | [Site officiel](https://www.llama.com/) |
| Qwen | LLM open weights | Modèles locaux, multilinguisme et usage déjà présent dans les projets | [Blog Qwen](https://qwenlm.github.io/blog/) |
| Mistral | LLM open weights et API | Alternative européenne, déploiement local ou API | [Changelog Mistral](https://docs.mistral.ai/getting-started/changelog/) |
| DeepSeek | LLM open weights | Nouvelles architectures et possibilités d'inférence locale | [Organisation officielle](https://github.com/deepseek-ai) |
| Gemma | LLM open weights | Modèles légers issus de l'écosystème Google | [Documentation Gemma](https://ai.google.dev/gemma) |
| Phi | Petit modèle de langage | Expérimentations locales à ressources contraintes | [Dépôt Microsoft](https://github.com/microsoft/Phi-3CookBook) |
| Whisper | Transcription automatique | Qualité de transcription et compatibilité des pipelines audio | [Dépôt officiel](https://github.com/openai/whisper) |
| Stable Diffusion | Génération d'images | Évolutions des modèles de vision générative | [Actualités Stability AI](https://stability.ai/news) |
| FLUX | Génération d'images | Alternative de génération d'images et licences associées | [Site Black Forest Labs](https://bfl.ai/) |

## Règles de sélection dans l'application

Un élément de veille est conservé seulement s'il répond au moins à un des critères suivants :

1. corrige une faille de sécurité, un bug bloquant ou une incompatibilité ;
2. améliore la qualité, la reproductibilité ou la maintenabilité d'un projet existant ;
3. apporte une capacité utile à un projet identifié ;
4. modifie une pratique importante (licence, API, compatibilité Python, fin de support) ;
5. mérite un test court avant adoption.

Chaque élément retenu devra contenir : date, source, résumé factuel, outil concerné, projet potentiellement impacté, niveau de priorité et décision humaine (`à tester`, `retenu`, `écarté` ou `à surveiller`).
