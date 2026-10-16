# BigBoxPizza – Calculation Audit Trail

This document explains how every number in the workbook and report is produced, so that it can be reproduced and checked independently. Notation: *s* = scenario (LOW/BASE/STRESS), *k* = SKU (3464, 3463, 3460), *n* = number of containers, FX = EGP per USD after bank spread.

## 1. Calculation sequence

1. **Inputs** (input sheets; LOW/BASE/STRESS columns; evidence class and sources per row) → `inputs.py` is the build source.
2. **Blank & bundle geometry** (Loading Geometry §A) → bundle a×b×h, bundle kg, m³ and kg per box.
3. **Usable container envelope** (§B) → usable L, W, H; road-weight limit; efficiency.
4. **Single-SKU capacity** (§C) → floor positions (row-mix pattern) × layers → theoretical → operational (× efficiency) → MIN(volume, weight).
5. **Shipment configurations** (Shipment Configuration) → units per SKU per scenario; zone-layout feasibility per container.
6. **Calc Engine**: one row per scenario × configuration × destination (150), plus 33 sensitivity and 6 combination rows → every cost, revenue, margin, cash and break-even figure.
7. **Views** (Landed Cost ledger & SKU allocation, Pricing, Profitability, Sensitivity, Scenario Comparison, Cash Flow, Dashboard) read the engine by INDEX/MATCH.
8. **Checks** (Model Checks) reconcile the ledger, allocation, quotation, customs value and double-count flags.

## 2. Principal formulas

| Quantity | Formula |
|:---|:---|
| Supplier value (USD) | SUP_k = units_k × price_EGP_k × (1 + re-quote) × supplier factor / FX |
| VAT cash / economic | VAT_cash = 14% × SUP if mode ∈ {2,3}; VAT_econ = VAT_cash if mode = 3 else 0 |
| Origin per container | n × [truck/FX + terminal + OTHC × (1 − OTHC-in-freight) + seal + inspection + detention days × rate + loading/FX] |
| Origin per shipment | (clearance + CoO)/FX + B/L + forwarder + QC + wires × fee |
| Ocean | n × (rate_container,s + port differential) × ocean factor + AMS   (LCL: max(m³ × factor, t, 1) × all-in rate/W-M) |
| Customs value | CV_k = SUP_k × (1 + 14% if mode 3) + tooling × units_k/U |
| Insurance | MAX(min, rate × 1.10 × (SUP + tooling + origin + ocean)) × (1 − included-elsewhere flag) |
| Duty | CV × (MFN 0% + Section 301 rate) |
| MPF | MIN(MAX(CV × 0.3464%, $34.58), $670.86) |
| HMF | CV × 0.125% |
| Bond (STB) | MAX(min, rate/1000 × (CV + duty + MPF + HMF)) |
| Delivery | n × [line × dray factor × (1 + FSC) + tolls + chassis days × rate × (1 − chassis-included) + waiting + split + pre-pull + dry run] |
| Unloading | n × unload rate × (1 − unloading-included) |
| COGS (delivered economic) | SUP + VAT_econ + tooling + origin + ocean + insurance + duty + MPF + HMF + US per-shipment + US per-container + delivery + unloading |
| Saleable units | units_k × (1 − damage rate) |
| Price | listing_k × (1 − E-flute discount if listing is B-flute) × (1 − buyer margin) × price factor |
| Gross margin / markup | GM = (REV − COGS)/REV;  markup = (REV − COGS)/COGS |
| Contribution | GP − REV × (commission + processing + bad debt) − testing × first-shipment flag − admin − financing |
| Financing | rate/365 × Σ outflow_i × (day customer pays − day_i), VAT (mode 2) financed until refund day |
| Peak working capital | MAX of cumulative outflows at days 0, export, entry, delivery, less VAT refund if received by then |
| Break-even price factor | (COGS + fixed selling + financing) / (REV × (1 − variable selling %)) |
| Supplier change for GM target | g = (REV(1 − GM) − (COGS − A))/A, A = (SUP + VAT_econ)(1 + duty + HMF + marginal MPF) + marginal insurance; change = (1 + re-quote) × g − 1 |
| Max EXW price for GM target | p_k = [price_k(1 − GM)(1 − dmg) − o_k] / (1 + a_k) × FX / (1 + re-quote); a_k, o_k from the SKU cost split |
| Break-even units | U = fixed / (price per unit × (1 − GM) − variable per unit) |

