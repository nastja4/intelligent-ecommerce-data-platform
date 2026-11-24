select
    source_id as user_id,
    ingested_at
from {{ source('bronze', 'raw_users') }}
