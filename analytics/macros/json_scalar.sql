{% macro json_scalar(document, path, sql_type) -%}
    {%- set json_types = {
        'bigint': ['BIGINT', 'UBIGINT'],
        'varchar': ['VARCHAR'],
        'decimal(18, 2)': ['BIGINT', 'UBIGINT', 'DOUBLE']
    }[sql_type] -%}
    {%- set value = "json_extract_string(" ~ document ~ ", '" ~ path ~ "')" -%}
    case
        when json_type({{ document }}, '{{ path }}') in ('{{ json_types | join("', '") }}')
        {%- if sql_type == 'decimal(18, 2)' %}
            {# Let the not-null test catch negative amounts that would round to zero. #}
            and not (try_cast({{ value }} as double) < 0 and try_cast({{ value }} as {{ sql_type }}) = 0)
        {%- endif %}
        then try_cast({{ value }} as {{ sql_type }})
    end
{%- endmacro %}
