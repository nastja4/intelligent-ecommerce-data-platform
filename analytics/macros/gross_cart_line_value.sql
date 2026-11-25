{% macro gross_cart_line_value(unit_price, quantity) -%}
    ({{ unit_price }} * {{ quantity }})
{%- endmacro %}
