# Intelligent E-Commerce Data Platform

## 1. Project Objective

Build an end-to-end data platform that integrates,
transforms, validates and exposes e-commerce data
through a REST API and an AI-compatible MCP server.

The project demonstrates practical capabilities in:

- Data Engineering
- Analytics Engineering
- Backend Development
- AI Engineering
- DevOps and CI/CD
- Spec-driven Development

## 2. Business Requirements

The platform must enable users to:

- Analyze product performance.
- Analyze product categories.
- Calculate simulated cart revenue.
- Calculate average cart value.
- Identify high-value customers based on cart data.
- Identify products with low inventory.
- Access analytical data through REST endpoints.
- Query business metrics using an AI agent.

DummyJSON provides synthetic shopping cart data,
not actual completed sales transactions.
All financial metrics must be interpreted accordingly.

## 3. Technology Stack

- Python 3.12
- SQL
- DuckDB
- dbt Core and dbt-duckdb
- DummyJSON REST API
- FastAPI
- MCP Python SDK
- Claude Code
- pytest
- Docker
- GitHub Actions
- GitHub Container Registry
- Git and GitHub

## 4. System Architecture

The platform follows an ELT architecture:

DummyJSON API
-> Python Extract and Load
-> DuckDB Bronze Layer
-> dbt Silver Layer
-> dbt Gold Layer
-> Shared Query Services
-> REST API / MCP Server
-> Business Users / AI Agent

## 5. Functional Requirements

### FR-01: Data Extraction

- Retrieve products, users and carts from DummyJSON.
- Support API pagination.
- Handle HTTP errors and request timeouts.
- Record ingestion timestamps.

### FR-02: Data Loading

- Store source data in DuckDB.
- Preserve raw source records in the Bronze layer.
- Support repeatable full-refresh ingestion.
- Prevent duplicate records across repeated runs.
- Use transactions where appropriate.

### FR-03: Data Transformation

Use dbt Core for SQL-based transformations.

Bronze:

- Raw products
- Raw users
- Raw carts

Silver:

- Cleaned and typed products
- Cleaned and typed users
- Cleaned carts
- Flattened cart items
- Deduplicated records

Gold:

- Product performance
- Category performance
- Customer performance
- Cart summary
- Inventory alerts

Implement:

- dbt sources
- source() and ref()
- Jinja
- Staging models
- Data marts
- Materializations
- Data lineage
- dbt documentation

### FR-04: Data Quality

Validate:

- Primary key uniqueness
- Non-null required fields
- Referential integrity
- Non-negative prices and quantities
- Valid business metric calculations

Implement dbt data tests and pytest tests.

Data quality failures must be visible and must
cause the relevant validation step to fail.

### FR-05: Business Analytics

Calculate:

- Total simulated cart value
- Total number of carts
- Average cart value
- Total cart item quantity
- Top products by simulated cart revenue
- Category-level performance
- Customer-level cart value
- Low-stock products

Document the business definition of each metric.

### FR-06: REST API

Implement FastAPI endpoints:

GET /health
GET /api/v1/kpis
GET /api/v1/products/top
GET /api/v1/categories
GET /api/v1/customers/top
GET /api/v1/inventory/low-stock

Requirements:

- JSON responses
- Input validation
- Appropriate HTTP status codes
- OpenAPI documentation
- Read-only analytical data access

### FR-07: MCP Server

Implement an MCP server exposing predefined tools:

- get_business_kpis
- get_top_products
- get_category_performance
- get_top_customers
- get_low_stock_products

Requirements:

- Read-only database access
- Validated tool arguments
- Structured tool responses
- No unrestricted SQL execution
- No access to unnecessary personal data

### FR-08: AI Agent Integration

Connect Claude Code to the MCP server.

The agent must be able to:

- Discover available tools.
- Select an appropriate tool.
- Execute tool calls.
- Interpret returned business data.
- Answer natural-language business questions.
- Avoid inventing unsupported metrics.

### FR-09: Automated Testing

Implement:

- Python unit tests
- API tests
- Database integration tests
- dbt data tests
- Ingestion idempotency tests
- MCP tool tests

Tests must be reproducible without depending
on the live external API.

### FR-10: Docker

