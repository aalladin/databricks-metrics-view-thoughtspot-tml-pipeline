# Databricks UC Metric View → ThoughtSpot Pipeline

End-to-end pipeline for publishing Databricks Unity Catalog Metric Views to ThoughtSpot as searchable Models (Worksheets) via the TML REST API.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  DATABRICKS (Unity Catalog)                                 │
│                                                             │
│  Physical Tables          UC Metric View                    │
│  ┌──────────┐            ┌────────────────┐                │
│  │ LINEITEM │──┐         │   SALES_MV     │                │
│  │ ORDERS   │  │  used   │   (measures +  │                │
│  │ CUSTOMER │──┼────by───│    dimensions) │                │
│  │ NATION   │  │         │                │                │
│  │ REGION   │──┘         └───────┬────────┘                │
│                                  │                          │
└──────────────────────────────────┼──────────────────────────┘
                                   │ maps to
                                   ▼
┌─────────────────────────────────────────────────────────────┐
│  ThoughtSpot TML                                            │
│                                                             │
│  Table TMLs              Model TML                          │
│  (1:1 physical)          (joins + formulas + columns)       │
│  ┌──────────┐            ┌────────────────┐                │
│  │ LINEITEM │            │  SALES_MODEL   │                │
│  │ ORDERS   │◀───refs────│  • joins       │                │
│  │ CUSTOMER │            │  • formulas    │                │
│  │ NATION   │            │  • columns     │                │
│  │ REGION   │            │  • synonyms    │                │
│  └──────────┘            └───────┬────────┘                │
│                                  │                          │
└──────────────────────────────────┼──────────────────────────┘
                                   │ REST API /tml/import
                                   ▼
┌─────────────────────────────────────────────────────────────┐
│  ThoughtSpot Cluster                                        │
│                                                             │
│  ┌──────────────────────────────────────────┐              │
│  │  SALES_MODEL (Worksheet)                  │              │
│  │  • Spotter / Natural Language Search      │              │
│  │  • Liveboards & Answers                   │              │
│  └──────────────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
databricks-thoughtspot-pipeline/
├── README.md                              ← You are here
├── .gitignore
├── sql/
│   ├── 01_create_tables.sql              # Create TPC-H physical tables
│   ├── 02_create_metric_view.sql         # Create UC Metric View (SALES_MV)
│   └── 03_create_flat_view.sql           # Create flat view (optional alternative)
├── tml/
│   ├── tables/
│   │   ├── LINEITEM.table.tml            # Physical table definitions
│   │   ├── ORDERS.table.tml
│   │   ├── CUSTOMER.table.tml
│   │   ├── NATION.table.tml
│   │   └── REGION.table.tml
│   ├── models/
│   │   └── SALES_MODEL.model.tml         # Model with joins, formulas, synonyms
│   └── SALES_SV.table.tml               # Flat view TML (alternative approach)
├── notebooks/
│   └── tml_export_to_thoughtspot.py      # Main import pipeline (Databricks notebook)
└── scripts/
    └── token_refresh.py                  # Scheduled token refresh job
