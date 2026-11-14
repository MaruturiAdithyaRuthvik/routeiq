# Assumptions

- `docs/PROBLEM_STATEMENT.md` became available after the initial repository inspection and was reviewed in full. Its detailed entity, data-generation, edge-case, validation, export, and reproducibility criteria are project acceptance criteria; this commit is limited to the requested project constitution and scaffolding, not an implementation of those behaviors.
- `docs/BUSINESS_RULES.md` is not present. Rule-specific docstrings and tests must cite its rule IDs once that document is added; no rule IDs or business rules are inferred here.
- The root `Makefile` targets are intentionally placeholders because no implementation commands or application code exist yet.
- `.env.example` contains local development connection settings and fixed reproducibility values only; replace the sample database credentials for any non-local deployment.
