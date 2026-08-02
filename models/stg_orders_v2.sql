-- stg_orders_v2.sql
-- Staging model: simple passthrough, references raw_orders_v2.user_id directly.
select
    user_id,
    order_id,
    order_total
from raw_orders_v2