```

## Quick Start

### 1. Create Databricks Tables

Run `sql/01_create_tables.sql` to create the TPC-H tables in `TS_AGENT_DEMO.SALES`.

### 2. Create UC Metric View

Run `sql/02_create_metric_view.sql` to define the semantic layer with measures and dimensions.

### 3. Configure ThoughtSpot Connection

Create a connection in ThoughtSpot:

| Setting | Value |
| --- | --- |
| Name | `Databricks MV` |
| Type | Databricks |
| Auth | OAuth (Service Principal) |
| Host | Your Databricks SQL warehouse host |
| **Advanced** | Key: `catalog`, Value: `ts_agent_demo` |

> ⚠️ The `catalog` advanced setting is **required** for OAuth connections.

### 4. Store Credentials

```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
w.secrets.create_scope(scope="thoughtspot")
w.secrets.put_secret(scope="thoughtspot", key="api-token", string_value="<token>")
# For token refresh automation:
w.secrets.put_secret(scope="thoughtspot", key="username", string_value="<user>")
w.secrets.put_secret(scope="thoughtspot", key="password", string_value="<pass>")
```

### 5. Run the Import Pipeline

Execute `notebooks/tml_export_to_thoughtspot.py` as a Databricks notebook. It will:
1. Authenticate to ThoughtSpot
2. Import table TMLs (physical tables)
3. Import the Model TML (creates the Worksheet with joins + formulas)
4. Validate via Search Data API

### 6. Use in ThoughtSpot

The `SALES_MODEL` appears as a **Worksheet** in ThoughtSpot with:
- Pre-defined formulas (Net Revenue, Order Count, Avg Order Value, etc.)
- Joins between all tables (LINEITEM → ORDERS → CUSTOMER → NATION → REGION)
- Synonyms for natural language search (e.g., "Revenue" → Net Revenue)
- AI context for Spotter-powered analytics

## Two Approaches

This repo supports two approaches for representing the metric view in ThoughtSpot:

| Approach | TML Type | Pros | Cons |
| --- | --- | --- | --- |
| **Model** (recommended) | `model:` | Joins, formulas, synonyms, AI context, Spotter | More complex TML |
| **Flat View** | `table:` | Simple, single TML | No formula control, no synonyms |

- **Model approach**: Use `tml/tables/*.tml` + `tml/models/SALES_MODEL.model.tml`
- **Flat view approach**: Use `tml/SALES_SV.table.tml` (requires `sql/03_create_flat_view.sql`)

## TML Format Reference

### Table TML (physical table)
```yaml
table:
  name: ORDERS
  db: ts_agent_demo          # lowercase (Unity Catalog)
  schema: sales              # lowercase
  db_table: orders           # lowercase
  connection:
    name: Databricks MV
  columns:
  - name: O_ORDERKEY         # UPPERCASE display name
    db_column_name: o_orderkey  # lowercase (UC convention)
    properties:
      column_type: ATTRIBUTE
    db_column_properties:
      data_type: INT64
```

### Model TML (semantic layer)
```yaml
model:
  name: SALES_MODEL
  model_tables:
  - name: LINEITEM
    joins:
    - with: ORDERS
      'on': '[LINEITEM::L_ORDERKEY] = [ORDERS::O_ORDERKEY]'
      type: INNER
      cardinality: MANY_TO_ONE
  formulas:
  - id: formula_Net Revenue
    name: Net Revenue
    expr: sum ( [LINEITEM::L_EXTENDEDPRICE] * ( 1 - [LINEITEM::L_DISCOUNT] ) )
  columns:
  - name: Net Revenue
    formula_id: formula_Net Revenue
    properties:
      column_type: MEASURE
      aggregation: SUM
```

## Token Management

Tokens expire after ~24 hours. Use `scripts/token_refresh.py` as a scheduled Databricks Job:

```
Schedule: Every 12 hours (cron: 0 0 */12 * * ? *)
```

## Troubleshooting

| Issue | Fix |
| --- | --- |
| "Database does not exist" | Add `catalog = ts_agent_demo` in connection Advanced |
| "aggregation: NONE" rejected | Remove `aggregation` line for ATTRIBUTE columns |
| "table already exists" | Set `create_new: False` in import payload |
| 401 Unauthorized | Token expired; run `scripts/token_refresh.py` |
| Model import fails | Ensure all referenced tables are imported first |

## Key Learnings

1. **Tables before Model**: Table TMLs must be imported before the Model TML (model references tables by name)
2. **UC = lowercase**: All `db`, `schema`, `db_table`, `db_column_name` must be lowercase
3. **OAuth needs catalog**: Service principal connections require `catalog` in Advanced settings
4. **Model = Worksheet**: A ThoughtSpot Model TML creates a Worksheet object with joins + formulas
5. **Spotter uses synonyms**: Add `synonyms` and `ai_context` to columns for better NL search

## License

Internal use — Databricks + ThoughtSpot field teams.
