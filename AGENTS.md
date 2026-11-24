# Project instructions for coding assistants

- Treat [SPEC.md](SPEC.md) as the source of truth for project requirements and acceptance criteria. Use [PLAN.md](PLAN.md) as the implementation roadmap and trace changes to the relevant requirement and acceptance IDs.
- Implement only the phase the owner has authorized. Before editing, explain the proposed changes, the affected components, and how you will verify them.
- Keep the architecture simple and modular. Reuse the shared query services for FastAPI and MCP, and add abstractions only when they solve a concrete problem.
- Use type hints for Python interfaces and parameterized SQL for query values. Keep business metric calculations in dbt so both delivery adapters expose the same definitions.
- Never expose secrets or raw customer data through responses, logs, examples, fixtures, or version control. Keep raw source records confined to local Bronze storage. Customer-facing results contain only customer IDs and aggregate metrics.
- Use deterministic synthetic fixtures and keep automated tests independent of live APIs. Run the live DummyJSON smoke test separately.
- Verify each implementation increment using the relevant checks in PLAN.md. Report the results and any verification that remains outstanding.
- Raise ambiguities or conflicts before changing business behavior. Obtain explicit approval before changing requirements and document approved changes in SPEC.md and PLAN.md.
- Obtain explicit approval before committing or pushing. Repository visibility, the GHCR namespace, and publication require explicit owner approval.
- Write project documentation in English. Explain generated code and architectural decisions for a developer learning Data and AI Engineering. Describe how data flows through the affected layers, why the design fits the requirement, and what the verification demonstrates.
