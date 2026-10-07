EIB REPORTING-COMPARABILITY ANALYSIS
Version: 7 October 2026. Python 3.12.14.

Purpose
A source-audited descriptive analysis of reported, expected GHG intensity in final EIB Climate Awareness Bond (CAB) impact workbooks for report years 2022–2024. The principal comparison is 2023–2024. The 2022 extension is a separate cost-vintage sensitivity. This is not an estimate of realized emissions, a causal financing effect, or a universal investment-effectiveness ranking.

Reproduction
1. Install the versions in requirements.txt in an appropriate Python environment.
2. Obtain the official original source editions, using python code/acquire_sources.py --source-dir sources, or place matching manually downloaded workbooks in that folder. The acquisition script verifies the exact audited SHA256; changed editions and non-workbook downloads fail rather than silently replacing the sources. Official URLs and hashes are also in code/extract.py.
3. Run python code/run_analysis.py --source-dir sources. Outputs are rebuilt under data/, results/ and figures/; no workbook is edited or recalculated.
4. Run EIB_SOURCE_DIR=sources python tests/test_analysis.py. The tests include independent openpyxl import of every financial/GHG value checked against the standalone OOXML extraction, decimal summary arithmetic, exact identity tests, hidden-merge handling, stream deduplication, genuine zeros and positive values, and source integrity.
5. Reproduce.ipynb is an optional notebook wrapper for the same complete workflow.

The run_analysis.py default is the sources/ directory relative to the analysis root; --source-dir can point to another read-only source directory. All regeneration paths are relative to the analysis root unless explicitly supplied by the caller. Source extraction uses Python standard-library OOXML parsing. openpyxl is used independently only in tests. Original drawing-format warnings from openpyxl do not affect read-only cell values and no source file is saved.

Files
- LOCKED_DESIGN.txt: design fixed before new results, including subsequent scope precautions.
- code/extract.py: merge-aware OOXML extraction, source manifest, literal/semantic status handling.
- code/run_analysis.py: estimands, exact decompositions, deterministic sensitivities and four Matplotlib figures.
- code/acquire_sources.py: exact-vintage acquisition with fail-closed integrity checks.
- tests/test_analysis.py: sixteen tests; results/test_stdout.txt records execution.
- RESULTS_AND_METHODS.txt: equations, findings, interpretation and limitations for manuscript use.
- FIGURE_CAPTIONS.txt: figures and mandatory interpretive qualifications.
- results/table1_coverage_and_intensities.csv: finance coverage, reconstructed and published aggregate measures.
- results/table2_exact_decomposition.csv: exact numeric-set and matched-panel decompositions, both cost bases and both GHG metrics.
- results/table3_sector_profiles.csv: main eligible-activity macro-sector grouping, not a claim about the sectoral boundary of whole-project GHG.
- results/table4_deterministic_sensitivities.csv: ten selected populations and cost/weight controls. Comparisons target different estimands; they are not alternative estimates of one latent total impact.
- results/fixed_cohort_scope_controls.csv: main residual-comparability evidence, 2023-, 2024- and symmetric-reference weights.
- results/deterministic_sensitivities_all.csv: complete deterministic alternatives.
- results/input_revision_and_membership_counts.csv: source-input changes at absolute tolerance 1e-8, numeric availability transitions and membership counts.
- results/coverage_convention_bridges.csv: fixed-allocation-rule coverage decomposition and benchmark-specific published-trend wedges.
- results/published_rule_shapley_bridge.csv: supplementary order-averaged bridge of conditional intensity, finance coverage and reconstructed denominator rule. It cannot be stacked unscaled with a lower-level intensity decomposition.
- results/matched_panel_results.csv and balanced_three_year_panel.csv: selected-cohort finance and fixed-weight comparisons.
- results/concentration.csv and sector_exact_decomposition.csv: deterministic contribution concentration and main-activity mix.
- results/missing_intensity_scenarios.csv and missing_intensity_tipping_points.csv: assumed missing-intensity scenarios, not physical bounds, forecasts, confidence intervals, or imputed estimates.
- results/duplicate_stream_ghg_precision_sensitivity.csv: duplicate Normandie GHG precision sensitivity using CAB- versus EuGBS-priority values.
- data/project_report_stream_rows.csv: internal analytic row file, 475 records = 461 CAB plus 14 EuGBS. Numeric fields without _raw suffix are merge-aware; raw payloads must never override semantic missingness.
- data/source_notes.csv: source method wording with workbook sheet and cell references.
- data/hidden_merged_payloads.csv: twelve concealed subordinate zero payloads explicitly excluded from numeric GHG.
- data/combined_2024_project_boundary_sensitivity.csv: unique-project boundary reconstruction for whole-cost sensitivity only. Its retained eligible_pct is not a combined eligibility variable and must not be used for an eligible-cost combined calculation.
- results/project_exact_decompositions.csv, project_contributions.csv, project_membership_transitions.csv, leave_one_project_out.csv and combined_boundary_matched_decomposition.csv: detailed internal audit rows.

