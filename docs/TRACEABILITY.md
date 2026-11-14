# Problem-statement traceability

| Requirement | Implementing file/command |
|---|---|
| Step 1: field-level entity dictionary | [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md), `data/schema/` |
| Step 2: master-before-dependent generation | `backend/app/datagen/master.py`, `leave.py`, `expenses.py`, `pipeline.py` |
| Step 3: deterministic IDs and cross-file consistency | `backend/app/engine/ids.py`, `backend/app/datagen/helpers.py` |
| Step 4: full/starter volumes and scenarios | `backend/app/datagen/context.py`, `make generate` |
| Step 5: clean baseline then labeled anomalies | `backend/app/datagen/pipeline.py`, `anomalies.py`, `data/ground_truth/` |
| Step 6: derived amounts, balances, statuses, paths | `backend/app/engine/`, `backend/app/datagen/` |
| Step 7: isolated expected decisions and anomaly labels | `data/ground_truth/ground_truth.json` and CSVs |
| Step 8: keys, joins, arithmetic, lifecycle and duplicates | `make validate`, `backend/app/datagen/validation.py` |
| Step 9: CSV/JSON/SQL, docs, manifest and reports | `make generate`, `backend/app/datagen/export.py` |
| Step 10: deterministic regeneration | `make repro`, `scripts/repro.py` |
| Leave/expense routing and documented exception paths | [`BUSINESS_RULES.md`](BUSINESS_RULES.md), `backend/app/engine/` |
| Core entities and cardinalities | [`ERD.md`](ERD.md), [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) |
| IDs: EMP/LVE/EXP/EXPL/APR/RMB | `backend/app/engine/ids.py`, `backend/app/datagen/validation.py` |
| Evaluation focus: realism, coverage, provenance | `data/SOURCE_MANIFEST.json`, `data/validation_summary.*`, `README.md` |
