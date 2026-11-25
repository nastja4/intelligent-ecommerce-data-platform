with cart_totals as (
    select
        coalesce(sum(gross_cart_value), 0.00) as total_gross_cart_value,
        count(*) as cart_count,
        coalesce(sum(total_quantity), 0) as total_quantity
    from {{ ref('cart_summary') }}
)

select
    total_gross_cart_value,
    cart_count,
    decimal_division(
        total_gross_cart_value, nullif(cart_count, 0)::decimal(38, 0), 2
    ) as average_cart_value,
    total_quantity,
    coalesce(
        greatest(
            (select max(ingested_at) from {{ ref('stg_products') }}),
            (select max(ingested_at) from {{ ref('stg_users') }}),
            (select max(ingested_at) from {{ ref('stg_carts') }})
        ),
        current_timestamp
    ) as snapshot_at
from cart_totals
