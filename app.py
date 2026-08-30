from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from src.collector import fetch_feed
from src.database import (
    PRIORITIES,
    STATUSES,
    add_source,
    complete_run,
    create_run,
    get_active_sources,
    get_ai_analyses,
    get_items,
    get_latest_preclassifications,
    get_preclassification_candidates,
    get_runs,
    get_translation_candidates,
    get_translations,
    initialize_database,
    insert_items,
    mark_source_checked,
    sanitize_existing_summaries,
    save_ai_analysis,
    save_translation,
    sync_sources_from_csv,
    update_evaluation,
)
from src.qwen import analyse_item, is_configured, translate_excerpt
from src.notifications import is_email_configured, mail_notifications_enabled, send_priority_alert
from src.settings import (
    get_auto_preclassify,
    get_render_raw_html,
    get_notification_priorities,
    save_auto_preclassify,
    save_render_raw_html,
    save_notification_priorities,
    get_notification_recipients,
    save_notification_recipients,
)


ROOT = Path(__file__).resolve().parent
SOURCES_CSV = ROOT / "sources_versions.csv"

st.set_page_config(page_title="Veille Data & IA", page_icon="🔎", layout="wide")
initialize_database()
sync_sources_from_csv(SOURCES_CSV)
sanitize_existing_summaries()
if "auto_preclassify" not in st.session_state:
    st.session_state["auto_preclassify"] = get_auto_preclassify()
if "render_raw_html" not in st.session_state:
    st.session_state["render_raw_html"] = get_render_raw_html()
if "notification_priorities" not in st.session_state:
    st.session_state["notification_priorities"] = get_notification_priorities()
if "notification_recipients" not in st.session_state:
    st.session_state["notification_recipients"] = get_notification_recipients()


def persist_auto_preclassify() -> None:
    save_auto_preclassify(st.session_state["auto_preclassify"])


def persist_render_raw_html() -> None:
    save_render_raw_html(st.session_state["render_raw_html"])


def persist_notification_priorities() -> None:
    save_notification_priorities(st.session_state["notification_priorities"])


def persist_notification_recipients() -> None:
    save_notification_recipients(st.session_state["notification_recipients"])


def synchronize() -> dict[str, int]:
    # Les candidats connus avant la collecte ne sont pas retraités par
    # l'automatisation : seuls les éléments qui viennent d'arriver le sont.
    candidates_before = set(get_preclassification_candidates(1000)["id"].tolist())
    first_collection = get_runs().empty
    run_id = create_run()
    counters = {"sources_checked": 0, "items_found": 0, "items_added": 0, "errors": 0, "preclassified": 0}
    for source in get_active_sources(automatic_only=True):
        counters["sources_checked"] += 1
        try:
            items = fetch_feed(source)
            counters["items_found"] += len(items)
            counters["items_added"] += insert_items(source["id"], items)
            mark_source_checked(source["id"])
        except Exception as error:  # une source indisponible ne doit pas interrompre toute la veille
            counters["errors"] += 1
            mark_source_checked(source["id"], str(error))
    complete_run(
        run_id,
        sources_checked=counters["sources_checked"],
        items_found=counters["items_found"],
        items_added=counters["items_added"],
        errors=counters["errors"],
    )
    if st.session_state.get("auto_preclassify", False) and counters["items_added"] and not first_collection:
        candidates_after = get_preclassification_candidates(1000)
        new_items = candidates_after[candidates_after["id"].isin(set(candidates_after["id"]) - candidates_before)]
        counters["preclassified"] = preclassify_items(new_items)
    return counters


