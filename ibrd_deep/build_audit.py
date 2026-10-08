from pathlib import Path
import json,csv,hashlib
R=Path(__file__).resolve().parent
# Manually adjudicated source fields. Every positive cost has an explicit page and numeric token.
# pid|cost USDm|source|page|token|appraisal USDm|appraisal token|cost interpretation
cost_text='''P084874|1440|IEG|4|1,440|593.6|593.6|Whole-project cost including additional financing; original appraisal scope smaller.
P095114|697.5|IEG|1|697.5|670|670.00|Whole-project appraisal and actual costs in legacy IEG table.
P096556|439.8|IEG|1|439.8|439.8|439.8|Whole-project costs include cofinancing.
P101988|344|IEG|1|344|319|319|Whole-project costs include navigation hydropower and flood protection.
P106261|358.215766|ICR|6|358,215,766|218.35|218,350,000|Whole-project financing table includes original and additional financing; component tables confirm combined scope.
P107159|357.34|ICR|51|357.34|2694|2694|Component-cost annex includes leveraged investment; reject 114.039027 datasheet bank-only amount.
P107992|13.8|IEG|3|13.8|9.4|9.4|Whole-project cost including front-end fees and additional financing; reported USD equivalent.
P110371|318.67|IEG|3|318.67|346.8|346.8|Whole-project cost includes national state and city contributions.
P112578|3097.07|ICR|45|3,097.07|1150|1,150.00|Explicit total project costs excluding 2.49 front-end fee; 3099.56 is total financing required.
P113078|622.7|IEG|3|622.7|581.65|581.65|Whole-project final cost including borrower contribution and CTF.
P120664|468.8|IEG|2|468.8|343.1|343.1|Narrative whole-project actual cost includes added activities financing charges and working capital; ignore stale cover field.
P122178|281.97|IEG|3|281.97|305.89|305.89|Whole-project actual cost; 268.4 in economic analysis refers to a narrower investment basis.
P127775|155.35|IEG|3|155.35|213.4|213.4|Whole-project final cost after reduction in component scope.
P144489|2128.611786|ICR|6|2,128,611,786|||Whole-project actual total including all financiers; original appraisal table differs in treatment of additional finance.
P146194|87.7|IEG|2|87.7|||Actual whole-project cost; no borrower contribution.
P147760|57.26|IEG|3|57.26|57.85|57.85|Whole-project actual cost includes additional financing; original label includes expanded financing basis.
P148129|144.77|IEG|4|144.77|224.27|224.27|Whole-project actual cost includes borrower contribution.
P148527|347.84|IEG|2|347.84|536.8|536.80|Whole-project actual cost after component cancellations and currency changes.
P149872|72.1|IEG|4|72.10|156|156.00|Whole-project actual cost; original and revised scope differ.
P150930|170.85|IEG|3|170.85|187.5|187.5|Whole-project actual cost includes taxes and on-farm subsidies.
P164047|683.449742|ICR|6|683,449,742|686|686,000,000|Whole-program actual cost includes 536m borrower contribution.
P132873|114.075042|ICR|6|114,075,042|150.78|150,780,000|Whole-project actual cost includes borrower contribution.'''
costs={}
for line in cost_text.splitlines():
 p,c,typ,pg,tok,a,atok,n=line.split('|');costs[p]=dict(cost_usd_m=float(c),cost_file=f'{p}_{typ}.pdf',cost_pdf_page=int(pg),cost_token=tok,appraisal_cost_usd_m=float(a) if a else None,appraisal_token=atok,cost_note=n)
