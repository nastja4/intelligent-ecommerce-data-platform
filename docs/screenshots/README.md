# Commerce Intelligence screenshot gallery

These owner-captured screenshots show the local Docker dashboard with the complete synthetic DummyJSON dataset, a live assistant conversation, Swagger, and GitHub Actions. [Project overview](../../README.md) · [Verification record](../../PROGRESS.md)

**Publication review pending.** All captures show a browser profile avatar. The CI capture also shows the GitHub account name and avatar, and the assistant captures show estimated budget or request usage. Review and remove those details from the public versions before publishing. The originals are retained here for review.

## Dashboard

### Business overview

![Overview with four cart KPIs, a category performance chart, and a low-stock inventory panel](overview.png)

The four KPI cards summarize the validated synthetic cart snapshot.

### Category analytics

![Horizontal category chart with gross cart values and item counts](categories.png)

The chart ranks categories by gross simulated cart value and shows item counts alongside the ranking.

### Product analytics

![Top-products table with category, gross cart value, item quantity, and a ranking limit set to ten](products.png)

The product page shows the top ten products by gross simulated cart value.

### Customer analytics

![Customer ranking table showing synthetic customer IDs, gross cart value, and cart counts](customers.png)

The ranking uses synthetic customer IDs and aggregate metrics.

### Inventory alerts

![Low-stock inventory table listing products with stock below the selected threshold of ten](inventory.png)

The threshold filter surfaces products with stock strictly below ten.

## AI Assistant

### Suggested questions

![AI Assistant start screen with four suggested analytical questions and a question input](ai-assistant_2.png)

The assistant offers starting questions about KPIs, categories, and stock.

### Category comparison

![Live assistant reply comparing the top three categories in a table with gross cart values and item quantities](ai-assistant_3.png)

The comparison presents the category results, snapshot timestamp, and interpretation of the metric.

### Tool execution and limitations

![Assistant reply with metric limitations, snapshot timestamp, and two expanded MCP tool results](ai-assistant_1.png)

The expanded panel shows successful category performance and business KPI calls. The displayed request cost is an application estimate.

## REST API and Swagger

### Endpoint catalog

![Swagger UI listing analytical, health, and local assistant endpoints](swagger_1.png)

The OpenAPI interface groups available endpoints and lists their schemas.

### KPI request

![Swagger showing an HTTP 200 response from the KPI endpoint with the snapshot timestamp and four metrics](swagger_2.png)

The example response exposes the snapshot, metric basis, and the four overview KPIs.

### Response schemas

![Swagger schema list for analytics, snapshots, chat requests, tool execution, and usage](swagger_3.png)

The schema catalog documents the structured API contracts.

## GitHub Actions

![GitHub Actions workflow list with successful full-stack pull request and historical main-branch runs](ci-cd.png)

The workflow list shows the successful full-stack PR run and the earlier backend run on main. [Publication status](../../PROGRESS.md)
