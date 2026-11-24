select
    source_id as cart_id,
    {{ json_scalar('payload', '$.userId', 'bigint') }} as user_id,
    {{ json_scalar('payload', '$.total', 'decimal(18, 2)') }} as source_total,
    {{ json_scalar('payload', '$.discountedTotal', 'decimal(18, 2)') }} as source_discounted_total,
    case
        when json_type(payload, '$.products') = 'ARRAY'
        then json_extract(payload, '$.products')
    end as items,
    ingested_at
from {{ source('bronze', 'raw_carts') }}
