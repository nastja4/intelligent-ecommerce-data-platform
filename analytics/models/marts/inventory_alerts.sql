select
    product_id,
    title,
    stock
from {{ ref('stg_products') }}