def preclassify_items(rows: pd.DataFrame, on_progress=None) -> int:
    """Archive et applique le classement initial proposé par Qwen."""
    completed = 0
    total = len(rows)
    for position, (_, row) in enumerate(rows.iterrows(), start=1):
        item = item_from_row(row)
        if on_progress:
            on_progress(int(item["id"]), "En cours", position - 1, total)
        try:
            model, prompt, response = analyse_item(item)
            result = json.loads(response)
            if result.get("statut_propose") not in {"À lire", "À tester", "À surveiller", "Écarté"}:
                raise ValueError("statut_propose absent ou invalide")
            if result.get("priorite_proposee") not in PRIORITIES:
                raise ValueError("priorite_proposee absente ou invalide")
            save_ai_analysis(int(item["id"]), model=model, prompt=prompt, response=response)
            update_evaluation(
                int(item["id"]),
                status=result["statut_propose"],
                priority=result["priorite_proposee"],
                related_project=" ; ".join(result.get("projets_impactes", [])),
                note="Pré-classification Qwen : " + result.get("resume_factuel", ""),
                decision="",
            )
            alert_item = {**item, "priority": result["priorite_proposee"], "status": result["statut_propose"]}
            if result["priorite_proposee"] in get_notification_priorities():
                send_priority_alert(alert_item, result.get("resume_factuel", ""))
            completed += 1
            status = "Terminé"
        except Exception:
            # Une indisponibilité du LLM ne doit pas empêcher la collecte RSS.
            status = "Erreur"
        if on_progress:
            on_progress(int(item["id"]), status, position, total)
    return completed


def item_from_row(row: pd.Series) -> dict[str, str]:
    return {key: "" if pd.isna(value) else str(value) for key, value in row.to_dict().items()}


def format_datetime_fr(value: object) -> str:
    """Affiche les dates source et les horodatages techniques en heure de Paris."""
    if value is None or pd.isna(value) or str(value).strip() == "":
        return "—"
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return str(value)
    return parsed.tz_convert("Europe/Paris").strftime("%d/%m/%Y à %H:%M")


