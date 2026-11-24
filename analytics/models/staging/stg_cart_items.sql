select
    carts.cart_id,
    item.key::bigint as item_ordinal,
    {{ json_scalar('item.value', '$.id', 'bigint') }} as product_id,
    {{ json_scalar('item.value', '$.price', 'decimal(18, 2)') }} as unit_price,
    {{ json_scalar('item.value', '$.quantity', 'bigint') }} as quantity,
    carts.ingested_at
from {{ ref('stg_carts') }} as carts
cross join lateral json_each(carts.items) as item
