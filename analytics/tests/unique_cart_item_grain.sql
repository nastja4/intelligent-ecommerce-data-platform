select cart_id, item_ordinal
from {{ ref('stg_cart_items') }}
group by cart_id, item_ordinal
having count(*) > 1