# Primary strict annual verification requires explicit annual basis and value agreement; arithmetic/lifetime averages form a separate class.
ghg_text='''P146194|annualized_lifetime|ICR|38|3,081,517|3081517|20|Lifetime total divided by explicitly stated 20-year life (ICR p21); 154075.85 rounds to 154076. Average not observed annual flow.
P154669|unit_ambiguity|ICR|44|2,876,006|2876006||Result number matches but indicator/unit says thousand tons while displayed value is already millions; no silent conversion.
P096556|annual_direct|ICR|27|785,000|785000|1|Explicit average annual estimate based on CDM pilot experience; not direct measurement of every household.
P084874|annual_direct|IEG|8|6.51|6510000|1|Explicit estimated annual GHG reductions in million tonnes; covers expanded project.
P101988|annual_direct|ICR|7|220,000|220000|1|Carbon reduction associated with 2013 hydropower output; annual observation from historical completion period.
P120664|unresolved_value|IEG|4|22.59|||Per-floor-area annual indicator verified but annex aggregate 415500 not reproduced from inspected completion documents.
P154283|unit_conflict|ICR|28|7,465|7465000|1|ICR and IEG explicitly thousand tonnes/year; annex displays 7465 under tonnes/year. Transition excluded.
P095114|unresolved_value|ICR|20|14 million|||Approximately 14m over 2014-2024 disclosed; annex 1407700 annual value not independently reconstructed.
P113078|annual_direct|ICR|20|1,010,125|1010125|1|Explicit ton/year estimate; results framework says calculated over 12 months to December 2018.
P149872|annualized_lifetime|ICR|22|189,682|189682|8|ICR explicitly states 8-year lifetime for actual subprojects; dividing gives 23710.25 rounding to annex value. Updated 15-year scenario kept separate.
P106261|horizon_conflict|IEG|9|6,021,967|6021967||ICR/IEG cumulative reductions from installation through reporting period; dividing by annex 10-year life reproduces number but does not establish annual flow.
P132443|annual_direct|ICR|18|55,850|55850|1|ICR distinguishes annual 55850 from lifetime 1675500; IEG conflates labels. Annual field resolved through ICR.
P107992|annualized_lifetime|IEG|6|41,504|41504|15|Lifetime emissions divided by 15-year investment life in IEG p11; 2766.93 rounds to annex value.
P131256|annual_direct|ICR|27|900,774|900774|1|January 2024 completion estimate and 1270000 target; transition not calendar-year deterioration.
P104266|horizon_conflict|ICR|7|205.84|205840||Explicit cumulative indicator in ktCO2; annex treats same numeric total in tonnes as annual. No annualization justified.
P112578|annual_components|ICR|34|1,746|3214000|1|Separate RE 1746 and EE 1468 thousand-tonne potentials sum to 3214000; annual energy/emission-factor interpretation, kept outside strict explicit-annual cohort.
P122178|annual_direct|ICR|18|397,796|397796|1|Explicit tons CO2e/year from subprojects; IEG rounded to about 400000.
P132741|interim_annual|ISR|4|32,000|32000|1|September 2023 ISR reports current 32000 and target 115840; no completion report retrieved. Value traced to interim reporting only.
P096586|approximate_period_average|ICR|28|8,561.00|8561000|10|ICR reports 8561 thousand tonnes over ten years, implying 856100 per year versus annex 856097. Close agreement within accumulated component rounding; no current-year measured flow established.
P148129|annual_direct|ICR|20|34,281|34281|1|Explicit modelled tCO2e/year; ICR p61 notes a revised estimate after economic analysis.
P148527|annual_components|ICR|50|1,831|17681|1|1831 tonnes for buses plus more than 15850 for motor vehicle trips in 2020; approximate component reconstruction.
P144489|annual_direct|ICR|18|64,056|64056|1|Explicit ex-post estimate for year 2024 against no-project scenario; not simply measured emissions.
P110371|horizon_conflict|ICR|35|312,000|312000||Indicator explicitly forecast cumulative CO2 over ten years; annex repeats total under annual heading.
P131765|unresolved_scope|ICR|37|9.6 million|||Completion report pools three corridors and estimates 9.6m over 2010-2045; phase-II annual 274286 not independently matched.
P107159|annual_direct|ICR|26|46,842|46842|1|ICR footnote explicitly annual emission reduction; lifetime calculations use 25 years, unlike annex life of 13.
P127775|annual_direct|ICR|63|83,757|83757|1|Modelled annual net GHG reduction from component outputs; leakage assumptions retained.
P160408|annual_direct|ICR|28|1,382,000|1382000|1|Net annual emissions shown negative in ICR; annex presents avoided-emission magnitude. Revised target differs from FY24.
P150930|horizon_conflict|ICR|24|599,858|599858||Preparation-stage sink estimated over 20 years; annex 23994 is consistent with division by 25, not documented 20-year horizon; no completion annual value verified.
P147760|basis_ambiguity|ICR|38|6,095,032|6095032||Exact Year-6 sequestration indicator with nonzero baseline and metric-ton unit; annual incremental avoided-emission basis not established.
P164047|horizon_conflict|ICR|17|3,190,000|3190000||Program-period sequestration total; annex 106333 equals division by 30-year life but ICR p53 distinguishes five-year program from 30-year model horizon.
P132873|annual_direct|ICR|18|76,955|76955|1|Explicit annual CO2 reductions at completion; some generation outputs remained prospective.'''
ghgs={}
for line in ghg_text.splitlines():
 p,cl,typ,pg,tok,v,div,n=line.split('|');ghgs[p]=dict(ghg_class=cl,ghg_file=f'{p}_{typ}.pdf',ghg_pdf_page=int(pg),ghg_token=tok,source_ghg_quantity=float(v) if v else None,divisor=float(div) if div else None,ghg_note=n)