- Create a reproducible Docker image.
- Install application dependencies.
- Support local container execution.
- Document database initialization.
- Support persistent warehouse storage.

### FR-11: CI/CD

Implement GitHub Actions workflows that:

Continuous Integration:

- Install dependencies.
- Initialize test data.
- Execute pytest.
- Execute dbt build.
- Build the Docker image.

Continuous Delivery:

- Publish the Docker image to GHCR
  after successful validation on the main branch.

### FR-12: Documentation

Provide:

- README.md
- Architecture diagram
- Setup instructions
- Data model documentation
- API usage examples
- MCP configuration instructions
- AI agent demonstration
- Known limitations
- Cloud migration considerations

## 6. Non-Functional Requirements

- Maintainability
- Modularity
- Reproducibility
- Idempotency
- Data integrity
- Secure, controlled data access
- Clear error handling
- Version-controlled implementation
- No paid external APIs or cloud services
- Windows-compatible local development

## 7. Acceptance Criteria

AC-01:
Ingestion successfully loads source data into DuckDB.

AC-02:
Repeated ingestion of the same source snapshot
does not create duplicate records.

AC-03:
dbt build completes successfully.

AC-04:
Bronze, Silver and Gold layers are available.

AC-05:
Business metrics are validated against test data.

AC-06:
REST endpoints return correct JSON responses.

AC-07:
MCP tools return validated business data.

AC-08:
Claude Code successfully answers business
questions using MCP tool calls.

AC-09:
All automated tests pass.

AC-10:
The Docker image builds and runs successfully.

AC-11:
GitHub Actions publishes the validated image
to GitHub Container Registry.

AC-12:
Another developer can reproduce the project
using the README instructions.

## 8. MVP Scope and Limitations

Included:

- Local analytical warehouse
- Batch ingestion
- Full-refresh data loading
- SQL-based transformations
- REST API
- MCP integration
- Automated testing
- Container image delivery

Out of scope for MVP:

- Real-time streaming
- Production cloud infrastructure
- Production authentication and authorization
- Distributed processing
- Production orchestration
- Historical change tracking
- Custom LLM training
- Automated deployment to production

Optional extensions:

- Incremental dbt models
- Scheduled ingestion
- Dashboard frontend
- Cloud warehouse migration

## 9. Cloud Portability

Document how the architecture can be adapted to:

- Google BigQuery
- Snowflake
- Databricks
- Microsoft Fabric

Consider:

- Warehouse adapters
- SQL dialect differences
- Storage architecture
- Authentication
- Orchestration
- Deployment

## 10. Development Methodology

Follow Spec-driven Development.

- Define requirements before implementation.
- Derive implementation tasks from this specification.
- Implement incrementally.
- Review AI-generated code.
- Test each component.
- Commit verified changes to Git.
- Document architectural decisions.
- Update the specification when requirements change.

## 11. Definition of Done

A feature is complete when:

- Its requirements are implemented.
- Relevant automated tests pass.
- Errors are handled appropriately.
- Documentation is updated.
- The implementation has been reviewed.
- Changes are committed to Git.

## 12. Approved Phase 7 extension · Integrated AI Business Assistant

The completed backend MVP and AC-01 through AC-12 retain their original scope. The no-paid-API requirement applies to that MVP. Phase 7 separately authorizes a native localhost assistant using the first-party Anthropic API and an estimated application budget of at most USD 2.00. Real paid requests require separate approval.

- **FR-13 · Assistant and tool grounding.** The React assistant calls local FastAPI chat routes. The backend uses the official Anthropic Messages SDK with Claude Haiku 5.5 and the official MCP stdio client. The agent discovers and validates the five approved read-only analytical tools. Tool calls go through MCP to the published Gold snapshot. The agent supports multiple tools per turn, reports execution outcomes, and provides snapshot and metric context when available. It explains unavailable historical or completed sales metrics. Synthetic cart value has no verified currency and represents neither revenue nor profit. Customer results contain IDs and aggregates.
- **FR-14 · Configuration and cost protection.** Load ignored backend-only dotenv configuration at runtime and default to disabled. Require loopback access and permitted hosts and browser origins. Never send secrets to the frontend or MCP child. Bound request rate, question and conversation length, tool results, timeouts, tool rounds, total Messages calls and model output. Disable SDK retries and prompt caching. Reserve estimated worst-case short-context cost before each call in a separate concurrency-safe persistent ledger. Retain uncertain reservations. Keep provider-side limits and prepaid credit protection independent of estimates.
- **FR-15 · Assistant experience and verification.** Provide accessible session-only chat, suggested questions, tool details, model and budget status, clear and pending states, and sanitized errors. Keep dashboard layout and existing read-only APIs functional. Automated validation uses mock provider responses and deterministic fixture data. Production integration and publication are outside this increment.

