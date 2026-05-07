-- ============================================================
-- Step 3: Create the Flat SQL View
-- Denormalized view that ThoughtSpot can query directly.
-- ThoughtSpot applies SUM aggregation at query time.
-- ============================================================

CREATE OR REPLACE VIEW TS_AGENT_DEMO.SALES.SALES_SV AS
SELECT
  -- Dimensions
  c.c_name           AS customer_name,
  c.c_mktsegment     AS market_segment,
  n.n_name           AS nation_name,
  r.r_name           AS region_name,
  o.o_orderdate      AS order_date,
  o.o_orderstatus    AS order_status,
  o.o_orderpriority  AS order_priority,
  l.l_shipmode       AS ship_mode,
  o.o_orderkey       AS order_key,

  -- Measures (row-level; ThoughtSpot applies SUM at query time)
  l.l_quantity                            AS quantity,
  l.l_extendedprice                       AS extended_price,
  l.l_discount                            AS discount,
  l.l_tax                                 AS tax,
  l.l_extendedprice                       AS total_revenue,
  l.l_extendedprice * (1 - l.l_discount)  AS net_revenue,
  l.l_extendedprice * l.l_discount        AS discount_amount,
  1                                       AS order_count,
  l.l_extendedprice * (1 - l.l_discount)  AS avg_order_value

FROM TS_AGENT_DEMO.SALES.LINEITEM l
JOIN TS_AGENT_DEMO.SALES.ORDERS o   ON l.l_orderkey = o.o_orderkey
JOIN TS_AGENT_DEMO.SALES.CUSTOMER c ON o.o_custkey = c.c_custkey
JOIN TS_AGENT_DEMO.SALES.NATION n   ON c.c_nationkey = n.n_nationkey
JOIN TS_AGENT_DEMO.SALES.REGION r   ON n.n_regionkey = r.r_regionkey;
