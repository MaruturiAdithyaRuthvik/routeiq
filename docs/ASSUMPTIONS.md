# Assumptions

- `docs/PROBLEM_STATEMENT.md` was not present when scaffolding began, so its acceptance criteria could not be read. Until it is supplied, the explicit RouteIQ constitution in `AGENTS.md` and `.github/copilot-instructions.md` is the available product and engineering baseline. Reconcile this assumption against the problem statement before implementing product behavior.
- `docs/BUSINESS_RULES.md` was also not present. Rule-specific docstrings and tests must cite its rule IDs once that document is added; no rule IDs or business rules are inferred here.
- The root `Makefile` targets are intentionally placeholders because no implementation commands or application code exist yet.
- `.env.example` contains local development connection settings and fixed reproducibility values only; replace the sample database credentials for any non-local deployment.
