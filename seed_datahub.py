"""Seed a local DataHub instance with three tables and column-level lineage.

Run with:
    py -3.11 seed_datahub.py
"""

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    AuditStampClass,
    DatasetPropertiesClass,
    FineGrainedLineageClass,
    NumberTypeClass,
    OwnershipClass,
    OwnerClass,
    SchemaFieldClass,
    SchemaFieldDataTypeClass,
    SchemaMetadataClass,
    StringTypeClass,
    UpstreamClass,
    UpstreamLineageClass,
)
from datahub.metadata.urns import DatasetUrn, SchemaFieldUrn

# Configuration
GMS_URL = "http://localhost:8080"
PLATFORM = "postgres"
ENV = "PROD"

DATAHUB_USER_URN = "urn:li:corpuser:datahub"

TABLES = ["raw_orders_v2", "stg_orders_v2", "fct_revenue_v2"]

# CLEAN BASELINE - this is the starting state. To trigger a demo change,
# edit ONE column name below (e.g. "order_total" -> "order_sum"), save,
# and re-run this script while watcher.py is running in another terminal.
COLUMNS = {
    "raw_orders_v2": [
        ("user_id", True),
        ("order_id", False),
        ("order_total", False),
        ("new_test_col", False),
    ],
    "stg_orders_v2": [
        ("user_id", True),
        ("order_id", False),
        ("order_total", False),
    ],
    "fct_revenue_v2": [
        ("user_id", True),
        ("order_total", False),
    ],
}


def make_dataset_urn(table: str) -> str:
    return str(DatasetUrn(platform=PLATFORM, name=table, env=ENV))


def make_field_urn(table: str, column: str) -> str:
    return str(SchemaFieldUrn(parent=make_dataset_urn(table), field_path=column))


def column_type_for(col_name: str) -> SchemaFieldDataTypeClass:
    if "total" in col_name or "amount" in col_name or "sum" in col_name:
        return SchemaFieldDataTypeClass(type=NumberTypeClass())
    return SchemaFieldDataTypeClass(type=StringTypeClass())


def build_schema_metadata(table: str) -> SchemaMetadataClass:
    now_ms = 0
    audit = AuditStampClass(time=now_ms, actor="urn:li:corpuser:ingestion")
    fields = []
    for col_name, nullable in COLUMNS[table]:
        fields.append(
            SchemaFieldClass(
                fieldPath=col_name,
                type=column_type_for(col_name),
                nullable=nullable,
                description=f"Column {col_name} of {table}",
                nativeDataType="character varying" if "id" in col_name else "numeric",
            )
        )
    return SchemaMetadataClass(
        schemaName="public",
        platform=f"urn:li:dataPlatform:{PLATFORM}",
        platformSchema={},
        version=0,
        created=audit,
        lastModified=audit,
        fields=fields,
        hash="",
    )


def build_dataset_properties(table: str) -> DatasetPropertiesClass:
    descriptions = {
        "raw_orders_v2": "Raw ingestion of orders from the transactional database.",
        "stg_orders_v2": "Cleansed staging table derived from raw_orders_v2.",
        "fct_revenue_v2": "Revenue fact table aggregated from raw_orders_v2.",
    }
    return DatasetPropertiesClass(
        description=descriptions.get(table, ""),
        customProperties={"source": "python-seed-script"},
    )


def build_ownership() -> OwnershipClass:
    return OwnershipClass(
        owners=[OwnerClass(owner=DATAHUB_USER_URN, type="TECHNICAL_OWNER")],
        lastModified=AuditStampClass(time=0, actor=DATAHUB_USER_URN),
    )


def build_upstream_lineage(table: str) -> UpstreamLineageClass:
    now_ms = 0
    audit = AuditStampClass(time=now_ms, actor="urn:li:corpuser:ingestion")
    upstreams: list[UpstreamClass] = []
    fine_grained: list[FineGrainedLineageClass] = []
    raw_urn = make_dataset_urn("raw_orders_v2")

    if table == "stg_orders_v2":
        upstreams.append(UpstreamClass(dataset=raw_urn, type="TRANSFORMED", auditStamp=audit))
        fine_grained.append(
            FineGrainedLineageClass(
                upstreamType="FIELD_SET",
                upstreams=[make_field_urn("raw_orders_v2", "user_id")],
                downstreamType="FIELD",
                downstreams=[make_field_urn("stg_orders_v2", "user_id")],
                transformOperation="DIRECT_REFERENCE",
                confidenceScore=1.0,
            )
        )
    elif table == "fct_revenue_v2":
        upstreams.append(UpstreamClass(dataset=raw_urn, type="TRANSFORMED", auditStamp=audit))
        fine_grained.append(
            FineGrainedLineageClass(
                upstreamType="FIELD_SET",
                upstreams=[make_field_urn("raw_orders_v2", "user_id")],
                downstreamType="FIELD",
                downstreams=[make_field_urn("fct_revenue_v2", "user_id")],
                transformOperation="JOIN_KEY",
                confidenceScore=1.0,
            )
        )

    return UpstreamLineageClass(
        upstreams=upstreams,
        fineGrainedLineages=fine_grained if fine_grained else None,
    )


def build_mcps_for_table(table: str) -> list[MetadataChangeProposalWrapper]:
    urn = make_dataset_urn(table)
    aspects = [
        build_schema_metadata(table),
        build_dataset_properties(table),
        build_ownership(),
    ]
    if table in ("stg_orders_v2", "fct_revenue_v2"):
        aspects.append(build_upstream_lineage(table))
    return MetadataChangeProposalWrapper.construct_many(urn, aspects)


def main() -> None:
    emitter = DatahubRestEmitter(gms_server=GMS_URL, disable_ssl_verification=True)
    for table in TABLES:
        mcps = build_mcps_for_table(table)
        for mcp in mcps:
            emitter.emit_mcp(mcp)
        print(f"  [OK]  emitted {table} ({len(mcps)} aspects)")
    emitter.flush()
    print("\nDone - 3 tables, ownership, and column-level lineage pushed.")


if __name__ == "__main__":
    main()
