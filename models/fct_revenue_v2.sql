-- fct_revenue_v2.sql
-- Revenue fact: JOINS on raw_orders_v2.user_id and aggregates order_total.
select
    o.user_id,
    sum(o.order_total) as total_revenue
from raw_orders_v2 o
join customers c
    on o.user_id = c.user_id
group by o.user_id
