# IBRD matched-project extension

This folder reproduces the separate FY2024–FY2025 IBRD application in manuscript Sections 3.7 and 4.7, Table 4 and Appendix C. It does not modify the original EIB, EBRD or NIB results. The EIB worked bridge appears in Appendix E, Table E4.

## Run from package root

Use the pinned original environment plus `pip install -r ibrd/requirements.txt` (Python 3.12.14 used).

```
python ibrd/acquire_sources.py
python ibrd/extract_ibrd.py
python ibrd/analyze_ibrd.py
python ibrd/audit_outcomes.py
python ibrd/validate_extraction.py
python ibrd/validate_analysis.py
```

PDF extraction may take several minutes. `acquire_sources.py` verifies the exact source hashes and refuses a different source edition. Six PDFs are retrieved from official World Bank sources. The source PDFs and complete extracted descriptions are not redistributed. `extract_ibrd.py` creates data/project_records.csv, data/source_totals.csv and data/cell_provenance.json locally. The last file preserves each audited page and cell bounding box.

`audit_outcomes.py` reruns the production calculations on import and adds three document-trace checks and the exploratory exclusion of P154283. No source value is silently corrected. `validate_analysis.py` uses independent subset-weight Shapley calculations, not production imports. `validate_extraction.py` uses pdfplumber, distinct from the PyMuPDF production reader, for every numeric field and project identifier. One crop carries an adjacent hyphen; exact unique P-code tokens are compared for identifiers. Numerical text is compared after whitespace normalization.

## Sample and estimand

There are 146 FY24 and 161 FY25 listed project rows. All 146 FY24 link identifiers occur in FY25. Four FY24 link/description ID conflicts are excluded conservatively, leaving 142 unambiguous pairs; 77 have numeric GHG at both endpoints, 69 also have positive eligible commitment and allocation, and 65 retain status (38 active, 27 closed). Empty/dash GHG is not zero. The twelve source-listed fully repaid projects are flagged from the FY25 note rather than inferred from row disappearance.

The primary construct is an allocation-weighted mean of whole-project reported annual GHG divided by green-bond eligible committed USD million. It is not physical financed impact, an issuer-published intensity, or the EIB project-cost indicator. Reported bank shares do not justify deriving an exact historical project cost from mixed-vintage, rounded financing fields. Cost, cancellation, eligibility and FX effects are not separately identified inside commitment updates. A separate share-adjusted sensitivity is explicitly an analyst construction.

Source FY24 finance values are USD million to one decimal place. FY25 column headings and the main-report commitment sum support USD units, although the annex note retains contradictory millions wording. FY25 sum = USD 25,577.207887 million, rounding to main-report page 43 total 25,577. Gross listed allocations are not the report's net outstanding balance; no forced reconciliation is performed. Six FY24 total comparisons fall within source rounding.

The primary same-status cohort's GHG inputs are identical at common whole-tonne precision. That does not establish unchanged physical outcomes. Both report labels are vintages; FY25 notes use completion reports available by January 2026. The four active-to-closed transitions are reported separately; the primary excludes them by design, not because of their result direction. The source-disclosed GHG drop in the 69-project comparison is not a calendar-year performance estimate.

## Exploratory project-document tracing

- P131256: IEG p. 8 matches 900,774 tonnes/year against target 1,270,000; closure June 2024.
- P160408: IEG p. 7 matches 1,382,000 estimated tonnes/year; its end target 4,789,515 differs from the FY24 annex value 5,661,643.6.
- P154283: IEG p. 6 states 8,892 and 7,465 **thousand** tonnes/year, while annex columns say tonnes/year. This factor-1000 unit conflict is preserved. The project is already excluded from the primary as a status transition. The broader 68-project exclusion sensitivity is exploratory.
- P132741: the initial trace remains in outcome_trace.csv as a historical result. The current ibrd_deep audit locates 32,000 in a September 2023 interim ISR; this is not completion verification.

## Output map

- Table 4: results/matched_results.csv
- Primary and subgroup exact bridges: results/matched_decomposition.csv
- Sample selection/coverage: sample_flow_project_level.csv; sample_coverage.csv
- Influence checks: leave_one_project_out.csv; leave_one_country_out.csv
- Appendix C: identity_conflicts.csv; status_transitions.csv; outcome_trace.csv
- Source totals and unit-conflict sensitivity: source_reconciliation.csv; unit_conflict_sensitivity.csv
- Validation: extraction_validation.json (1,842 field matches), analysis_validation.json (735 checks)
- summary.json: compact primary results

The DOI literature and original EIB analyses are unchanged. `DESIGN.txt` records the pre-calculation internal design; it is not a preregistration. Source identity and mathematical checks are not independent environmental validation. Source license/terms continue to apply to downloaded files. Original code and derived diagnostics are included for review and replication.
