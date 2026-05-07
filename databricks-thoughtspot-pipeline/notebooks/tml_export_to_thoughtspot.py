# Databricks notebook source
# MAGIC %md
# MAGIC # TML Export to ThoughtSpot
# MAGIC
# MAGIC Imports physical table TMLs and Model TML into ThoughtSpot via REST API v2.0.
# MAGIC
# MAGIC **Pipeline**: UC Metric View → Table TMLs + Model TML → ThoughtSpot Import → Search Validation
# MAGIC
# MAGIC **Prerequisites**:
# MAGIC - Tables in `TS_AGENT_DEMO.SALES`
# MAGIC - ThoughtSpot connection "Databricks MV" with `catalog=ts_agent_demo` in Advanced
# MAGIC - Bearer token in Databricks Secrets (scope: `thoughtspot`, key: `api-token`)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration and Authentication

# COMMAND ----------

import requests
import os
import json
import time

CONFIG = {
    "ts_base_url": "https://databricks-emea.thoughtspot.cloud",
    "secret_scope": "thoughtspot",
    "secret_key": "api-token",
    "connection_name": "Databricks MV",
    "tml_dir": os.path.dirname(os.path.abspath(__file__)) + "/../tml",
}


def get_ts_headers() -> dict:
    """Retrieve ThoughtSpot bearer token from Databricks Secrets."""
    token = dbutils.secrets.get(scope=CONFIG["secret_scope"], key=CONFIG["secret_key"])
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# Test the connection
headers = get_ts_headers()
resp = requests.get(f"{CONFIG['ts_base_url']}/api/rest/2.0/auth/session/user", headers=headers)

if resp.status_code == 200:
    user_info = resp.json()
    print(f"✓ Connected to ThoughtSpot as: {user_info.get('name', 'unknown')}")
    print(f"  Cluster: {CONFIG['ts_base_url']}")
