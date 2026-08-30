"""Collecte autonome, prévue pour un timer systemd."""

from pathlib import Path
import json

from src.collector import fetch_feed
from src.database import (
    PRIORITIES, STATUSES, complete_run, create_run, get_active_sources,
    get_preclassification_candidates, get_runs, insert_items, mark_source_checked,
    save_ai_analysis, sync_sources_from_csv, update_evaluation,
)
from src.notifications import send_priority_alert
from src.qwen import analyse_item, is_configured
from src.settings import get_auto_preclassify, get_notification_priorities


ROOT = Path(__file__).resolve().parent


def main() -> None:
    sync_sources_from_csv(ROOT / "sources_versions.csv")
    before = set(get_preclassification_candidates(1000)["id"].tolist())
    first_collection = get_runs().empty
    run_id = create_run()
    counters = {"sources_checked": 0, "items_found": 0, "items_added": 0, "errors": 0}
    for source in get_active_sources(automatic_only=True):
        counters["sources_checked"] += 1
        try:
            entries = fetch_feed(source)
            counters["items_found"] += len(entries)
            counters["items_added"] += insert_items(source["id"], entries)
            mark_source_checked(source["id"])
        except Exception as error:
            counters["errors"] += 1
            mark_source_checked(source["id"], str(error))
    complete_run(run_id, **counters)

    preclassified = 0
    if get_auto_preclassify() and is_configured() and counters["items_added"] and not first_collection:
        pending = get_preclassification_candidates(1000)
        new_items = pending[pending["id"].isin(set(pending["id"]) - before)]
        for _, row in new_items.iterrows():
            item = {key: "" if value is None else str(value) for key, value in row.to_dict().items()}
            try:
                model, prompt, response = analyse_item(item)
                result = json.loads(response)
                if result.get("statut_propose") not in STATUSES or result.get("priorite_proposee") not in PRIORITIES:
                    raise ValueError("Réponse Qwen incomplète")
                save_ai_analysis(int(item["id"]), model=model, prompt=prompt, response=response)
                update_evaluation(int(item["id"]), status=result["statut_propose"], priority=result["priorite_proposee"], related_project=" ; ".join(result.get("projets_impactes", [])), note="Pré-classification Qwen : " + result.get("resume_factuel", ""), decision="")
                if result["priorite_proposee"] in get_notification_priorities():
                    send_priority_alert({**item, "priority": result["priorite_proposee"], "status": result["statut_propose"]}, result.get("resume_factuel", ""))
                preclassified += 1
            except Exception as error:
                print(f"Pré-classification impossible pour {item['id']}: {error}")
    print({**counters, "preclassified": preclassified})


if __name__ == "__main__":
    main()
