# Carbon Impact Comparability in Green Bond Finance

Replication materials aligned with the manuscript revision of 8 October 2026.

## Scope

This repository contains a descriptive accounting analysis of carbon impact comparability in green bond finance. It combines EIB project disclosures for 2022–2024 (primary comparison: 2023–2024), matched IBRD project disclosures for fiscal 2024–2025, EBRD category diagnostics for 2023–2025, and a NIB December 2025 hierarchy audit. These cases use distinct financial and emissions boundaries and are not pooled into a common efficiency ranking.

The original EIB numerical results and figures are retained. The additional modules provide IBRD matching, documentary outcome checks, historical project-cost controls and complementary EBRD/NIB diagnostics. The manuscript contains five main tables; supporting comparisons appear in Appendix E. `MANUSCRIPT_MAP.csv` gives the current mapping. Historical numerical output filenames have been retained for reproducibility.

## Main findings and interpretation

- Among 48 continuing EIB projects, whole-project-cost intensity declines by 42.18% with annual allocation weights, compared with 0.25% with earlier weights fixed. This distinction separates financing composition from revisions to continuing-project inputs.
- The original 65-project IBRD comparison gives a 2.48% decline. Joint exclusion of seven projects with measurement-basis concerns leaves 58 projects and a +0.016% change. The 38 active projects were outside the completion audit; the remaining cohort is not fully outcome-verified.
- The completion-document audit covers 31 projects. Historical total costs are accepted for 22; ten also meet the strict annual outcome definition. Their change is +0.015963%, with allocation-rounding bounds of −0.006134% to +0.038065%. The bounds span zero and are not confidence intervals.
- The expanded 15-project cost cohort includes documented lifetime averages and component reconstructions. Its −0.207916% change must remain separate from the strict annual cohort. Fixed-weight changes are mechanically zero when both outcome inputs and reference costs are constant.
- EBRD trend direction depends on financing attribution, while NIB category hierarchy affects aggregation. These diagnostics do not establish environmental deterioration, causality or reporting misconduct.

Historical completion costs are a common reference denominator applied to both reporting vintages. They are not two observed annual cost series and have not been deflated to a common price year. Documentary agreement does not validate counterfactual emissions or financing additionality.

## Folder guide

| Folder | Contents |
| --- | --- |
| `code/`, `tests/`, `results/`, `figures/` | Original EIB analysis, validation and derived outputs |
| `extension/` | EBRD attribution and NIB hierarchy diagnostics |
| `ibrd/` | Matched IBRD FY2024–FY2025 analysis and initial document tracing |
| `ibrd_deep/` | Historical cost audit, outcome adjudication and rounding/flag sensitivities |

`README.txt` documents the original EIB method in greater detail. Module guides explain their sample definitions and limits. `DESIGN.txt` and related design records document sequential analytical decisions; they are not public preregistrations.

## Reproduction

Use Python 3.12 with the pinned requirements. The recorded analysis runtime was Python 3.12.14. Run commands from the repository root. The Conda recipe is provided as a recipe only; a fresh Conda environment was not executed during the recorded validation.

```bash
python -m pip install -r requirements.txt -r extension/requirements.txt -r ibrd/requirements.txt -r ibrd_deep/requirements.txt

# Check distributed files before regenerating outputs.
python code/verify_bundle.py

# EIB
python code/acquire_sources.py --source-dir sources
python code/run_analysis.py --source-dir sources
python tests/test_analysis.py
python tests/test_independent_shapley.py
python code/verify_bundle.py --sources --outputs

# EBRD and NIB
python extension/acquire_sources.py
python extension/analyze_ebrd.py
python extension/analyze_nib.py
python extension/validate_extension.py

# IBRD matched projects: creates local ibrd/data/project_records.csv.
python ibrd/acquire_sources.py
python ibrd/extract_ibrd.py
python ibrd/analyze_ibrd.py
python ibrd/audit_outcomes.py
python ibrd/validate_extraction.py
python ibrd/validate_analysis.py

# IBRD cost and outcome audit: requires the preceding IBRD inputs.
python ibrd_deep/acquire_sources.py
python ibrd_deep/build_audit.py
python ibrd_deep/analyze_cost.py
python ibrd_deep/rounding_bounds.py
python ibrd_deep/validate_cost_audit.py
```

