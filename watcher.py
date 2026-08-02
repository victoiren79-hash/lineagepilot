"""
LineagePilot - live watcher. Detects schema changes on DataHub in real
time and AUTOMATICALLY runs the full pipeline (lineage -> reasoning ->
fix -> PR -> write-back) when it can confidently tell what happened.

This is the piece that makes the "detects a change and fixes it" claim
literally true: you don't tell it what changed, it figures that out from
the live event and acts on it.

How it decides what changed:
  - Exactly one field added + one field removed on the same dataset, in
    the same event -> treated as a RENAME (old = removed field name,
    new = added field name). The pipeline runs automatically.
  - Anything else (pure add, pure delete, type change, multiple fields
    changing at once) -> printed for visibility, but NOT auto-run, since
    it isn't safe to guess a single old->new column pair from it. This
    matches a real limitation: DataHub's schema events don't carry a
    "rename" concept natively, only field-level add/remove, so a rename
    is an inference, not a certainty.

Run with (leave this running in its own terminal):
    py -3.11 watcher.py
"""
import sys, os, json, yaml
from confluent_kafka import Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer

from main import run_pipeline

site_packages = r"C:\Users\VIGO\AppData\Local\Programs\Python\Python311\Lib\site-packages"
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

with open("schema_watcher.yaml", "r") as f:
    config = yaml.safe_load(f)

kafka_bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVER", "localhost:9092")
schema_registry_url = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8080/schema-registry/api/")

schema_registry_conf = {'url': schema_registry_url}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)
avro_deserializer = AvroDeserializer(schema_registry_client)

consumer_conf = {
    'bootstrap.servers': kafka_bootstrap,
    'group.id': config['name'],
    'auto.offset.reset': 'latest',
    'allow.auto.create.topics': 'true'
}

print("Connecting to Kafka...")
consumer = Consumer(consumer_conf)
consumer.subscribe(['MetadataChangeLog_Versioned_v1'])

print("Watching for schema changes. Rename a column in seed_datahub.py and")
print("re-run it (or make any schema change via the SDK) to trigger this.\n")


def parse_aspect(aspect_wrapper):
    if not aspect_wrapper:
        return None
    value = aspect_wrapper.get('value')
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        value = value.decode('utf-8')
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None


def fields_by_path(schema_metadata):
    if not schema_metadata:
        return {}
    return {f['fieldPath']: f for f in schema_metadata.get('fields', [])}


try:
    while True:
        msg = consumer.poll(2.0)

        if msg is None:
            continue

        if msg.error():
            if msg.error().code() in (3, -194):
                continue
            else:
                print(f"Kafka error: {msg.error()}")
                continue

        try:
            event = avro_deserializer(msg.value(), None)
        except Exception:
            continue

        if not event or not isinstance(event, dict):
            continue

        if event.get('entityType') != "dataset":
            continue
        if event.get('aspectName') != "schemaMetadata":
            continue

        entity_urn = event.get('entityUrn', 'Unknown URN')

        new_schema = parse_aspect(event.get('aspect'))
        old_schema = parse_aspect(event.get('previousAspectValue'))

        new_fields = fields_by_path(new_schema)
        old_fields = fields_by_path(old_schema)

        if not old_fields and not new_fields:
            continue

        added = set(new_fields) - set(old_fields)
        removed = set(old_fields) - set(new_fields)

        for field_path in added:
            if field_path not in removed:
                print(f"URN: {entity_urn} | Changed Field: {field_path} | Type of Change: COLUMN_ADDED")
        for field_path in removed:
            print(f"URN: {entity_urn} | Changed Field: {field_path} | Type of Change: COLUMN_DELETED")

        # Confident rename inference: exactly one add + one remove together.
        if len(added) == 1 and len(removed) == 1:
            new_column = next(iter(added))
            old_column = next(iter(removed))
            print(f"\n>>> Inferred RENAME: {old_column} -> {new_column} on {entity_urn}")
            print(">>> Triggering LineagePilot pipeline automatically...\n")
            try:
                run_pipeline(entity_urn, old_column, new_column)
            except Exception as e:
                print(f">>> Pipeline run failed: {e}")
        elif added or removed:
            print(">>> Multiple or ambiguous field changes detected — not auto-running "
                  "the pipeline (can't safely infer a single old->new rename pair). "
                  "Run main.py manually with the correct column names if needed.\n")

except KeyboardInterrupt:
    print("\nStopping watcher...")
finally:
    consumer.close()