Disclosure, denominator and unit discipline
Relative GHG retains the source sign: negative means reported reduction/avoidance relative to a counterfactual baseline; positive means additional expected emissions. GHG is ktCO2e/year in the workbook. Intensity multiplies it by 1000 and divides by EUR-million project cost. It is an allocation-weighted project-cost-normalized reporting statistic. Allocation itself is not the intensity denominator and this is not tonnes per euro of financed causal abatement. Annual GHG figures are generally long-term expected averages, not metered reporting-year outcomes.

When eligible percentage is below 100, source GHG is whole-project while eligible cost concerns eligible components. The reconstruction follows disclosed labels; it does not prove physical scope alignment. Whole-project G/C and 100%-eligible restrictions provide scope checks. Even whole-cost alignment does not guarantee identical absolute/relative GHG boundaries or lifecycle coverage. Do not infer a physical baseline as absolute minus relative GHG without proving boundary equality.

The all-allocation ratio retains the numeric numerator and the entire allocation denominator. Its missing-record numerator is unavailable, not physically zero. The observed ratio conditions on a changing, nonrandomly disclosed set. A constant denominator rule is not a constant project population. Matched cohorts also select projects; they do not fix nonrandom selection or establish representative changes.

Cost, eligibility and allocation factors can be economically linked, particularly under the retrospective CAB/EuGBS partition. Shapley values allocate an arithmetic change symmetrically, not independently manipulable or causal effects. EIB approved financing share (L), signed loan (M), economic life (N), eligible fraction (O) and annual allocation (R) are distinct; L and M are not substituted for C in the primary analysis. Multiplying annual GHG by lifetime is not authorized by this analysis.

2024 combined-stream sensitivity
One project, Normandie, occurs in both streams. Whole-project GHG and cost are counted once; annual allocations are added. Relative GHG is identical in both records; absolute differs 15.2 versus 15.0 kt/year, so both disclosed precision choices are evaluated. No combined eligible-cost intensity is produced. Seven apparent 2023-CAB exits are reported in 2024 EuGBS. Adding that stream and deduplicating known shared projects is a boundary sensitivity; it does not prove a fully harmonized pre-/post-regulation investment universe or explain all report entry and exit. The final 2024 report includes retrospective allocation reconciliation after an April 2025 issue. These are ex-post report-edition comparisons, not contemporaneous calendar-2024 investor information sets.

Missingness and inference
Below-threshold, deferred intermediary/framework, not-applicable, clarification nondisclosure and external-review withholding are retained separately. A common statistical censoring bound is not assumed. Census summaries have no sampling p-values, bootstrap confidence intervals or superpopulation standard errors. Leave-one-out ranges and scenario grids describe deterministic sensitivity, not probability.

Source rights and conservative distribution
Public accessibility is not an open-data licence. EIB retains copyright; no reusable open licence was verified in these workbooks. Do not package or publicly upload source XLSX/PDF, source screenshots, full source-text extracts or project-level row data without permission. A conservative replication bundle contains original code, acquisition instructions, source URLs/hashes, environment/tests, derived aggregate outputs and original figures. The full internal workspace retains read-only-source-derived audit detail for this authorized analysis. No EIB originals are copied into this analysis directory and nothing has been publicly uploaded.

Known unresolved issue
The 2022 absolute summary is 35.2164758522, while the audited disclosed numerator divided by all allocations gives 35.2322196814, a residual of −0.0157438292. This is preserved, not forced to reconcile. The 2022 relative summary matches the all-allocation calculation. Its non-intermediated heading and initial-versus-current cost definition limit its role in longitudinal claims. No preparer intention, misconduct, error or hidden policy is inferred from numerical matches or residuals.

Portable bundle verification
The conservative ZIP excludes original source files, source screenshots, full source-text extracts, every project-level data/audit output, caches and independent-review working files. The analysis script regenerates project-level audit files locally after exact sources are acquired; that regeneration does not authorize redistribution. LICENSE_CODE.txt licenses only original code under code/ and tests/, not EIB sources or their data. The environment.yml file is a proposed pinned Conda recipe; it was defined but was not created or executed. The successful runtime is the installed Python 3.12.14 environment recorded in VALIDATION_SUMMARY.txt.

Run python code/verify_bundle.py to verify every distributed file against CHECKSUMS.sha256. After acquiring sources and regenerating outputs, run python code/verify_bundle.py --sources --outputs. The source switch checks the original workbook hashes. The output switch checks reproducible aggregate CSV and PNG checksums; PDF creation timestamps are suppressed for deterministic rendering; explicit expected-output checks cover CSV and PNG, while all shipped PDFs remain covered by the distributed-artifact manifest. A mismatch requires investigation, not automatic baseline replacement. Rendering hashes may depend on the font/runtime platform even when CSVs are numerically unchanged.
