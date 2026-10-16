"""Single source of truth for every BigBoxPizza model input.

Each scenario input is a tuple (LOW, BASE, STRESS):
  LOW    = low-cost / optimistic but defensible
  BASE   = best-supported current value
  STRESS = adverse but plausible
Evidence classes follow brief section 3.4:
  VERIFIED_OFFICIAL, VERIFIED_QUOTE, VERIFIED_SUPPLIER, VERIFIED_MARKET,
  CALCULATED, ESTIMATED, ASSUMED, UNRESOLVED
Source IDs refer to scripts/sources_data.py (BigBoxPizza_Source_Register.csv).

Both the pure-Python engine (engine.py) and the Excel builder (build_model.py)
read these values, so the workbook and the report always share one set of inputs.
"""

VALUATION_DATE = "2026-10-16"
RESEARCH_START_UTC = "2026-10-15T23:47:06Z"
QUOTE = dict(number="NFC-OFFER-2026-0120", date="2026-09-23", valid_until="2026-09-30",
             currency="EGP", tax_rate=0.14, subtotal=463300.0, tax=64862.0, total=528162.0,
             payment_terms_printed="advance_50", incoterm_printed="(none stated)",
             shipping_printed="—")

SCENARIOS = ["LOW", "BASE", "STRESS"]

# --------------------------------------------------------------------------- SKUs
# Quote order is preserved everywhere (3464, 3463, 3460).
SKUS = [
    dict(code="3464", desc_ar="علبة بيتزا 5*35.5*35.5", desc_doc_en="Pizza box 5*35.5*35.5 (no unit printed)",
         desc_brief="5 × 5 × 5.5 inch pizza box", L=355, W=355, H=50, qty=20000, price_egp=8.365,
         line_total=167300.0, us_nominal='14"', bench_flute="B",
         flag="Brief says '5 × 5 × 5.5 inch'; document says 5*35.5*35.5 (consistent with 355×355×50 mm). Confirm nominal size, unit, inside/outside dims."),
    dict(code="3463", desc_ar="علبة بيتزا 5*40.5*40.5", desc_doc_en="Pizza box 5*40.5*40.5 (no unit printed)",
         desc_brief="5 × 40.5 × 40.5 cm pizza box", L=405, W=405, H=50, qty=20000, price_egp=7.900,
         line_total=158000.0, us_nominal='16"', bench_flute="B",
         flag="405 mm = 15.94 in; if outside dimension, a 16-inch pizza may not fit. Priced BELOW the smaller 3464."),
    dict(code="3460", desc_ar="بيتزا 5*30.5*30.5", desc_doc_en="Pizza 5*30.5*30.5 (word 'box' absent)",
         desc_brief="5 × 30.5 × 30.5 cm pizza box", L=305, W=305, H=50, qty=20000, price_egp=6.900,
         line_total=138000.0, us_nominal='12"', bench_flute="E",
         flag="Description lacks the word 'box' (علبة). Confirm item is a complete pizza box."),
]

def inp(name, unit, low, base, stress, evidence, sources, note=""):
    return dict(name=name, unit=unit, v=(low, base, stress), evidence=evidence, sources=sources, note=note)

