CROSS-ISSUER DIAGNOSTIC EXTENSION
Analysis completed 7 October 2026. The current manuscript presents these diagnostics in Appendix E, Tables E2 and E3.

Run from package root with the original requirements plus pyxlsb==1.0.10:
 python extension/acquire_sources.py
 python extension/analyze_ebrd.py
 python extension/analyze_nib.py
 python extension/validate_extension.py

EBRD: YE2023 XLSB and YE2024/YE2025 XLSX. Sections 7.1 and 7.2 only; renewable energy and energy efficiency, excluding GEFFs. Sources are ex-ante portfolio-level disclosures. Analyst ratios use reported portfolio EUR million, not EIB project cost or bond issuance. Full-project and attributed numerators are positive reductions; no direct level comparison with EIB's signed relative GHG intensity is valid. Country groups include <REGIONAL>; they are not project cohorts. Effective attribution is an aggregate ratio, not a causal policy or a representative financing share.
NIB: December 2025 snapshot of the old framework portfolio, historically allocated to August 2024. It is not a 2011–2025 time series. The hierarchy audit preserves published values and reports non-overlapping alternatives. It is not an issuer-confirmed restatement or a physical impact validation.

Source exceptions: EBRD 2024 category counts sum to 195, while the general total is 194. Financial and GHG sums reconcile. Possible category overlap cannot be resolved without identifiers. NIB totals include the renewable-energy parent and its exhaustive children, verified against expanded shared formulas and cached values. No forced corrections were applied.

EIB 2025: publication page discovered but workbook not obtained. No 2025 EIB observations or results were fabricated. EBRD 2023 and the NIB diagnostic are exploratory extensions after initial source inspection; this work was not publicly preregistered. See EXTENSION_DESIGN.txt.

Source workbooks, wholesale project extracts, webpage mirrors and source screenshots are excluded from redistribution. Fetch fixed versions from official URLs in source_manifest.json. Derived aggregate results, code and validation are included. These selected issuer cases establish existence, not prevalence or an equivalent multi-issuer project panel.

Original EIB work remains in code/, tests/, results/ and figures/. Its outputs are unchanged.
