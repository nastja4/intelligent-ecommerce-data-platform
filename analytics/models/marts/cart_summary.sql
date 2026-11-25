with item_totals as (
    select
        cart_id,
        sum({{ gross_cart_line_value('unit_price', 'quantity') }}) as gross_cart_value,
        sum(quantity) as total_quantity
    from {{ ref('stg_cart_items') }}
    group by cart_id
)

select
    carts.cart_id,
    carts.user_id as customer_id,
    coalesce(item_totals.gross_cart_value, 0.00) as gross_cart_value,
    coalesce(item_totals.total_quantity, 0) as total_quantity
from {{ ref('stg_carts') }} as carts
left join item_totals on item_totals.cart_id = carts.cart_id
