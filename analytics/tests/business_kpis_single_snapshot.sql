select count(*) as snapshot_count
from {{ ref('business_kpis') }}
having count(*) <> 1
