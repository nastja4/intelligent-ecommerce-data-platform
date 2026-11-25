select cart_count, average_cart_value
from {{ ref('business_kpis') }}
where (cart_count = 0) is distinct from (average_cart_value is null)
