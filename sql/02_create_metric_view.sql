-- ============================================================
-- Step 2: Create the UC Metric View
-- Defines semantic dimensions and measures using YAML syntax
-- ============================================================

CREATE OR REPLACE VIEW TS_AGENT_DEMO.SALES.SALES_MV
WITH METRICS LANGUAGE YAML AS $$
source: lineitem
joins:
  - target: orders
    on: lineitem.l_orderkey = orders.o_orderkey
  - target: customer
    on: orders.o_custkey = customer.c_custkey
  - target: nation
    on: customer.c_nationkey = nation.n_nationkey
  - target: region
    on: nation.n_regionkey = region.r_regionkey

dimensions:
  - name: order_date
    expr: orders.o_orderdate
  - name: order_status
    expr: |
      CASE orders.o_orderstatus
        WHEN 'F' THEN 'Fulfilled'
        WHEN 'O' THEN 'Open'
        WHEN 'P' THEN 'Partial'
      END
  - name: order_priority
    expr: orders.o_orderpriority
  - name: ship_mode
    expr: lineitem.l_shipmode
  - name: customer_name
    expr: customer.c_name
  - name: market_segment
    expr: customer.c_mktsegment
  - name: nation_name
    expr: nation.n_name
  - name: region_name
    expr: region.r_name

measures:
  - name: total_revenue
    expr: SUM(lineitem.l_extendedprice)
  - name: net_revenue
    expr: SUM(lineitem.l_extendedprice * (1 - lineitem.l_discount))
  - name: discount_amount
    expr: SUM(lineitem.l_extendedprice * lineitem.l_discount)
  - name: order_count
    expr: COUNT(DISTINCT orders.o_orderkey)
  - name: avg_order_value
    expr: MEASURE(net_revenue) / MEASURE(order_count)
$$;