exclude={'P096586':'Only supported-investment total 539m and unquantified implementation contribution; full cost boundary unresolved.','P104266':'IEG 33.9m is credit-line cost; ICR associated investments 42.71m imply different financing and outcome scopes.','P131765':'Joint three-phase ICR: phase-II datasheet omits counterpart funds; phase components and program outcomes cannot be assigned without further reconciliation.','P132443':'IEG reports 40.3m bank cost while 20m in-kind investments are excluded from formal cofinancing; whole-project boundary unresolved.','P154669':'Program financing versus underlying subproject investment totals differ; bank-only cover field rejected.','P131256':'Reporting-status transition; actual cost/financing figures and expanded Noor complex require scope reconciliation.','P154283':'Reporting-status transition; infrastructure cost excludes mobilized generation investments; unit conflict retained.','P160408':'Reporting-status transition; IEG cost field repeats bank disbursement while counterpart funds are reported separately.','P132741':'Reporting-status transition; no completion document retrieved.'}
universe=list(csv.DictReader(open(R/'audit_universe.csv')));old={r['project_id']:r for r in csv.DictReader(open(R.parent/'ibrd/results/sample_flow_project_level.csv'))}
man=json.loads((R/'source_manifest.json').read_text())+json.loads((R/'icr_manifest.json').read_text())+json.loads((R/'isr_manifest.json').read_text());md={r['file']:r for r in man if 'error' not in r}
rows=[]
for x in universe:
 p=x['project_id'];r=dict(project_id=p,country=x['country'],annex_ghg=float(x['ghg']),annex_life=float(x['life']),same_status=old[p]['same_status']=='True',**ghgs[p]);r.update(costs.get(p,dict(cost_usd_m=None,cost_note=exclude.get(p,''))));r['cost_accepted']=p in costs
 for key in ['cost','ghg']:
  if key+'_file' in r:r[key+'_source_date']=md[r[key+'_file']]['doc_date'][:10];r[key+'_source_url']=md[r[key+'_file']]['url']
 rows.append(r)
(R/'audit_ledger.json').write_text(json.dumps(rows,indent=2));fields=list(dict.fromkeys(k for r in rows for k in r))
with open(R/'results/audit_ledger.csv','w') as f:
 w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
# Source manifest records all acquired files; identical report copies explicitly retained as catalog records.
(R/'all_sources.json').write_text(json.dumps(man,indent=2))
print('Audit rows',len(rows),'accepted costs',sum(r['cost_accepted'] for r in rows))
