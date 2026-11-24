{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set schema = custom_schema_name | trim if custom_schema_name is not none else target.schema -%}
    {%- if schema in ['silver', 'gold'] or custom_schema_name is none -%}
        {{ schema }}
    {%- else -%}
        {{ target.schema }}_{{ schema }}
    {%- endif -%}
{%- endmacro %}