else:
    raise Exception(f"✗ Auth failed ({resp.status_code}): {resp.text[:200]}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Load TML Files

# COMMAND ----------

tml_dir = CONFIG["tml_dir"]

# Load table TMLs
table_tml_dir = os.path.join(tml_dir, "tables")
model_tml_dir = os.path.join(tml_dir, "models")

table_files = [
    "REGION.table.tml",
    "NATION.table.tml",
    "CUSTOMER.table.tml",
    "ORDERS.table.tml",
    "LINEITEM.table.tml",
]

model_files = [
    "SALES_MODEL.model.tml",
]

print("Loading TML files...")
print("=" * 60)

tml_contents = {}

# Load table TMLs
print("\nTable TMLs:")
for filename in table_files:
    filepath = os.path.join(table_tml_dir, filename)
    if os.path.exists(filepath):
        with open(filepath) as f:
            tml_contents[filename] = f.read()
        print(f"  ✓ {filename:30s} ({len(tml_contents[filename]):,} chars)")
    else:
        print(f"  ✗ {filename:30s} (NOT FOUND at {filepath})")

# Load model TMLs
print("\nModel TMLs:")
for filename in model_files:
    filepath = os.path.join(model_tml_dir, filename)
    if os.path.exists(filepath):
        with open(filepath) as f:
            tml_contents[filename] = f.read()
        print(f"  ✓ {filename:30s} ({len(tml_contents[filename]):,} chars)")
    else:
        print(f"  ✗ {filename:30s} (NOT FOUND at {filepath})")

print(f"\nTotal: {len(tml_contents)} TML files loaded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Table TMLs to ThoughtSpot
# MAGIC Tables must be imported FIRST (model depends on them).

# COMMAND ----------

headers = get_ts_headers()
url = f"{CONFIG['ts_base_url']}/api/rest/2.0/metadata/tml/import"

print("Importing TABLE TMLs to ThoughtSpot...")
print("=" * 60)

results_summary = []

for filename in table_files:
    tml_content = tml_contents.get(filename)
    if not tml_content:
        print(f"  ⏭ {filename:30s} → SKIPPED (not found)")
        continue

    payload = {
        "metadata_tmls": [tml_content],
        "import_policy": "PARTIAL",
        "create_new": False,  # Set to True for first-time import
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                response = item.get("response", {})
                header = response.get("header", {})
                status = response.get("status", {})
                name = header.get("name", filename)
                guid = header.get("id_guid", "")
                status_code = status.get("status_code", "unknown")
                error_msg = status.get("error_message", "")

                if status_code in ("OK", "WARNING"):
                    print(f"  ✓ {filename:30s} → {name} ({guid[:8]}...) {status_code}")
                    results_summary.append((filename, "OK", guid))
                else:
                    print(f"  ✗ {filename:30s} → ERROR: {error_msg[:150]}")
                    results_summary.append((filename, "ERROR", error_msg[:150]))
        else:
            print(f"  ✗ {filename:30s} → HTTP {resp.status_code}: {resp.text[:200]}")
            results_summary.append((filename, f"HTTP {resp.status_code}", resp.text[:200]))
    except Exception as e:
        print(f"  ✗ {filename:30s} → Exception: {e}")
        results_summary.append((filename, "EXCEPTION", str(e)))

    time.sleep(2)

successes = sum(1 for _, s, _ in results_summary if s == "OK")
print(f"\nTable import: {successes}/{len(results_summary)} succeeded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Import Model TML to ThoughtSpot
# MAGIC The model defines joins, formulas, and curated columns over the physical tables.
# MAGIC This creates a **Worksheet/Model** object that represents the UC Metric View.

# COMMAND ----------

print("\nImporting MODEL TML to ThoughtSpot...")
print("=" * 60)

for filename in model_files:
    tml_content = tml_contents.get(filename)
    if not tml_content:
        print(f"  ⏭ {filename:30s} → SKIPPED (not found)")
        continue

    payload = {
        "metadata_tmls": [tml_content],
        "import_policy": "PARTIAL",
        "create_new": False,  # Set to True for first-time import
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            for item in data:
                response = item.get("response", {})
                header = response.get("header", {})
                status = response.get("status", {})
                name = header.get("name", filename)
                guid = header.get("id_guid", "")
                status_code = status.get("status_code", "unknown")
                error_msg = status.get("error_message", "")

                if status_code in ("OK", "WARNING"):
                    print(f"  ✓ {filename:30s} → {name} ({guid[:8]}...) {status_code}")
                    print(f"    Model is now available as a Worksheet in ThoughtSpot!")
                else:
                    print(f"  ✗ {filename:30s} → ERROR: {error_msg[:200]}")
        else:
            print(f"  ✗ {filename:30s} → HTTP {resp.status_code}: {resp.text[:300]}")
    except Exception as e:
        print(f"  ✗ {filename:30s} → Exception: {e}")

    time.sleep(2)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validate: Search Data API

# COMMAND ----------

headers = get_ts_headers()
search_url = f"{CONFIG['ts_base_url']}/api/rest/2.0/searchdata"

# Find SALES_MODEL GUID (the model/worksheet)
search_resp = requests.post(
    f"{CONFIG['ts_base_url']}/api/rest/2.0/metadata/search",
    headers=headers,
    json={"metadata": [{"type": "LOGICAL_TABLE", "name_pattern": "SALES_MODEL"}]},
    timeout=30,
)

model_guid = None
if search_resp.status_code == 200:
    results = search_resp.json()
    if results:
        model_guid = results[0].get("metadata_id", "")
        print(f"SALES_MODEL GUID: {model_guid}")

if not model_guid:
    print("⚠ Could not find SALES_MODEL. Trying SALES_SV instead.")
    # Fallback to flat table
    search_resp = requests.post(
        f"{CONFIG['ts_base_url']}/api/rest/2.0/metadata/search",
        headers=headers,
        json={"metadata": [{"type": "LOGICAL_TABLE", "name_pattern": "SALES_SV"}]},
        timeout=30,
    )
    if search_resp.status_code == 200:
        results = search_resp.json()
        if results:
            model_guid = results[0].get("metadata_id", "")
            print(f"SALES_SV GUID (fallback): {model_guid}")

if not model_guid:
    print("✗ No searchable object found. Skipping validation.")
else:
    # Test queries
    test_queries = [
        "[Net Revenue] by [Region Name]",
        "[Net Revenue] [Order Count] by [Market Segment]",
        "[Total Revenue] [Discount Amount] by [Nation Name]",
    ]

    print(f"\nThoughtSpot Search Validation (on {model_guid[:8]}...)")
    print("=" * 60)

    for query in test_queries:
        payload = {
            "query_string": query,
            "logical_table_identifier": model_guid,
            "data_format": "COMPACT",
            "record_offset": 0,
            "record_size": 5,
        }
        try:
            resp = requests.post(search_url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                rows = data.get("contents", [{}])[0].get("data_rows", [])
                print(f"\n  Query: {query}")
                print(f"  Rows: {len(rows)} ✓")
            else:
                print(f"\n  Query: {query}")
                print(f"  ✗ HTTP {resp.status_code}")
        except Exception as e:
            print(f"\n  Query: {query}")
            print(f"  ✗ Error: {e}")

    print(f"\n{'='*60}")
    print("Validation complete.")