# --------------------------------------------------------------------------- engineering / blanks
BLANK = dict(
    k_len=inp("Blank length = 2×L + k×H : k", "×H", 4.5, 4.5, 4.5, "ESTIMATED", "S080",
              "Calibrated on Arvco 14×14×1.75 in box listed with 36×18 in pack (36 = 2×14 + 4.57×1.75). Replace with NFC die-line."),
    w_allow=inp("Blank width = W + 2×H + allowance", "mm", 13, 13, 13, "ESTIMATED", "S080",
                "18 in = 14 + 2×1.75 + 0.5 in (12.7 mm) on the Arvco calibration point."),
    net_area=inp("Net board area / bounding rectangle", "ratio", 0.92, 0.92, 0.92, "ASSUMED", "",
                 "Die-cut corner and flap cut-outs removed from bounding rectangle."),
    grammage=inp("Combined board grammage (SINGLE-E)", "g/m²", 400, 420, 480, "ESTIMATED", "S074;S082",
                 "Base calibrated to WebstaurantStore 12×12×2 E-flute: 15 lb per 50 = 136 g/box ⇒ ≈420 g/m² net."),
    pitch=inp("Stacking pitch per flat blank", "mm", 1.5, 1.6, 1.8, "ESTIMATED", "S082",
              "E-flute caliper 1.2–1.8 mm; effective pitch in a strapped bundle. NFC must confirm bundle height."),
    per_bundle=inp("Blanks per bundle", "pcs", 50, 50, 50, "ASSUMED", "S073;S074;S080",
                   "US norm is 50/bundle; NFC bundle count not stated."),
    wrap_mm=inp("Bundle footprint allowance (strap/wrap)", "mm", 5, 5, 5, "ASSUMED", "", ""),
    wrap_kg=inp("Bundle wrap/strap weight", "kg", 0.10, 0.10, 0.10, "ASSUMED", "", ""),
)

# --------------------------------------------------------------------------- containers
CONTAINERS = [
    dict(key="20GP", name="20' dry (GP)", L=5900, W=2350, H=2390, door_W=2340, door_H=2280, tare=2300,
         payload=25000, cube=33.2, teu=1, road_kg=17237, road_note="38,000 lb practical cargo limit on standard chassis (tri-axle needed above)"),
    dict(key="40GP", name="40' dry (GP)", L=12030, W=2350, H=2390, door_W=2340, door_H=2280, tare=3750,
         payload=27600, cube=67.7, teu=2, road_kg=19958, road_note="44,000 lb practical cargo limit (80,000 lb GVW)"),
    dict(key="40HC", name="40' high-cube (HC)", L=12030, W=2350, H=2700, door_W=2340, door_H=2580, tare=3940,
         payload=28560, cube=76.4, teu=2, road_kg=19958, road_note="44,000 lb practical cargo limit (80,000 lb GVW)"),
]
CONTAINER_SOURCES = "S041;S042;S043;S096"
USABLE = dict(
    len_ded=inp("Usable length deduction (door/securing)", "mm", 100, 100, 100, "ASSUMED", "", ""),
    wid_ded=inp("Usable width deduction (wall corrugation/tolerance)", "mm", 20, 20, 20, "ASSUMED", "", ""),
    hgt_ded=inp("Top clearance for hand stacking", "mm", 90, 90, 90, "ASSUMED", "", "Usable height = MIN(internal − clearance, door height)."),
    efficiency=inp("Operational loading efficiency vs geometric maximum", "ratio", 0.97, 0.95, 0.90, "ASSUMED", "",
                   "Hand-stacked loose bundles; voids, dunnage/airbags, dimensional variation."),
)

# --------------------------------------------------------------------------- FX
FX = dict(
    cbe=inp("EGP per USD (CBE official buy rate basis)", "EGP/USD", 54.60, 53.04, 49.00, "VERIFIED_OFFICIAL", "S063;S064;S065",
            "BASE = CBE buy 53.04 (15-Oct-2026). LOW = 2026 high ~54.6 (late March, weaker EGP favours USD buyer). STRESS = 49.0 (Reuters poll, EGP appreciation)."),
    spread=inp("Bank FX spread vs CBE rate", "%", 0.0, 0.005, 0.015, "ASSUMED", "", "Effective rate = CBE × (1 − spread)."),
)

