with cart_totals as (
    select
        coalesce(sum(gross_cart_value), 0) as gross_value,
        coalesce(sum(total_quantity), 0) as quantity,
        count(*) as cart_count
    from {{ ref('cart_summary') }}
),
product_totals as (
    select
        coalesce(sum(gross_cart_value), 0) as gross_value,
        coalesce(sum(total_quantity), 0) as quantity
    from {{ ref('product_performance') }}
),
category_totals as (
    select
        coalesce(sum(gross_cart_value), 0) as gross_value,
        coalesce(sum(total_quantity), 0) as quantity
    from {{ ref('category_performance') }}
),
customer_totals as (
    select
        coalesce(sum(gross_cart_value), 0) as gross_value,
        coalesce(sum(cart_count), 0) as cart_count
    from {{ ref('customer_performance') }}
)

select
    carts.gross_value as cart_gross_value,
    products.gross_value as product_gross_value,
    categories.gross_value as category_gross_value,
    customers.gross_value as customer_gross_value,
    kpis.total_gross_cart_value as kpi_gross_value
from cart_totals as carts
cross join product_totals as products
cross join category_totals as categories
cross join customer_totals as customers
cross join {{ ref('business_kpis') }} as kpis
where carts.gross_value is distinct from products.gross_value
    or carts.gross_value is distinct from categories.gross_value
    or carts.gross_value is distinct from customers.gross_value
    or carts.gross_value is distinct from kpis.total_gross_cart_value
    or carts.quantity is distinct from products.quantity
    or carts.quantity is distinct from categories.quantity
    or carts.quantity is distinct from kpis.total_quantity
    or carts.cart_count is distinct from customers.cart_count
    or carts.cart_count is distinct from kpis.cart_count
    or carts.cart_count <> (select count(*) from {{ ref('stg_carts') }})
