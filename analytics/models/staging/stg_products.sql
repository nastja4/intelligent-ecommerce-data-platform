select
    source_id as product_id,
    {{ json_scalar('payload', '$.title', 'varchar') }} as title,
    {{ json_scalar('payload', '$.category', 'varchar') }} as category,
    {{ json_scalar('payload', '$.price', 'decimal(18, 2)') }} as price,
    {{ json_scalar('payload', '$.stock', 'bigint') }} as stock,
    ingested_at
from {{ source('bronze', 'raw_products') }}
