"""
Finds downstream datasets connected to a given DataHub entity via lineage.

Run standalone to test:
    py -3.11 lineage_lookup.py
"""
import requests

GMS_URL = "http://localhost:8080"


def get_downstream_datasets(source_urn: str) -> list[str]:
    """Return a list of downstream dataset URNs connected to source_urn."""
    query = """
    query getLineage($urn: String!) {
      searchAcrossLineage(
        input: {
          urn: $urn
          direction: DOWNSTREAM
          types: [DATASET]
          start: 0
          count: 20
        }
      ) {
        searchResults {
          entity {
            urn
          }
        }
      }
    }
    """
    resp = requests.post(
        f"{GMS_URL}/api/graphql",
        json={"query": query, "variables": {"urn": source_urn}},
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()

    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")

    results = data["data"]["searchAcrossLineage"]["searchResults"]
    return [r["entity"]["urn"] for r in results]


if __name__ == "__main__":
    raw_orders_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,raw_orders_v2,PROD)"
    downstream = get_downstream_datasets(raw_orders_urn)
    print(f"Downstream of raw_orders_v2:")
    for urn in downstream:
        print(f"  - {urn}")