# --------------------------------------------------------------------------- supplier & tax
SUPPLIER = dict(
    requote=inp("Re-quote price change vs expired quote", "%", -0.05, 0.0, 0.10, "ASSUMED", "S001;S068",
                "Quote expired 30-Sep-2026. Upward pressure: diesel +17% since Oct-2025; LOW assumes 5% negotiated discount."),
    vat_rate=inp("Egyptian VAT rate on domestic supply", "%", 0.14, 0.14, 0.14, "VERIFIED_QUOTE", "S001;S060", ""),
    vat_mode=inp("VAT treatment (1=zero-rated direct export; 2=paid & refunded; 3=paid, not recoverable)", "mode", 1, 2, 3, "UNRESOLVED", "S060;S061;S062",
                 "Depends on who is exporter of record. Quote is addressed to a domestic Alexandria buyer with 14% VAT."),
    vat_lag=inp("VAT refund lag after export", "days", 30, 60, 180, "ESTIMATED", "S060;S061", "Statutory 45 days after documented application; ETA target 20 days; delays plausible."),
    advance=inp("Advance payment share", "%", 0.50, 0.50, 0.50, "VERIFIED_QUOTE", "S001", "'advance_50' printed; meaning to be confirmed."),
    tooling_egp=inp("Tooling / dies / plates (one-off)", "EGP", 0, 0, 25000, "ASSUMED", "", "Not mentioned on quote; plain standard sizes assumed to need none."),
    lead_days=inp("Production lead time (order to collection)", "days", 14, 21, 35, "ASSUMED", "", "Not stated on quote."),
)

# --------------------------------------------------------------------------- origin costs (Egypt)
ORIGIN = dict(
    truck_20=inp("Inland trucking factory→Alexandria/Dekheila, 20'", "EGP/ctr", 8500, 10500, 13500, "ESTIMATED", "S066;S067;S068",
                 "2025 association tariff scaled for ~200 km and diesel +17%."),
    truck_40=inp("Inland trucking factory→Alexandria/Dekheila, 40'/HC", "EGP/ctr", 11000, 14000, 18000, "ESTIMATED", "S066;S067;S068",
                 "Sadat/Tanta ≈ EGP 9,500 (2025, ~125 km) → +25% distance → +7% fuel → + loading wait time."),
    clearance=inp("Export customs clearance & documentation (broker)", "EGP/shpt", 4000, 6000, 9000, "ASSUMED", "S062", "No published tariff found; RFQ item."),
    coo=inp("Certificate of origin / chamber (optional for US)", "EGP/shpt", 0, 1000, 2000, "ASSUMED", "", "Not legally required for US MFN entry."),
    terminal=inp("Terminal receiving + VGM weighing", "USD/ctr", 45, 65, 80, "VERIFIED_MARKET", "S069", "ACCHC from 1-Sep-2026: entry USD 15–20; weighing USD 30–60."),
    othc_20=inp("Origin THC, 20'", "USD/ctr", 130, 140, 150, "VERIFIED_MARKET", "S050", "Hapag-Lloyd Alexandria/Damietta."),
    othc_40=inp("Origin THC, 40'/HC", "USD/ctr", 201, 210, 220, "VERIFIED_MARKET", "S050", ""),
    othc_in_freight=inp("Origin THC already included in ocean quote? (1=yes)", "flag", 0, 0, 0, "ASSUMED", "S047",
                        "Ocean estimate is built EXCLUDING origin THC; set 1 if forwarder quote includes it (double-count control)."),
    seal=inp("Container seal", "USD/ctr", 10, 15, 20, "ASSUMED", "", ""),
    bl_fee=inp("B/L & carrier documentation fee", "USD/shpt", 50, 75, 100, "ASSUMED", "S050", "Fee exists on carrier local tariffs; amount not retrieved."),
    fwd_fee=inp("Forwarder origin handling fee", "USD/shpt", 75, 100, 150, "ASSUMED", "", ""),
    inspection=inp("Egyptian export inspection (if selected)", "USD/ctr", 0, 0, 64, "VERIFIED_MARKET", "S069", ""),
    dd_days=inp("Origin detention days beyond free time", "days", 0, 0, 3, "ASSUMED", "S070", ""),
    dd_20=inp("Origin detention rate, 20'", "USD/day", 14, 14, 14, "VERIFIED_MARKET", "S070", "Maersk Egypt days 4–10."),
    dd_40=inp("Origin detention rate, 40'/HC", "USD/day", 28, 28, 28, "VERIFIED_MARKET", "S070", ""),
    loading_egp=inp("Factory loading labour (if NFC charges under EXW)", "EGP/ctr", 0, 0, 2000, "ASSUMED", "S072", "Under EXW the seller has no loading obligation."),
    qc=inp("Pre-shipment QC inspection (third party)", "USD/shpt", 0, 350, 450, "ASSUMED", "", ""),
    wires=inp("Bank wires (count)", "count", 4, 4, 4, "ASSUMED", "", "Advance + balance + forwarder + broker."),
    wire_fee=inp("Bank wire fee", "USD/wire", 25, 40, 60, "ASSUMED", "", ""),
    lcl_truck=inp("LCL: trucking factory→CFS", "EGP/shpt", 5000, 7000, 9000, "ASSUMED", "", ""),
    lcl_cfs_o=inp("LCL: origin fixed charges (documents, export declaration at CFS)", "USD/shpt", 100, 150, 200, "ASSUMED", "",
                  "Per-W-M CFS handling is inside the LCL all-in rate; this line holds per-shipment fixed fees only."),
)

