-- fct_revenue_v2.sql
-- Revenue fact: JOINS on raw_orders_v2.customer_id and aggregates order_total.
select
    o.customer_id,
    sum(o.order_total) as total_revenue
from raw_orders_v2 o
join customers c
    on o.customer_id = c.customer_id
group by o.customer_id
