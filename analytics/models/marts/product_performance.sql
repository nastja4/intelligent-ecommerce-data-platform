with item_totals as (
    select
        product_id,
        sum({{ gross_cart_line_value('unit_price', 'quantity') }}) as gross_cart_value,
        sum(quantity) as total_quantity
    from {{ ref('stg_cart_items') }}
    group by product_id
)

select
    item_totals.product_id,
    products.title,
    products.category,
    item_totals.gross_cart_value,
    item_totals.total_quantity
from item_totals
join {{ ref('stg_products') }} as products on products.product_id = item_totals.product_id