# --------------------------------------------------------------------------- ocean & insurance
OCEAN = dict(
    rate_20=inp("Ocean freight Egypt→USEC base port, 20' (incl. BAF & DTHC, excl. OTHC)", "USD/ctr", 2000, 3000, 3900, "ESTIMATED", "S045;S046;S047;S048;S049",
                "LOW ≈ N.Europe–USEC spot parity; BASE = CMA CGM Med→NY FAK $2,750 + ~$250 surcharges; STRESS = BASE + HL Egypt GRI $300 + ~$600."),
    rate_40=inp("Ocean freight, 40' GP", "USD/ctr", 2800, 3900, 4900, "ESTIMATED", "S044;S045;S046;S047;S048;S095",
                "LOW ≈ FBX22 $2,723 / Xeneta $2,741; BASE = CMA CGM FAK $3,600 + ~$300 bunker/other; STRESS = BASE + HL GRI $600 + ~$400."),
    rate_hc=inp("Ocean freight, 40' HC", "USD/ctr", 2900, 4000, 5000, "ESTIMATED", "S047;S048", "40' GP + $100 HC premium (assumed)."),
    ams=inp("AMS / manifest filing fee", "USD/B/L", 30, 35, 45, "ASSUMED", "", ""),
    transit=inp("Transit time Egypt→USEC", "days", 25, 30, 38, "VERIFIED_MARKET", "S049;S051", "Indicative 25–33 days; 22–35 with transshipment."),
    ins_rate=inp("Cargo insurance rate on (CIF + 10%)", "%", 0.0015, 0.0025, 0.0040, "ESTIMATED", "S089", ""),
    ins_uplift=inp("Insured value uplift", "%", 0.10, 0.10, 0.10, "ESTIMATED", "S089", ""),
    ins_min=inp("Minimum insurance premium", "USD", 50, 75, 100, "ASSUMED", "S089", ""),
    ins_in_other=inp("Insurance already included in another quote? (1=yes)", "flag", 0, 0, 0, "ASSUMED", "", "Double-count control: set 1 if the forwarder quote includes cargo insurance."),
    lcl_rate=inp("LCL all-in rate (ocean + origin & destination CFS handling)", "USD/W-M", 120, 170, 230, "ASSUMED", "",
                 "No Egypt→USEC LCL tariff retrieved (RFQ 2). All-in structure because CFS handling is billed per W-M at both ends; "
                 "an ocean-only rate would make LCL cheaper than a full 20' FCL, which is implausible."),
    lcl_factor=inp("LCL chargeable volume factor vs bundle volume", "ratio", 1.10, 1.10, 1.15, "ASSUMED", "", ""),
    lcl_extra_days=inp("LCL extra transit/consolidation time", "days", 5, 7, 12, "ASSUMED", "", ""),
)
# Port differentials over base port (NY/NJ, Norfolk) — ASSUMED except Savannah (S053 peak premium $75–200/TEU)
PORT_DIFF = {
    "NYNJ": (0, 0, 0),
    "BAL": (0, 150, 300),
    "ORF": (0, 0, 100),
    "SAV": (0, 100, 200),
}