## 3. Cost allocation to SKUs

| Cost | Driver | Rationale |
|:---|:---|:---|
| Supplier price, VAT | Direct | Invoiced per SKU |
| Duty | Direct via customs value | Ad valorem on each line |
| MPF + HMF | Customs value share | Ad valorem at entry level |
| Insurance | Supplier value share | Insured value driven by product value |
| Tooling | Units | One-off, no better driver |
| Origin per container, ocean, US per container (CFC, exam, demurrage), drayage, unloading | Bundle volume (cube) | Container space and time are the cost cause |
| Origin per shipment, broker, ISF, bonds, DO | Units | Administrative, shipment-level |
| Selling costs (profitability view) | Revenue share | Commission and credit costs scale with revenue |

The check `Σ_k cost_k − COGS = 0` is evaluated on every engine row (Model Checks #7).

## 4. Customs value and duty logic

- Basis: transaction value = price actually paid or payable (19 U.S.C. 1401a; 19 CFR 152.103). Additions: buyer-paid packing, assists (tooling), commissions, royalties (none assumed except tooling).
- Exclusions: international freight and insurance; Egyptian inland freight for a proven ex-factory sale (19 CFR 152.103(a)(5)(i)).
- VAT: zero-rated or refunded VAT is not part of the price paid; non-recoverable VAT (mode 3) is added to customs value (conservative).
- Duty layers: HTS 4819.10.00 MFN Free + Section 301 (Egypt) 9903.05.36 12.5% (BASE/STRESS) or 0% (LOW, i.e. exemption or invalidation). No AD/CVD or Section 232 applies to Egypt-origin 4819.10 on the research date.
- BASE quoted order: CV $8,778.81; duty $1,097.35; MPF $34.58 (minimum binds); HMF $10.97.

## 5. Container-loading logic

- Blank: length = 2L + k·H (k = 4.5), width = W + 2H + 13 mm, calibrated on a US 14×14×1.75 in box listed with a 36×18 in pack [S080]. Net board = 92% of the bounding rectangle; weight = net area × g/m².
- Bundle: a = blank length + 5 mm, b = blank width + 5 mm, h = blanks per bundle (50) × pitch (1.5/1.6/1.8 mm).
- Usable envelope: L − 100 mm, W − 20 mm, MIN(H − 90 mm, door height).
- Floor pattern (Excel formulas): for n2 = 0..2 rows with the long side across the container, n1 = INT((W − n2·a)/b); positions = n1·INT(L/a) + n2·INT(L/b); best of three. Validated by an exhaustive two-dimensional guillotine dynamic program over raster points (`loading_model.dp_positions`); it equals the formula optimum in all 27 SKU × container × scenario cases.
- Layers = INT(usable height / bundle height); theoretical = positions × layers × 50; operational = INT(theoretical bundles × efficiency) × 50; weight-limited = INT(road limit / bundle kg) × 50; realistic = MIN.
- Mixed loads: each SKU occupies a block of container length. Stacks_k = ROUNDUP(bundles_k / (efficiency × layers)); minimum block length found from candidate lengths (multiples of a and b around the continuous estimate; the Excel method equals the exact search in every case); fits if Σ block lengths ≤ usable length and Σ kg ≤ road limit.
- Equal-mix maxima are solved by bisection in `loading_model.best_equal_mix` and written as orange values; the workbook re-tests them with formulas (Model Checks #20).

## 6. Scenario assumptions (summary)

| Input | LOW | BASE | STRESS | Evidence |
|---|---|---|---|---|
| FX (EGP/USD, CBE) | 54.6 | 53.04 | 49 | VERIFIED_OFFICIAL |
| Re-quote change | −5% | 0% | 10% | ASSUMED |
| VAT mode | 1 | 2 | 3 | UNRESOLVED |
| Section 301 rate | 0% | 12.5% | 12.5% | VERIFIED_OFFICIAL |
| Ocean 40' HC (USD) | 2,900 | 4,000 | 5,000 | ESTIMATED |
| Stacking pitch (mm) | 1.5 | 1.6 | 1.8 | ESTIMATED |
| Loading efficiency | 97% | 95% | 90% | ASSUMED |
| Buyer resale margin | 20% | 25% | 30% | ASSUMED |
| E-flute discount | 15% | 20% | 25% | CALCULATED |
| Damage rate | 0.005 | 0.015 | 0.04 | ASSUMED |
| Exam (USD/ctr) | 0 | 0 | 350 | ESTIMATED |
| Demurrage days | 0 | 0 | 3 | ASSUMED |

## 7. Validation performed

- Workbook rebuilt by `scripts/build_model.py`, recalculated in LibreOffice 24.2.7.2 (headless, UNO `calculateAll`) and re-opened with openpyxl: status **PASS**.
- Worksheets: 27; missing required sheets: none; formula cells: 30,785.
- Error values after recalculation: 0.
- Independent cross-check: 189 Calc Engine rows compared with `scripts/engine.py` on 45 values each (cost, revenue, margin, cash and break-even outputs, per-SKU cost, price and maximum EXW, and the container-fit flag; tolerance 1e-6, relative above 1): 0 mismatches. Geometry capacities: 0 mismatches.
- Formal QA checklist (brief §21: research, engineering, financial and deliverable validation) with the evidence for each item: `outputs/qa_validation_checklist.md`.

Model Checks sheet after recalculation:

| Check | Status |
|:---|:---|
| Quote line totals = qty × unit price | OK |
| Quote subtotal reconciles | OK |
| Quote tax = 14% × subtotal | OK |
| Quote total reconciles | OK |
| Quoted quantity = 60,000 | OK |
| Fixed configurations C1–C3 total 60,000 units in every scenario | OK |
| Engine: SKU cost allocation sums to COGS on every row | OK |
| Ledger economic total = engine COGS (selected case) | OK |
| No duplicate cost IDs in ledger | OK |
| Origin ledger lines = engine ORIGIN | OK |
| Ocean + insurance ledger = engine | OK |
| US duty/fees ledger = engine | OK |
| Delivery & disruption ledger = engine | OK |
| SKU allocation table total = engine COGS | OK |
| Supplier quotation reconciles to shipment value (when units = quoted mix) | n/a – configuration differs from quoted mix |
| Customs value build-up = engine customs value | OK |
| Double-count flag: origin THC not also in ocean freight | OK – THC charged once (ocean estimate excludes OTHC) |
| Double-count flag: CFC / insurance / chassis / unloading | OK – flags set (each item once) |
| Recoverable VAT excluded from COGS unless mode 3 | OK |
| Equal-mix maxima (script values) still fit in all scenarios | OK |
| Floor pattern equals exact DP optimum (all SKU × container × scenario) | OK |
| No error values in engine key outputs | OK |
| Supplier quotation expired (information) | WARN – expired quote used as historical reference |
| FX observation within 7 days of valuation date | OK |
| OVERALL STATUS | WARN – 1 warning(s), no failures |

## 8. Limitations

- No written quotations (supplier re-quote, freight, broker, trucking, insurance, buyers). All logistics and market inputs are ESTIMATED or ASSUMED from documented proxies.
- Official websites could not be opened directly from the research environment; facts were taken from search-engine extracts of those pages. Re-verify before use.
- Blank geometry, grammage and bundle data are estimates; NFC data will change container capacity.
- Achievable prices are derived from advertised small-quantity prices, not negotiated container-lot prices.
- Financing uses simple interest on a 5-event timeline; no tax on profits; no US sales tax (B2B resale).
- The workbook recalculates in Excel/LibreOffice; the equal-mix maxima (orange) need `build_all.py` to be re-run if geometry inputs change. The checks flag this.

## 9. Reproduction

```bash
python3 BigBoxPizza/scripts/build_all.py   # charts, workbook, LibreOffice recalculation + validation, CSV, Markdown, QA checklist
python3 BigBoxPizza/scripts/engine.py      # prints the reference engine results
python3 BigBoxPizza/scripts/check_urls.py  # optional, needs network: source URL reachability → outputs/url_check.json
```

