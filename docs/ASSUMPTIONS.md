# Assumptions

- `docs/BUSINESS_RULES.md` is not present. Rule-specific docstrings and tests must cite its rule IDs once that document is added; no rule IDs or business rules are inferred here.
- The root `Makefile` targets are intentionally placeholders because no implementation commands or application code exist yet.
- `.env.example` contains local development connection settings and fixed reproducibility values only; replace the sample database credentials for any non-local deployment.
- The constitution requires generated scenario and transaction data to remain synthetic. Although external data is optional in the problem statement, this project will not incorporate external records into generated datasets; any public references used only for schema inspiration must meet the problem statement's lawful-use and provenance requirements.