Acquisition scripts fetch official sources and require exact SHA256 identities. A changed source edition must be investigated; expected hashes must not be silently replaced. Source workbooks/PDFs and complete extracted descriptions are acquired or regenerated locally. They are not included in this repository update. Figure hashes can depend on the rendering platform even when numerical outputs agree.

## Manuscript mapping

| Manuscript item | Repository files | Selection or scope |
| --- | --- | --- |
| Table 1 | results/table1_coverage_and_intensities.csv | EIB coverage and aggregate conventions |
| Table 2 | results/table2_exact_decomposition.csv | Select 2023–2024 relative-GHG population and cost basis |
| Table 3 | results/fixed_cohort_scope_controls.csv | Matched CAB and combined-stream cohorts |
| Table 4 | ibrd/results/matched_results.csv | IBRD FY2024–FY2025 matched comparisons |
| Table 5 | ibrd_deep/results/cost_results.csv; ibrd_deep/results/flag_exclusion_sensitivity.csv | IBRD historical cost and outcome-basis controls |
| Table E1 | results/deterministic_sensitivities_all.csv | EIB population and scope sensitivities |
| Table E2 | extension/results/ebrd_category.csv | EBRD category/year diagnostics |
| Table E3 | extension/results/nib_hierarchy_audit.csv | NIB hierarchy reconciliation |
| Table E4 | results/published_rule_shapley_bridge.csv | Select the 2023_2024 reconciliation |
| Figure 1 | figures/figure1_conventions.png | EIB aggregate conventions |
| Figure 2 | figures/figure2_decomposition.png | EIB observed-set attribution |
| Figure 3 | figures/figure3_coverage.png | EIB disclosure coverage |
| Figure 4 | figures/figure4_sensitivity.png | EIB alternative comparisons |
| Table A1 | README.md; MANUSCRIPT_MAP.csv | EIB execution/output map |
| Table B1 | extension/README.txt | EBRD/NIB output map |
| Table C1 | ibrd/results/status_transitions.csv; ibrd/results/outcome_trace.csv; ibrd_deep/results/audit_ledger.csv | Transition traces; current audit supersedes the earlier unresolved P132741 trace |
| Table D1 | ibrd_deep/results/audit_ledger.csv | Outcome-basis classification across the 31-project audit |

## Validation records

The distributed records document 16 EIB unit tests and an independent subset-formula check across 760 project/model records; 38 extension checks; IBRD agreement across 1,842 extracted fields and 735 analysis checks; and 307 cost/outcome checks, including 53 independently parsed cost/outcome locators. The prior packaged cost-module rerun matched its reviewed outputs using already acquired, hash-verified sources and regenerated IBRD inputs. These records establish extraction and calculation checks, not independent validation of physical environmental outcomes.

This October 8 update changes documentation and manuscript mapping. Analytical scripts and result files are preserved from the reviewed package. It does not claim a new end-to-end acquisition run. Root `CHECKSUMS.sha256` covers the complete update, while module checksum files cover their folders. `BUNDLE_MANIFEST.json` inventories distributed files and their scope.

## Source scope and rights

The update includes original code, derived diagnostics, a minimal 31-project audit index, source locators, metadata and adjudication records. It excludes original issuer workbooks/PDFs, screenshots and full extracted project-description tables. Third-party source rights remain with their respective holders. The existing `LICENSE_CODE.txt` applies to the original `code/` and `tests/` directories; this update does not extend that licence to third-party sources or other materials.
