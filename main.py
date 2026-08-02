"""
LineagePilot - core pipeline logic, callable with any detected change.

Given a source entity URN and the old/new column names, this:
  1. Finds downstream datasets via DataHub lineage
  2. Reasons about risk for each affected file (Groq)
  3. Generates a corrected version + diff
  4. Opens a GitHub PR (auto-merge if LOW risk, review if HIGH risk)
  5. Writes a migration history record back into DataHub

SETUP REQUIRED (do this once):
    Copy .env.example to .env and fill in GROQ_API_KEY and GITHUB_TOKEN.
    Set REPO_NAME in github_pr.py to your own repo.

Can be run directly for manual testing (uses a default demo scenario), or
imported and called from watcher.py, which triggers it automatically when
it detects a real schema-change event in DataHub.
"""
import time

from lineage_lookup import get_downstream_datasets
from reasoning_engine import classify_change
from diff_generator import generate_fix
from github_pr import open_pr
from write_back import write_migration_history

# Maps a DataHub dataset URN to the local file that represents its code.
# (In a real system this would come from your dbt/Airflow project structure
# via DataHub's own metadata rather than a hardcoded dict; kept simple here
# since this demo only tracks two downstream files.)
URN_TO_FILE = {
    "urn:li:dataset:(urn:li:dataPlatform:postgres,stg_orders_v2,PROD)": "models/stg_orders_v2.sql",
    "urn:li:dataset:(urn:li:dataPlatform:postgres,fct_revenue_v2,PROD)": "models/fct_revenue_v2.sql",
}


def run_pipeline(source_urn: str, old_column: str, new_column: str) -> dict:
    """Runs the full pipeline for one detected schema change. Returns a summary dict."""
    print(f"\n=== LineagePilot: processing change {old_column} -> {new_column} on {source_urn} ===\n")

    print("[1/5] Finding downstream datasets via DataHub lineage...")
    downstream_urns = get_downstream_datasets(source_urn)
    print(f"      Found {len(downstream_urns)} downstream dataset(s).")

    change_id = f"{old_column}_rename_{int(time.time())}"
    affected_entities = []
    generated_prs = []

    for urn in downstream_urns:
        file_path = URN_TO_FILE.get(urn)
        if not file_path:
            print(f"      Skipping {urn} (no local file mapping known for this demo)")
            continue

        print(f"\n[2/5] Reasoning about risk for {file_path}...")
        with open(file_path) as f:
            file_content = f.read()

        classification = classify_change(old_column, new_column, file_path, file_content)
        risk = classification["risk"]
        reasoning = classification["reasoning"]
        print(f"      Risk: {risk} - {reasoning}")

        print(f"[3/5] Generating fix for {file_path}...")
        fix = generate_fix(old_column, new_column, file_path, file_content, risk)
        print(f"      Diff:\n{fix['diff']}")

        print(f"[4/5] Opening GitHub PR for {file_path}...")
        pr_result = open_pr(
            file_path=file_path,
            fixed_content=fix["fixed_content"],
            risk=risk,
            reasoning=reasoning,
            old_column=old_column,
            new_column=new_column,
        )
        print(f"      PR: {pr_result['pr_url']} ({pr_result['status']})")

        affected_entities.append(file_path)
        generated_prs.append({"repo": file_path, "url": pr_result["pr_url"], "status": pr_result["status"]})

    print(f"\n[5/5] Writing migration history back to DataHub...")
    write_migration_history(
        dataset_urn=source_urn,
        change_id=change_id,
        changed_field=f"{old_column} -> {new_column}",
        affected_entities=affected_entities,
        generated_prs=generated_prs,
        validation_status="completed",
        risk_note="See individual PR descriptions for per-file risk reasoning.",
    )

    print("\n=== Done. Check localhost:9002 and your GitHub repo. ===\n")

    return {
        "change_id": change_id,
        "affected_entities": affected_entities,
        "generated_prs": generated_prs,
    }


if __name__ == "__main__":
    # Manual test run using the demo scenario. For automatic, real-time
    # detection instead of this hardcoded example, run watcher.py.
    DEMO_SOURCE_URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,raw_orders_v2,PROD)"
    run_pipeline(DEMO_SOURCE_URN, "user_id", "customer_id")
