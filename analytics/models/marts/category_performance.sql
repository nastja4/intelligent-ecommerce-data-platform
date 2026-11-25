select
    category,
    sum(gross_cart_value) as gross_cart_value,
    sum(total_quantity) as total_quantity
from {{ ref('product_performance') }}
group by category
