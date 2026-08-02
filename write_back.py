"""
Writes a migration history record back into DataHub, attached to the
dataset entity that changed, using the same emitter pattern as seed_datahub.py.

Run standalone to test:
    py -3.11 write_back.py
"""
import json
import time
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import DatasetPropertiesClass

GMS_URL = "http://localhost:8080"


def write_migration_history(dataset_urn: str, change_id: str, changed_field: str,
                             affected_entities: list[str], generated_prs: list[dict],
                             validation_status: str, risk_note: str) -> None:
    """Attaches a migrationHistory record to the dataset's customProperties."""
    record = {
        "changeId": change_id,
        "changedField": changed_field,
        "affectedEntities": affected_entities,
        "generatedPRs": generated_prs,
        "validationStatus": validation_status,
        "riskNote": risk_note,
    }

    emitter = DatahubRestEmitter(gms_server=GMS_URL, disable_ssl_verification=True)

    properties = DatasetPropertiesClass(
        customProperties={"migrationHistory": json.dumps(record)}
    )

    mcp = MetadataChangeProposalWrapper(
        entityUrn=dataset_urn,
        aspect=properties,
    )
    emitter.emit_mcp(mcp)
    emitter.flush()
    print(f"Migration history written to {dataset_urn}")


if __name__ == "__main__":
    write_migration_history(
        dataset_urn="urn:li:dataset:(urn:li:dataPlatform:postgres,raw_orders_v2,PROD)",
        change_id=f"user_id_rename_{int(time.time())}",
        changed_field="user_id -> customer_id",
        affected_entities=["stg_orders_v2", "fct_revenue_v2"],
        generated_prs=[{"repo": "test", "status": "test"}],
        validation_status="test run",
        risk_note="Standalone test of write_back.py",
    )