# --------------------------------------------------------------------------- US customs
CUSTOMS = dict(
    mfn=inp("MFN duty HTS 4819.10.00", "%", 0.0, 0.0, 0.0, "VERIFIED_OFFICIAL", "S010;S011;S013", "Column 1 General: Free."),
    s301=inp("Section 301 forced-labor duty, Egypt (9903.05.36)", "%", 0.0, 0.125, 0.125, "VERIFIED_OFFICIAL", "S014;S015;S016;S017;S020",
             "LOW = 0% only if broker confirms an Annex II exemption or the CIT invalidates the action (challenge argued 30-Sep-2026)."),
    mpf_rate=inp("MPF ad valorem", "%", 0.003464, 0.003464, 0.003464, "VERIFIED_OFFICIAL", "S024", ""),
    mpf_min=inp("MPF minimum (FY2027)", "USD", 34.58, 34.58, 34.58, "VERIFIED_OFFICIAL", "S024", ""),
    mpf_max=inp("MPF maximum (FY2027)", "USD", 670.86, 670.86, 670.86, "VERIFIED_OFFICIAL", "S024", ""),
    hmf=inp("Harbor Maintenance Fee", "%", 0.00125, 0.00125, 0.00125, "VERIFIED_OFFICIAL", "S025", ""),
    broker=inp("Customs broker entry fee", "USD/entry", 175, 200, 300, "ESTIMATED", "S039", ""),
    isf=inp("ISF filing fee", "USD/shpt", 35, 50, 75, "ESTIMATED", "S039;S037", ""),
    stb_rate=inp("Single-transaction bond rate", "USD per $1,000", 4, 6, 7, "ESTIMATED", "S038", "Face = value + duties + fees."),
    stb_min=inp("Single-transaction bond minimum premium", "USD", 50, 75, 75, "ESTIMATED", "S038", ""),
    isf_bond=inp("ISF bond (single)", "USD/shpt", 50, 60, 75, "ASSUMED", "S038", ""),
    cfc=inp("PANYNJ Cargo Facility Charge (NY/NJ only)", "USD/TEU", 14.80, 14.80, 14.80, "VERIFIED_OFFICIAL", "S056", "Often passed through by carrier; check quote."),
    cfc_in_freight=inp("CFC already included in ocean freight? (1=yes)", "flag", 0, 0, 0, "ASSUMED", "S056", "Double-count control."),
    do_fee=inp("Destination delivery order / arrival handling", "USD/shpt", 75, 125, 175, "ASSUMED", "", ""),
    exam=inp("CBP exam (VACIS/tailgate)", "USD/ctr", 0, 0, 350, "ESTIMATED", "S091", ""),
    exam_dray=inp("Exam-site drayage", "USD/ctr", 0, 0, 250, "ASSUMED", "S091", ""),
    dem_days=inp("Demurrage/storage days beyond free time", "days", 0, 0, 3, "ASSUMED", "S057", ""),
    dem_rate=inp("Demurrage/storage rate", "USD/day", 150, 200, 250, "ESTIMATED", "S057", ""),
)

