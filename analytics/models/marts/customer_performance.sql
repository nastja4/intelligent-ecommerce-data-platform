select
    customer_id,
    sum(gross_cart_value) as gross_cart_value,
    count(*) as cart_count
from {{ ref('cart_summary') }}
group by customer_id
