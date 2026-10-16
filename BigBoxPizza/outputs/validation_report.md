# Workbook validation report

Status: **PASS**

- Source workbook: `_build_formulas.xlsx`; recalculated with LibreOffice (headless, UNO calculateAll) in 2.4 s → `BigBoxPizza_US_Landed_Cost_Model.xlsx`
- Worksheets: 27 (Executive Dashboard, Read Me & Instructions, Product & SKU Master, Supplier Quotation, Technical Specifications, Exchange Rates, Container Specifications, Loading Geometry, Shipment Configuration, Origin Costs, Ocean Freight, U.S. Port & Customs, Destination Delivery, Tariffs & Customs Value, Landed Cost by SKU, Pricing & Margin, Container Profitability, Sensitivity Analysis, Scenario Comparison, Cash Flow & Working Capital, Competitor Benchmark, Risk Register, Assumptions Register, Source Register, Quote Requests & Missing Data, Calc Engine, Model Checks)
- Missing required worksheets: none
- Formula cells: 30,785
- Error values after recalculation: 0
- Calc Engine rows compared with independent Python engine: 189 (mismatches: 0)
- Loading-geometry capacity mismatches: 0

## Model Checks sheet

| Check | Status |
|---|---|
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
| Supplier quotation reconciles to shipment value (when units = quoted mix) | OK – reconciles |
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

## Formula cells per sheet

| Sheet | Formula cells |
|---|---:|
| Executive Dashboard | 115 |
| Read Me & Instructions | 0 |
| Product & SKU Master | 42 |
| Supplier Quotation | 51 |
| Technical Specifications | 8 |
| Exchange Rates | 6 |
| Container Specifications | 7 |
| Loading Geometry | 1,089 |
| Shipment Configuration | 2,672 |
| Origin Costs | 27 |
| Ocean Freight | 21 |
| U.S. Port & Customs | 20 |
| Destination Delivery | 31 |
| Tariffs & Customs Value | 64 |
| Landed Cost by SKU | 213 |
| Pricing & Margin | 100 |
| Container Profitability | 212 |
| Sensitivity Analysis | 277 |
| Scenario Comparison | 290 |
| Cash Flow & Working Capital | 45 |
| Competitor Benchmark | 24 |
| Risk Register | 24 |
| Assumptions Register | 411 |
| Source Register | 0 |
| Quote Requests & Missing Data | 0 |
| Calc Engine | 25,011 |
| Model Checks | 25 |
