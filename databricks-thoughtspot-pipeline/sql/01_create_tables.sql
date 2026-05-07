-- ============================================================
-- Step 1: Create Physical Tables in Unity Catalog
-- Source: TPC-H sample data (replace with your own tables)
-- ============================================================

CREATE CATALOG IF NOT EXISTS TS_AGENT_DEMO;
CREATE SCHEMA IF NOT EXISTS TS_AGENT_DEMO.SALES;

-- Fact tables
CREATE OR REPLACE TABLE TS_AGENT_DEMO.SALES.ORDERS AS SELECT * FROM samples.tpch.orders;
CREATE OR REPLACE TABLE TS_AGENT_DEMO.SALES.LINEITEM AS SELECT * FROM samples.tpch.lineitem;

-- Dimension tables
CREATE OR REPLACE TABLE TS_AGENT_DEMO.SALES.CUSTOMER AS SELECT * FROM samples.tpch.customer;
CREATE OR REPLACE TABLE TS_AGENT_DEMO.SALES.NATION AS SELECT * FROM samples.tpch.nation;
CREATE OR REPLACE TABLE TS_AGENT_DEMO.SALES.REGION AS SELECT * FROM samples.tpch.region;
CREATE OR REPLACE TABLE TS_AGENT_DEMO.SALES.SUPPLIER AS SELECT * FROM samples.tpch.supplier;
CREATE OR REPLACE TABLE TS_AGENT_DEMO.SALES.PART AS SELECT * FROM samples.tpch.part;