def relative_age_fr(value: object) -> str:
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return "date non précisée"
    days = max(0, (pd.Timestamp.now(tz="Europe/Paris") - parsed.tz_convert("Europe/Paris")).days)
    if days == 0:
        return "aujourd’hui"
    if days == 1:
        return "il y a 1 jour"
    if days < 7:
        return f"il y a {days} jours"
    if days < 14:
        return "il y a 1 semaine"
    if days < 60:
        return f"il y a {days // 7} semaines"
    months = max(1, days // 30)
    return f"il y a {months} mois"


def priority_badge(priority: str) -> str:
    colors = {"Basse": "#2e7d32", "Moyenne": "#e67e22", "Haute": "#c62828", "Urgente": "#6a1b9a"}
    color = colors.get(priority, "#5f6368")
    return (
        f'<span style="display:inline-block;padding:0.18rem 0.55rem;border-radius:999px;'
        f'background:{color};color:white;font-size:0.82rem;font-weight:600">{escape(priority)}</span>'
    )


def priority_marker(priority: str) -> str:
    return {"Basse": "🟢", "Moyenne": "🟠", "Haute": "🔴", "Urgente": "🟣"}.get(priority, "⚪")


@st.fragment(run_every="20s")
def render_dashboard() -> None:
    """Rafraîchit les indicateurs sans interrompre la lecture des autres onglets."""
    fresh_items = get_items()
    total = len(fresh_items)
    retained = int((fresh_items["status"] == "Retenu").sum()) if total else 0
    to_review = int(fresh_items["status"].isin(["À trier", "À lire", "À tester"]).sum()) if total else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Éléments archivés", total)
    col2.metric("À examiner", to_review)
    col3.metric("Retenus", retained)
    st.subheader("Répartition des décisions")
    if total:
        status_counts = (
            fresh_items["status"]
            .value_counts()
            .reindex(STATUSES, fill_value=0)
            .rename_axis("Statut")
            .reset_index(name="Éléments")
        )
        st.bar_chart(status_counts, x="Statut", y="Éléments", horizontal=True)
        st.subheader("Dernières nouveautés")
        latest = fresh_items[["tool", "title", "published_at", "status", "priority"]].head(10).copy()
        latest["published_at"] = latest["published_at"].map(format_datetime_fr)
        latest.columns = ["Outil", "Élément", "Publication", "Statut", "Priorité"]
        st.dataframe(latest, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun élément encore archivé. Lance une actualisation des flux depuis la barre latérale.")


st.title("🔎 Veille Data & IA")
st.caption("Versions, notes de version et décisions humaines — avec enrichissement Qwen local facultatif.")

with st.sidebar:
    st.header("Actions")
    if st.button("Actualiser les flux", type="primary", use_container_width=True):
        with st.spinner("Récupération des flux Atom/RSS…"):
            result = synchronize()
        message = f"{result['items_added']} nouveauté(s) ajoutée(s) ; {result['errors']} erreur(s)."
        if result["preclassified"]:
            message += f" {result['preclassified']} pré-classification(s) Qwen ajoutée(s)."
        st.success(message)
    latest_runs = get_runs()
    if latest_runs.empty:
        st.caption("Dernière actualisation : aucune")
    else:
        last_run = latest_runs.iloc[0]
        st.caption(f"Dernière actualisation : {format_datetime_fr(last_run['finished_at'] or last_run['started_at'])}")
    st.divider()
    st.write("**Qwen local**")
    st.caption("Disponible" if is_configured() else "Non configuré")
    st.checkbox(
        "Pré-classer automatiquement les nouveaux éléments",
        key="auto_preclassify",
        on_change=persist_auto_preclassify,
        help="À chaque actualisation, Qwen enregistre une proposition pour les seuls nouveaux éléments RSS."
    )
    if mail_notifications_enabled():
        st.multiselect(
            "Priorités à notifier par e-mail",
            PRIORITIES,
            key="notification_priorities",
            on_change=persist_notification_priorities,
            help="Réglage conservé localement, utilisé par le module d'envoi e-mail lors de la pré-classification automatique.",
        )
        st.text_area(
            "Destinataires des alertes e-mail",
            key="notification_recipients",
            on_change=persist_notification_recipients,
            placeholder="prenom.nom@exemple.fr\nautre@exemple.fr",
            help="Une adresse par ligne, ou plusieurs adresses séparées par des virgules.",
        )
        st.caption("E-mail configuré" if is_email_configured() else "E-mail non configuré")
    else:
        st.caption("Notifications e-mail désactivées par la configuration serveur.")
    st.divider()
    render_raw_html = st.checkbox(
        "Afficher le HTML brut des flux",
        key="render_raw_html",
        on_change=persist_render_raw_html,
        help="Désactive le filtrage visuel pour les contenus RSS. À réserver aux flux de confiance.",
    )
    if render_raw_html:
        st.warning("Mode HTML brut actif : les balises fournies par les éditeurs ne sont plus filtrées.")
    st.divider()
    st.caption("Les sources `release_notes` et `provider_news` sont répertoriées, mais ne sont pas encore récupérées automatiquement afin d'éviter un scraping fragile.")

items = get_items()
translations_qwen = get_translations()
tab_dashboard, tab_feed, tab_preclassify, tab_items, tab_sources, tab_history = st.tabs(
    ["Tableau de bord", "Flux RSS", "Pré-classification Qwen", "Trier les éléments", "Sources", "Historique"]
)

with tab_dashboard:
    render_dashboard()

with tab_feed:
    st.subheader("Flux RSS et Atom")
    st.caption("Vue de lecture des contenus publiés par les sources. Le volume et le niveau de détail dépendent du flux fourni par chaque éditeur.")
    if items.empty:
        st.info("Actualise les flux pour afficher les dernières entrées.")
    else:
        show_translation = st.checkbox("Afficher la traduction Qwen lorsqu'elle est disponible", value=True)
        feed_tools = ["Toutes les sources"] + sorted(items["tool"].dropna().unique().tolist())
        feed_tool_filter = st.selectbox("Filtrer le flux", feed_tools, key="feed_tool_filter")
        feed_items = items.copy()
        if feed_tool_filter != "Toutes les sources":
            feed_items = feed_items[feed_items["tool"] == feed_tool_filter]

        for _, row in feed_items.iterrows():
            item = item_from_row(row)
            st.markdown(f"### {item['title']}")
            st.caption(f"{item['tool']} · {format_datetime_fr(item.get('published_at'))}")
            content = item.get("raw_html") if render_raw_html else item.get("raw_summary")
            if content:
                st.markdown(content, unsafe_allow_html=True)
            else:
                st.caption("Cette entrée ne contient pas de résumé dans le flux.")
            translation = translations_qwen.get(int(item["id"]))
            if show_translation and translation:
                st.markdown("**Traduction Qwen de l’extrait**")
                st.write(translation)
            st.markdown(f"[Ouvrir la publication source]({item['url']})")
            st.divider()

with tab_preclassify:
    st.subheader("Pré-classification Qwen")
    st.caption("Qwen classe automatiquement les nouveaux éléments : statut, priorité et projets concernés restent modifiables ensuite dans la vue de tri.")
    if not is_configured():
        st.warning("Qwen local n'est pas configuré.")
    else:
        batch_in_progress = bool(st.session_state.get("preclassification_in_progress", False))
        batch_size = st.slider(
            "Nombre d'éléments à proposer",
            min_value=1,
            max_value=50,
            value=10,
            disabled=batch_in_progress,
        )
        candidates = get_preclassification_candidates(batch_size)
        if batch_in_progress:
            batch_rows = st.session_state.get("preclassification_batch", [])
            batch_statuses = st.session_state.get("preclassification_statuses", {})
            status_placeholder = st.empty()
            progress = st.progress(0, text="Pré-classification Qwen en préparation…")

            def render_batch() -> None:
                display = pd.DataFrame(batch_rows)[["id", "tool", "title"]].copy()
                display["statut Qwen"] = display["id"].astype(str).map(batch_statuses)
                status_placeholder.dataframe(display[["tool", "title", "statut Qwen"]], use_container_width=True, hide_index=True)

            def refresh_status(item_id: int, status: str, done: int, total: int) -> None:
                batch_statuses[str(item_id)] = status
                st.session_state["preclassification_statuses"] = batch_statuses
                render_batch()
                progress.progress(done / total, text=f"Pré-classification Qwen : {done}/{total}")

            render_batch()
            completed = preclassify_items(pd.DataFrame(batch_rows), on_progress=refresh_status)
            progress.empty()
            st.session_state["preclassification_in_progress"] = False
            st.session_state["preclassification_last_count"] = completed
            st.rerun()
        elif st.session_state.get("preclassification_batch"):
            batch_rows = st.session_state["preclassification_batch"]
            batch_statuses = st.session_state.get("preclassification_statuses", {})
            st.success(f"Pré-classification terminée : {st.session_state.get('preclassification_last_count', 0)}/{len(batch_rows)} proposition(s) enregistrée(s).")
            display = pd.DataFrame(batch_rows)[["tool", "title", "id"]].copy()
            display["statut Qwen"] = display["id"].astype(str).map(batch_statuses)
            st.dataframe(display[["tool", "title", "statut Qwen"]], use_container_width=True, hide_index=True)
        if candidates.empty and not batch_in_progress:
            st.info("Aucun élément « À trier » sans proposition Qwen.")
        elif not batch_in_progress and st.button("Pré-classer les éléments non traités", type="primary"):
            batch_rows = candidates.to_dict("records")
            st.session_state["preclassification_batch"] = batch_rows
            st.session_state["preclassification_statuses"] = {str(row["id"]): "En attente" for row in batch_rows}
            st.session_state["preclassification_last_count"] = 0
            st.session_state["preclassification_in_progress"] = True
            st.rerun()

        st.divider()
        st.subheader("Compléter les traductions RSS")
        st.caption("Coche les extraits à traduire. La traduction est indépendante du classement Qwen déjà enregistré.")
        translation_size = st.slider("Nombre d'extraits à afficher", min_value=1, max_value=50, value=10, key="translation_batch_size", disabled=batch_in_progress)
        translation_candidates = get_translation_candidates(translation_size)
        if translation_candidates.empty:
            st.success("Tous les éléments possèdent une traduction Qwen.")
        else:
            translation_display = translation_candidates[["id", "tool", "title", "published_at"]].copy()
            translation_display.insert(0, "Traduire", False)
            translation_display["published_at"] = translation_display["published_at"].map(format_datetime_fr)
            translation_display.columns = ["Traduire", "ID", "Outil", "Élément", "Publication"]
            selector_version = st.session_state.get("translation_selector_version", 0)
            selected_display = st.data_editor(
                translation_display,
                hide_index=True,
                use_container_width=True,
                disabled=["ID", "Outil", "Élément", "Publication"],
                column_config={"Traduire": st.column_config.CheckboxColumn("Traduire")},
                key=f"translation_selector_{selector_version}",
            )
            selected_ids = selected_display.loc[selected_display["Traduire"], "ID"].tolist()
            selected_translations = translation_candidates[translation_candidates["id"].isin(selected_ids)]
            st.caption(f"{len(selected_translations)} extrait(s) sélectionné(s).")
        if not translation_candidates.empty and not batch_in_progress and st.button(
            f"Traduire les {len(selected_translations)} extrait(s) sélectionné(s)",
            disabled=not selected_ids,
        ):
            completed = 0
            with st.spinner("Traduction des extraits par Qwen…"):
                for _, row in selected_translations.iterrows():
                    try:
                        item = item_from_row(row)
                        model, translation = translate_excerpt(item)
                        save_translation(int(item["id"]), model=model, translation=translation)
                        completed += 1
                    except Exception:
                        continue
            st.success(f"{completed} traduction(s) enregistrée(s).")
            st.session_state["translation_selector_version"] = st.session_state.get("translation_selector_version", 0) + 1
            st.rerun()

    proposals = get_latest_preclassifications()
    priority_order = {"Urgente": 0, "Haute": 1, "Moyenne": 2, "Basse": 3}
    parsed_proposals = []
    for proposal in proposals:
        try:
            result = json.loads(proposal["response"])
        except json.JSONDecodeError:
            continue
        if "statut_propose" not in result:
            continue
        parsed_proposals.append((proposal, result))
    parsed_proposals.sort(key=lambda entry: priority_order.get(entry[1].get("priorite_proposee"), 3))
    st.subheader(f"Pré-classifications enregistrées ({len(parsed_proposals)} / {len(items)})")
    if parsed_proposals:
        overview = pd.DataFrame(
            [
                {
                    "Priorité": result.get("priorite_proposee", "Non renseignée"),
                    "Statut": result.get("statut_propose", "Non renseigné"),
                    "Outil": proposal["tool"],
                    "Élément": proposal["title"],
                    "Résumé Qwen": result.get("resume_factuel", ""),
                    "À vérifier": result.get("verification_humaine", ""),
                }
                for proposal, result in parsed_proposals
            ]
        )
        st.dataframe(overview, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune pré-classification Qwen enregistrée pour le moment.")

with tab_items:
    st.subheader("Trier et documenter les éléments")
    if items.empty:
        st.info("Actualise les flux pour remplir cette vue.")
    else:
        tools = ["Tous"] + sorted(items["tool"].dropna().unique().tolist())
        statuses = ["Tous"] + list(STATUSES)
        col1, col2 = st.columns(2)
        tool_filter = col1.selectbox("Outil / modèle", tools)
        status_filter = col2.selectbox("Statut", statuses)
        classification_filter = st.selectbox("Pré-classification", ("Toutes", "Pré-classifiées par Qwen", "À pré-classer"))
        filtered = items.copy()
        if tool_filter != "Tous":
            filtered = filtered[filtered["tool"] == tool_filter]
        if status_filter != "Tous":
            filtered = filtered[filtered["status"] == status_filter]
        if classification_filter == "Pré-classifiées par Qwen":
            filtered = filtered[filtered["qwen_preclassified"] == 1]
        elif classification_filter == "À pré-classer":
            filtered = filtered[filtered["qwen_preclassified"] == 0]

        st.caption(f"{len(filtered)} élément(s) affiché(s)")
        for _, row in filtered.iterrows():
            item = item_from_row(row)
            if item.get("qwen_preclassified") == "1":
                classification_label = f"{priority_marker(item['priority'])} {item['priority']}"
            else:
                classification_label = "⚪ À pré-classer"
            label = f"{classification_label} · {relative_age_fr(item.get('published_at'))} · {item['status']} · [{item['tool']}] {item['title']}"
            with st.expander(label):
                detail_priority = priority_badge(item["priority"]) if item.get("qwen_preclassified") == "1" else "⚪ À pré-classer"
                st.markdown(
                    f"{detail_priority} &nbsp; "
                    f"**Publié le {format_datetime_fr(item.get('published_at'))}** — {relative_age_fr(item.get('published_at'))}",
                    unsafe_allow_html=True,
                )
                if item.get("note"):
                    st.info(item["note"])
                if item.get("related_project"):
                    st.caption(f"Projets concernés : {item['related_project']}")
                st.link_button("Lire l’article original", item["url"], type="primary")
                content = item.get("raw_html") if render_raw_html else item.get("raw_summary")
                if content:
                    st.caption("Extrait fourni par le flux : il aide au tri, mais ne remplace pas la lecture de la source.")
                    st.markdown(content, unsafe_allow_html=True)
                if item.get("published_at"):
                    st.caption(
                        f"Publié : {format_datetime_fr(item['published_at'])} · "
                        f"Récupéré : {format_datetime_fr(item['fetched_at'])}"
                    )

                with st.form(f"evaluation_{item['id']}"):
                    left, right = st.columns(2)
                    status = left.selectbox("Statut", STATUSES, index=STATUSES.index(item["status"]), key=f"status_{item['id']}")
                    priority = right.selectbox("Priorité", PRIORITIES, index=PRIORITIES.index(item["priority"]), key=f"priority_{item['id']}")
                    related_project = st.text_input("Projet impacté", value=item.get("related_project", ""), key=f"project_{item['id']}")
                    note = st.text_area("Note", value=item.get("note", ""), key=f"note_{item['id']}")
                    decision = st.text_area("Décision / suite", value=item.get("decision", ""), key=f"decision_{item['id']}")
                    if st.form_submit_button("Enregistrer la décision"):
                        update_evaluation(int(item["id"]), status=status, priority=priority, related_project=related_project, note=note, decision=decision)
                        st.success("Décision enregistrée.")
                        st.rerun()


with tab_sources:
    st.subheader("Sources actives")
    with st.expander("Ajouter une source", expanded=False):
        st.caption("Choisis RSS ou Atom GitHub pour l'inclure dans le bouton « Actualiser les flux ». Les autres types restent dans le catalogue pour consultation manuelle.")
        with st.form("add_source"):
            source_name = st.text_input("Nom de la source / de l'outil *", placeholder="Ex. Hugging Face")
            source_url = st.text_input("URL *", placeholder="https://…")
            left, right = st.columns(2)
            source_category = left.text_input("Catégorie", value="IA générative")
            source_type = right.selectbox(
                "Type",
                ("rss", "atom_github", "release_notes", "provider_news"),
                format_func=lambda value: {
                    "rss": "RSS (collecte automatique)",
                    "atom_github": "Atom GitHub (collecte automatique)",
                    "release_notes": "Notes de version (consultation manuelle)",
                    "provider_news": "Actualités éditeur (consultation manuelle)",
                }[value],
            )
            source_frequency = left.text_input("Fréquence de vérification", value="hebdomadaire")
            source_projects = right.text_input("Projets concernés", placeholder="P13 ; portfolio")
            source_active = st.checkbox("Source active", value=True)
            if st.form_submit_button("Enregistrer la source", type="primary"):
                try:
                    add_source(
                        tool=source_name,
                        category=source_category,
                        source_type=source_type,
                        url=source_url,
                        frequency=source_frequency,
                        related_projects=source_projects,
                        active=source_active,
                    )
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success("Source enregistrée.")
                    st.rerun()

    sources = pd.DataFrame(get_active_sources())
    if not sources.empty:
        source_display = sources[["tool", "category", "source_type", "frequency", "related_projects", "last_checked_at", "last_error", "url"]].copy()
        source_display["last_checked_at"] = source_display["last_checked_at"].map(format_datetime_fr)
        source_display["last_error"] = source_display["last_error"].fillna("—")
        source_display.columns = [
            "Outil", "Catégorie", "Type", "Fréquence", "Projets concernés",
            "Dernière vérification", "Dernière erreur", "Source",
        ]
        st.dataframe(
            source_display,
            use_container_width=True,
            hide_index=True,
            column_config={"Source": st.column_config.LinkColumn("Source")},
        )
    st.info("Les flux Atom/RSS sont collectés automatiquement. Les notes de version et actualités de fournisseurs sont conservées comme sources à consulter, en attendant un collecteur adapté et robuste.")

with tab_history:
    st.subheader("Journal des actualisations")
    runs = get_runs()
    if runs.empty:
        st.info("Aucune actualisation enregistrée.")
    else:
        history = runs.copy()
        history["started_at"] = history["started_at"].map(format_datetime_fr)
        history["finished_at"] = history["finished_at"].map(format_datetime_fr)
        history.columns = [
            "N°", "Début", "Fin", "Sources vérifiées", "Éléments trouvés",
            "Nouveaux éléments", "Erreurs",
        ]
        st.dataframe(history, use_container_width=True, hide_index=True)
