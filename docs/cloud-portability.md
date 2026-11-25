# Cloud portability

The shipped MVP uses DuckDB and dbt Core with dbt-duckdb. No cloud deployment has been implemented or verified. The options below describe how to move the existing pipeline while preserving its data contracts and validation rules.

## What moves

Keep HTTP extraction, the Bronze/Silver/Gold separation, dbt lineage, fixture tests, and the REST/MCP contracts. Replace the DuckDB loader and read connector with platform-specific implementations. Rework JSON extraction and array flattening, relation naming, parameter placeholders and ranking syntax, and decimal division and timestamp conversion.

Replace the local candidate file with an isolated batch or schema. Run dbt and reconcile the candidate, then switch a serving view or batch pointer using a publication mechanism verified for that platform. Keep the previous validated batch available on failure. Give the loader, transformer, and shared read service separate identities. The service identity should only read approved Gold results.

| Platform | Proposed adaptation |
| --- | --- |
| **BigQuery** | Use `dbt-bigquery` with Bronze, Silver, and Gold datasets. Load raw JSON into BigQuery directly or from Cloud Storage. Use GoogleSQL `JSON_QUERY_ARRAY` and `UNNEST ... WITH OFFSET` to preserve line positions. Use a workload identity or service account with scoped dataset access. Run the gated batch from a controlled job and have the Python read service query published Gold datasets. [BigQuery JSON](https://docs.cloud.google.com/bigquery/docs/json-data), [query syntax](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax) |
| **Snowflake** | Use `dbt-snowflake` with a staged load into Bronze `VARIANT` columns and role-scoped schemas. Flatten items with `LATERAL FLATTEN` and its array `INDEX`. Run dbt on a designated warehouse with a dedicated job identity, and give serving a separate Gold read role. [Snowflake FLATTEN](https://docs.snowflake.com/en/sql-reference/functions/flatten) |
| **Databricks** | Use `dbt-databricks`, Unity Catalog, and Delta tables. Parse cart arrays and use `posexplode` to retain position. Run the batch with a service principal in a Databricks job or an external runner, and query published Gold tables through a SQL warehouse and restricted service identity. [Databricks posexplode](https://docs.databricks.com/aws/en/sql/language-manual/functions/posexplode) |
| **Microsoft Fabric** | Use `dbt-fabric` with a Fabric Warehouse. Land data in the Warehouse or stage it in OneLake, then build typed Warehouse tables or views. Use T-SQL `OPENJSON` and its array key for ordinals. Use Microsoft Entra identities for transformation and Gold reads. A Fabric dbt job or an external runner can execute the gated batch. [Fabric dbt patterns](https://learn.microsoft.com/en-us/fabric/data-factory/common-dbt-job-patterns), [Warehouse connectivity](https://learn.microsoft.com/en-us/fabric/data-warehouse/connectivity), [OPENJSON](https://learn.microsoft.com/en-us/sql/t-sql/functions/openjson-transact-sql) |

Before moving a target into service, verify adapter and dbt Core compatibility, exact metric parity, array ordinal and empty-cart behavior, half-even monetary rounding, permissions, and failed-publication recovery. Keep cloud credentials out of the repository and image, and confirm cost and capacity requirements with the owner. The existing GitHub workflow delivers a container image. Cloud orchestration and deployment would need separate configuration. [dbt adapters](https://docs.getdbt.com/docs/supported-data-platforms)