| ID | Phase 7 acceptance criterion |
| --- | --- |
| AC-13 | Native assistant discovers and uses approved MCP tools with deterministic fixtures in single-tool and multi-tool mocked conversations. Tool arguments, tool-use IDs and stop reasons are validated. |
| AC-14 | Chat is local-only and disabled by default. Invalid requests and failures produce sanitized responses. Token accounting, persistent reservations, concurrency and limits pass automated tests. |
| AC-15 | React sends a bounded conversation and safely displays answers, available snapshots, MCP execution outcomes, remaining budget and clear error and disabled states. Verify in Edge with the provider mocked. |
| AC-16 | A separately authorized live smoke test verifies first-party model access and one grounded analytical response. Record actual tokens and estimated cost. |

## 13. Approved Phase 8 extension · Production full-stack image

- **FR-16 · Single-origin packaging.** Build the React dashboard with pinned Node and `npm ci`. Run TypeScript checks and copy only the compiled dashboard into the non-root, hash-locked Python image. FastAPI serves the dashboard, assets, favicon, REST and documentation together. Native development still supports optional assets and the Vite proxy. Preserve the existing endpoint contracts and JSON API 404s.
- **FR-17 · Local container operation.** Publish only on host IPv4 loopback. Keep AI disabled by default, use runtime-only credentials, require a trusted bridge peer and same-origin browser metadata for paid chat, and preserve native access checks. Keep the validated warehouse readable through a read-only serving volume and use a separate persistent writable usage volume. Refresh remains an explicit maintenance operation with readers stopped. Supply a ledger migration procedure that retains the original and refuses to overwrite an existing destination.

| ID | Phase 8 acceptance criterion |
| --- | --- |
| AC-17 | A single non-root image serves the dashboard, compiled assets, favicon, existing analytics, Swagger and OpenAPI. Unknown API routes return JSON 404. Verify frontend traffic in Edge through the single published origin. |
| AC-18 | Explicit fixture refresh succeeds with dbt validation. Read-only warehouse and writable ledger volumes retain their state across container replacement. |
| AC-19 | AI defaults to disabled, the production chat boundary rejects an untrusted peer or origin, mocked enabled flows pass without paid requests, and the runtime image excludes local secrets and generated state. |

The previous MVP and Phase 7 acceptance evidence remains applicable. Hosted full-stack CI/CD and publication require a later approved increment.

## 14. Approved Phase 9 extension · Full-stack CI/CD

- **FR-18 · Full-stack validation.** Pull requests and main pushes run fixture dbt and hash-locked Python tests on Windows and Linux, plus an independent lockfile-based Node build and frontend tests. A dependent job builds the production image once, tests it with container networking disabled for pytest, and verifies serving and persistence using temporary Compose resources. Clean up those resources after failure or success. Automated AI tests use mocked Anthropic responses and no real credentials.
- **FR-19 · Exact-image delivery.** Only successful main pushes with `GHCR_APPROVED_SHA` matching the workflow commit may publish. Transfer only the validated image archive, its checksum and image ID. Verify the archive, reloaded image ID and revision before pushing the same image to a commit-SHA tag. Only the publish job may write packages. Exclude secrets, warehouses and usage ledgers from every release artifact.

| ID | Phase 9 acceptance criterion |
| --- | --- |
| AC-20 | The full-stack workflow passes for the reviewed commit on GitHub. Local workflow lint and fixture smoke runs establish reproducibility but do not establish hosted success. |
| AC-21 | An owner-approved main push publishes the exact validated full-stack image and a registry pull matches the reported digest. An unapproved SHA does not publish. |