# --------------------------------------------------------------------------- destinations
DESTINATIONS = [
    dict(key="D1", port="NYNJ", port_name="New York/New Jersey", city="Edison, NJ (ZIP 08837 – Central NJ warehouse cluster)", miles=28,
         line=(500, 650, 800), tolls=(30, 40, 50), chassis=(28, 35, 45)),
    dict(key="D2", port="NYNJ", port_name="New York/New Jersey", city="Bronx, NY (ZIP 10474 – Hunts Point food-distribution area)", miles=22,
         line=(600, 800, 1000), tolls=(120, 150, 180), chassis=(28, 35, 45)),
    dict(key="D3", port="BAL", port_name="Baltimore", city="Jessup, MD (ZIP 20794 – Baltimore–Washington food-distribution hub)", miles=15,
         line=(450, 550, 700), tolls=(0, 10, 20), chassis=(25, 32, 40)),
    dict(key="D4", port="ORF", port_name="Norfolk (Port of Virginia)", city="Richmond, VA (ZIP 23230 metro warehouses)", miles=95,
         line=(850, 1050, 1300), tolls=(0, 10, 20), chassis=(25, 32, 40)),
    dict(key="D5", port="SAV", port_name="Savannah", city="Atlanta, GA (ZIP 30336 – west Atlanta distribution corridor)", miles=250,
         line=(1200, 1450, 1800), tolls=(0, 0, 20), chassis=(22, 30, 38)),
]
DEST_SOURCES = "S052;S053;S054;S094 (ESTIMATED distance-band anchors)"
DRAY = dict(
    fsc=inp("Drayage fuel surcharge on linehaul", "%", 0.15, 0.20, 0.25, "ESTIMATED", "S052", ""),
    chassis_days=inp("Chassis days billed", "days", 2, 2, 5, "ESTIMATED", "S054", ""),
    wait_hours=inp("Waiting time beyond 2 free hours (floor-loaded live unload)", "hours", 0, 2, 4, "ASSUMED", "", ""),
    wait_rate=inp("Waiting-time rate", "USD/hour", 75, 85, 95, "ASSUMED", "", ""),
    split=inp("Chassis split fee", "USD/ctr", 0, 0, 75, "ESTIMATED", "S052", ""),
    chassis_in_dray=inp("Chassis rental already included in drayage linehaul? (1=yes)", "flag", 0, 0, 0, "ASSUMED", "", "Double-count control."),
    unload_in_dray=inp("Unloading already included in drayage quote? (1=yes)", "flag", 0, 0, 0, "ASSUMED", "", "Double-count control (most dray quotes exclude unloading)."),
    prepull=inp("Pre-pull + yard storage (disruption)", "USD/ctr", 0, 0, 250, "ASSUMED", "", ""),
    dryrun=inp("Dry run / failed delivery", "USD/ctr", 0, 0, 300, "ASSUMED", "", ""),
    unload_20=inp("Unloading floor-loaded 20' (paid by BigBoxPizza)", "USD/ctr", 150, 300, 450, "ESTIMATED", "S055", ""),
    unload_40=inp("Unloading floor-loaded 40'/HC (paid by BigBoxPizza)", "USD/ctr", 250, 450, 650, "ESTIMATED", "S055", "Guide: $350–600 devan."),
    lcl_cfs_d=inp("LCL: destination fixed charges (delivery order, documents, CFS minimum)", "USD/shpt", 150, 200, 300, "ASSUMED", "",
                  "Per-W-M devanning/handling is inside the LCL all-in rate."),
    lcl_deliv=inp("LCL: final truck delivery from CFS", "USD/shpt", 350, 500, 700, "ASSUMED", "", ""),
)

# --------------------------------------------------------------------------- selling & finance
SELLING = dict(
    commission=inp("Sales commission / broker", "% rev", 0.03, 0.05, 0.07, "ASSUMED", "", "No reliable source found."),
    processing=inp("Payment processing", "% rev", 0.0, 0.003, 0.010, "ASSUMED", "", ""),
    bad_debt=inp("Bad-debt allowance", "% rev", 0.0025, 0.005, 0.015, "ASSUMED", "", ""),
    credit_days=inp("Customer credit terms", "days", 30, 45, 60, "ASSUMED", "", ""),
    fin_rate=inp("Cost of capital / financing rate", "% p.a.", 0.08, 0.10, 0.14, "ASSUMED", "", ""),
    damage=inp("Damage / rejection rate (unsaleable units)", "% units", 0.005, 0.015, 0.04, "ASSUMED", "", ""),
    testing=inp("Samples, courier & lab testing (per shipment)", "USD/shpt", 1000, 2500, 4000, "ESTIMATED", "S092", "PFAS screen, heavy metals, food-contact docs review."),
    admin=inp("Sales administration (per shipment)", "USD/shpt", 250, 500, 750, "ASSUMED", "", ""),
    setup=inp("One-time importer set-up (IOR/entity/broker onboarding)", "USD", 0, 750, 2500, "ASSUMED", "S040", "Shown separately; not in per-box cost."),
)

# --------------------------------------------------------------------------- market benchmarks (per SKU, quote order)
MARKET = dict(
    listing={  # resale price per box observed online (restaurant-supply level)
        "3464": inp('14" listing (B-flute kraft)', "USD/box", 0.42, 0.39, 0.38, "VERIFIED_MARKET", "S073;S076", "WebstaurantStore $20.99 / $19.49 / $18.99 per 50."),
        "3463": inp('16" listing (B-flute kraft/white)', "USD/box", 0.46, 0.45, 0.45, "VERIFIED_MARKET", "S076", "WebstaurantStore $22.99 / $22.49 per 50."),
        "3460": inp('12" listing (E-flute kraft)', "USD/box", 0.32, 0.30, 0.30, "VERIFIED_MARKET", "S074", "WebstaurantStore E-flute $15.99 (1) / $14.99 (2+) per 50."),
    },
    eflute_disc=inp("E-flute vs B-flute equivalence discount (applied to B-flute listings)", "%", 0.15, 0.20, 0.25, "CALCULATED", "S074;S075",
                    "1 − 15.99/19.99 = 20.0% (WebstaurantStore 12\" E vs B, same tier)."),
    dist_margin=inp("Wholesale buyer's resale gross margin", "%", 0.20, 0.25, 0.30, "ASSUMED", "S093", "Converts resale listing to the buyer's acceptable purchase price."),
)
GM_TARGETS = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
THRESHOLDS = dict(
    gm_go=0.25, gm_conditional=0.15, cm_min=0.12, cost_ratio_max=0.75, util_min=0.85, demand_min=0.70, compliance_blockers=0,
)

# --------------------------------------------------------------------------- shipment configurations
# kind: 'fixed' (units given), 'fullmix' (equal-units max, solved per scenario), 'fullsku' (single SKU at capacity), 'lcl'
CONFIGS = [
    dict(key="C1", name="Quoted 60,000 mix in one 40' HC", ctype="40HC", n=1, kind="fixed", units={"3464": 20000, "3463": 20000, "3460": 20000}),
    dict(key="C2", name="Quoted 60,000 mix in one 40' GP", ctype="40GP", n=1, kind="fixed", units={"3464": 20000, "3463": 20000, "3460": 20000}),
    dict(key="C3", name="Quoted 60,000 mix split over two 20' GP", ctype="20GP", n=2, kind="fixed", units={"3464": 20000, "3463": 20000, "3460": 20000}),
    dict(key="C4", name="Full 40' HC – equal-units mix (max)", ctype="40HC", n=1, kind="fullmix", units=None),
    dict(key="C5", name="Full 40' HC – 3464 (14\") only", ctype="40HC", n=1, kind="fullsku", sku="3464", units=None),
    dict(key="C6", name="Full 40' HC – 3463 (16\") only", ctype="40HC", n=1, kind="fullsku", sku="3463", units=None),
    dict(key="C7", name="Full 40' HC – 3460 (12\") only", ctype="40HC", n=1, kind="fullsku", sku="3460", units=None),
    dict(key="C8", name="Full 40' GP – equal-units mix (max)", ctype="40GP", n=1, kind="fullmix", units=None),
    dict(key="C9", name="Full 20' GP – equal-units mix (max)", ctype="20GP", n=1, kind="fullmix", units=None),
    dict(key="C10", name="LCL pilot – 10,000 mix (3,350/3,350/3,300 = 200 bundles)", ctype="LCL", n=0, kind="fixed", units={"3464": 3350, "3463": 3350, "3460": 3300}),
]


def all_inputs():
    """Flat list of (group, key, input-dict) for registers."""
    out = []
    for g, d in [("Engineering", BLANK), ("Container", USABLE), ("FX", FX), ("Supplier", SUPPLIER), ("Origin", ORIGIN),
                 ("Ocean", OCEAN), ("US customs", CUSTOMS), ("Destination", DRAY), ("Selling", SELLING)]:
        for k, v in d.items():
            out.append((g, k, v))
    for k, v in MARKET["listing"].items():
        out.append(("Market", "listing_" + k, v))
    out.append(("Market", "eflute_disc", MARKET["eflute_disc"]))
    out.append(("Market", "dist_margin", MARKET["dist_margin"]))
    return out
