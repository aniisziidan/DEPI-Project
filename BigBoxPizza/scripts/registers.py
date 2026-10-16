"""Risk register, missing-information register, competitor listings and RFQ tracker data.
Shared by build_model.py (worksheets) and write_reports.py (Markdown deliverables)."""
import engine as E
import inputs as I
import loading_model as LM


def _money(x, d=0, sign=False):
    t = f"${abs(x):,.{d}f}"
    return (("−" if x < 0 else "+") if sign else ("−" if x < 0 else "")) + t


def _signed(x, d=0):
    return ("−" if x < 0 else "+") + f"{abs(x):.{d}f}"


def _gap_figures():
    """Figures quoted in the gap register, computed from the engine (BASE = scenario 1, C1 quoted order,
    D1 NY/NJ → Edison) so the register text cannot drift from the model."""
    r = [E.compute(s, 0, 0) for s in range(3)]
    b = r[1]
    alt = lambda **o: E.compute(1, 0, 0, o)  # noqa: E731
    v = lambda inp: inp["v"]  # noqa: E731
    hc = v(I.OCEAN["rate_hc"])
    eq = [3 * LM.best_equal_mix(LM.container_by_key("40HC"), s) for s in range(3)]
    dl = [[E.compute(s, 0, di)["DELIV"] for s in range(3)] for di in range(len(I.DESTINATIONS))]
    d_lo = [round(x[0] - x[1], -1) for x in dl]
    d_hi = [round(x[2] - x[1], -1) for x in dl]
    adv = [v(I.SUPPLIER["advance"])[s] * (r[s]["SUP"] + r[s]["VAT_CASH"]) for s in range(3)]
    full_kg = max(LM.capacity(k, LM.container_by_key("40HC"), s)["real_units"] * E.unit_props(s)[k["code"]]["kg"]
                  for k in I.SKUS for s in range(3))
    ins_min = v(I.OCEAN["ins_min"])
    return dict(
        cm_lo=(alt(pricefac=0.85)["CM"] - b["CM"]) * 100, cm_hi=(alt(pricefac=1.15)["CM"] - b["CM"]) * 100,
        f_be=b["f_be"] - 1, price=b["price"],
        duty_b=b["DUTY"] / b["SALE"], duty_s=r[2]["DUTY"] / r[2]["SALE"], gm_s301=(alt(s301=0.0)["GM"] - b["GM"]) * 100,
        sup_share=b["SUP"] / b["COGS"], sup10=alt(supfac=1.10)["avg_cpb"] - b["avg_cpb"], cut25=-b["chg_gm_t"],
        adv_ex=v(I.SUPPLIER["advance"])[1] * b["SUP"], adv=adv,
        vat=b["VAT_CASH"], vat3=alt(vatmode=3)["avg_cpb"] - b["avg_cpb"],
        ocean=b["OCEAN"] / b["SALE"], oc_lo=alt(oceanfac=hc[0] / hc[1])["avg_cpb"] - b["avg_cpb"],
        oc_hi=alt(oceanfac=hc[2] / hc[1])["avg_cpb"] - b["avg_cpb"],
        pitch=v(I.BLANK["pitch"]), eff=v(I.USABLE["efficiency"]), eq=eq, cap_drop=1 - eq[2] / eq[0],
        gp_fits_stress=LM.config_feasibility(I.CONFIGS[1], 2)["fits"],
        kg=[x["kg"] / 1000 for x in r], full_kg=full_kg / 1000, unload=v(I.DRAY["unload_40"]),
        d_lo=(max(d_lo), min(d_lo)), d_hi=(min(d_hi), max(d_hi)),
        ins=[x["INS"] for x in r], ins_binds=all(abs(r[s]["INS"] - ins_min[s]) < 0.01 for s in range(3)),
        lead=v(I.SUPPLIER["lead_days"]), tool=v(I.SUPPLIER["tooling_egp"]), setup=v(I.SELLING["setup"]),
        gsm=v(I.BLANK["grammage"]), ins_rate=v(I.OCEAN["ins_rate"]), ins_up=v(I.OCEAN["ins_uplift"]), ins_min=ins_min,
    )


_F = _gap_figures()

# ----------------------------------------------------------------------------- missing information / gaps
# blocks: "SHIPMENT" (must be resolved before paying/shipping), "PRICING" (decision-relevant), "PRECISION"
GAPS = [
    dict(id="G01", fact="Achievable US wholesale price for E-flute 12\"/14\"/16\" boxes bought in container lots (written buyer quotes / letters of intent)",
         why="Selling price is the single largest driver of the decision; benchmark is derived from online listings, not transactions.",
         impact=f"Selling price −15% / +15% moves contribution margin by {_signed(_F['cm_lo'])} / {_signed(_F['cm_hi'])} points; zero contribution needs prices {_F['f_be']:.0%} above the benchmark on the quoted order.",
         treatment=f"Online listing × (1 − E-flute discount, applied to the 14\"/16\" B-flute listings only) × (1 − buyer resale margin): "
                   f"3464 ${_F['price']['3464']:.3f}, 3463 ${_F['price']['3463']:.3f}, 3460 ${_F['price']['3460']:.3f} (BASE).",
         evidence="Signed RFQ responses or LOIs from ≥3 wholesale buyers stating price, specification, volume and delivery point.",
         who="US distributors / cash-and-carry / regional pizza groups (RFQ 4)", blocks="PRICING", priority=1),
    dict(id="G02", fact="Whether HTS 4819.10 from Egypt is caught by the 12.5% Section 301 forced-labor duty (9903.05.36) or exempt under Annex II Part A; status of the CIT challenge",
         why="Additional duty is the only legal cost that can disappear or rise by government action.",
         impact=f"12.5% of customs value ≈ ${_F['duty_b']:.3f} per box in BASE (${_F['duty_s']:.3f} in STRESS) on the quoted order; 0% improves GM by {_F['gm_s301']:.1f} points.",
         treatment="12.5% in BASE and STRESS; 0% only in LOW.",
         evidence="Licensed customs broker written confirmation against the July-2026 notice annexes and CSMS 69326983 attachment; docket monitoring.",
         who="US customs broker / trade counsel (RFQ 3)", blocks="PRICING", priority=2),
    dict(id="G03", fact="Current NFC price, validity, Incoterm (FCA vs EXW, 2020 edition) and named place, inclusions (loading, bundling, export clearance), payment milestones",
         why=f"Quote expired 30-Sep-2026; no Incoterm printed; supplier price is {_F['sup_share']:.0%} of delivered cost.",
         impact=f"±10% supplier price ⇒ ±${_F['sup10']:.3f} per box; required cut for 25% GM ≈ −{_F['cut25']:.0%} on the quoted order.",
         treatment="Expired prices used as reference; LOW −5%, STRESS +10%.",
         evidence="Signed, dated re-quotation on letterhead naming the buyer entity, FCA named place and validity ≥30 days.",
         who="NFC (RFQ 1)", blocks="SHIPMENT", priority=3),
    dict(id="G04", fact="NFC legal identity, manufacturer status and bank-account ownership",
         why="No independent public record was found; bank name printed 'FAP MISR'; signature name differs from printed name.",
         impact=f"Total loss of the 50% advance in a fraud scenario: {_money(_F['adv_ex'])} before VAT ({_money(_F['adv'][1])} with VAT) in BASE; "
                f"{_money(_F['adv'][0])}–{_money(_F['adv'][2])} from LOW to STRESS.",
         treatment="UNRESOLVED – no payment assumed until verified.",
         evidence="Commercial-registry extract, tax card, industrial registry/licence, factory video audit or visit, bank letter confirming beneficiary; call-back on independently sourced number.",
         who="NFC; Egyptian commercial registry; BigBoxPizza's Egyptian bank", blocks="SHIPMENT", priority=4),
    dict(id="G05", fact="Board specification and food-contact documentation (flute, liner/medium gsm, recycled content, coatings, inks, adhesives; 21 CFR 176.170/176.260 compliance declaration; PFAS-free and heavy-metal certificates)",
         why="'SINGLE-E' does not establish construction or compliance; US buyers expect PFAS-free and TPCH heavy-metal certificates; NY and MD prohibit intentionally added PFAS.",
         impact="Non-compliance can block sale or create liability; weaker board may be unsaleable for 14\"/16\".",
         treatment=f"Assumed E-flute ≈{_F['gsm'][1]} g/m² in BASE ({_F['gsm'][0]}–{_F['gsm'][2]}), calibrated to a US 12\" E-flute bundle weight; compliance UNRESOLVED.",
         evidence="Spec sheet per SKU, supplier declaration of compliance, third-party PFAS (total fluorine) and heavy-metal test reports, sample testing.",
         who="NFC; accredited lab", blocks="SHIPMENT", priority=5),
    dict(id="G06", fact="Inside vs outside dimensions; die-line drawings; nominal size of 3464 (brief '5 × 5 × 5.5 inch' vs document 5×35.5×35.5); whether 3460 is a complete box",
         why="US boxes are sold by inside dimension; 405 mm outside would be too small for a 16\" pizza.",
         impact="Wrong size = unsaleable product.",
         treatment="Quoted L×W×H used as given; descriptions preserved; discrepancy flagged.",
         evidence="Dimensioned drawings and physical samples.", who="NFC", blocks="SHIPMENT", priority=6),
    dict(id="G07", fact="Exporter of record in Egypt and VAT treatment (zero-rated direct export vs domestic sale with refund)",
         why="Export requires an Exporters-Register entry (Law 118/1975); quote is addressed to a domestic Alexandria company with 14% VAT.",
         impact=f"VAT 14% ≈ {_money(_F['vat'])} cash on the quoted order; non-recoverable VAT adds ≈${_F['vat3']:.3f}/box.",
         treatment="BASE: paid and refunded after 60 days; LOW: zero-rated; STRESS: not recoverable.",
         evidence="Egyptian tax adviser opinion; confirmation of exporter registration of the exporting entity.",
         who="Egyptian tax adviser / customs broker / NFC", blocks="SHIPMENT", priority=7),
    dict(id="G08", fact="Written ocean-freight, origin and destination quotes (20'/40'/HC; NY/NJ, Baltimore, Norfolk, Savannah; door delivery)",
         why=f"Ocean freight is the second-largest cost (≈${_F['ocean']:.3f}/box on the quoted order).",
         impact=f"LOW / STRESS freight levels move delivered cost by {_money(_F['oc_lo'], 3, True)} / {_money(_F['oc_hi'], 3, True)} per box.",
         treatment="Estimated from CMA CGM Med FAK, Hapag-Lloyd Egypt GRI, FBX22, WCI.",
         evidence="Itemised forwarder quotes with validity, inclusions/exclusions and free time.", who="Egyptian forwarders (RFQ 2)", blocks="PRICING", priority=8),
    dict(id="G09", fact="Blank and bundle geometry: flat blank size, blanks per bundle, bundle size/weight, palletisation option, NFC load plan",
         why="Units per container drive the per-box share of fixed logistics cost.",
         impact=f"LOW→STRESS geometry (stacking pitch {_F['pitch'][0]}→{_F['pitch'][2]} mm, loading efficiency {_F['eff'][0]:.0%}→{_F['eff'][2]:.0%}) "
                f"cuts 40' HC equal-mix capacity by {_F['cap_drop']:.0%} ({_F['eq'][0]:,}→{_F['eq'][2]:,} boxes); "
                + ("the quoted order still fits a 40' GP under STRESS." if _F["gp_fits_stress"] else "the quoted order does not fit a 40' GP under STRESS."),
         treatment="Parametric die-line estimate calibrated to a US 14\" box; 50 blanks/bundle.",
         evidence="Bundle drawings, weights and NFC container load plan.", who="NFC (RFQ 1)", blocks="PRECISION", priority=9),
    dict(id="G10", fact="US importer-of-record structure (entity, CBP Form 5106, bond, broker power of attorney)",
         why="Without an IOR the goods cannot be entered; IOR carries legal liability for classification and value.",
         impact=f"One-time set-up {_money(_F['setup'][0])}–{_money(_F['setup'][2])} (BASE {_money(_F['setup'][1])}); bond and broker fees per entry.",
         treatment="Single-transaction bond assumed; set-up shown separately.",
         evidence="Broker onboarding pack; decision on entity/third-party IOR.", who="BigBoxPizza; US customs broker", blocks="SHIPMENT", priority=10),
    dict(id="G11", fact="Customer receiving requirements (floor-loaded acceptance, appointment windows, unloading fees, pallet requirements)",
         why=f"Floor-loaded flat bundles require hand unloading (≈{_F['kg'][0]:.1f}–{_F['kg'][2]:.1f} t for the quoted order; up to ≈{_F['full_kg']:.1f} t for a full single-size 40' HC).",
         impact=f"Unloading {_money(_F['unload'][0])}–{_money(_F['unload'][2])} per 40' ($0 if the customer unloads); palletising would reduce container capacity.",
         treatment=f"Floor-loaded, live unload, BigBoxPizza pays {_money(_F['unload'][1])} per 40' (BASE).",
         evidence="Buyer receiving guide / RFQ answers.", who="US buyers (RFQ 4)", blocks="PRICING", priority=11),
    dict(id="G12", fact="Drayage quotes per destination (incl. chassis, fuel, tolls, waiting time) and free-time terms",
         why="Distance-band estimates are vendor-guide quality.", impact=f"Delivery cost per container versus BASE: {_money(_F['d_lo'][0], 0, True)} to {_money(_F['d_lo'][1], 0, True)} at LOW rates and "
                f"{_money(_F['d_hi'][0], 0, True)} to {_money(_F['d_hi'][1], 0, True)} under STRESS (incl. disruption accessorials), depending on destination.",
         treatment="ESTIMATED per destination.", evidence="Two drayage quotes per lane.", who="US truckers/forwarder", blocks="PRECISION", priority=12),
    dict(id="G13", fact="Country-of-origin marking method ('Made in Egypt' on bundle wraps vs each box)",
         why="19 CFR 134.24 allows outer-container marking if users are 'ultimate purchasers' – broker should confirm.",
         impact="Printing each box would add cost; improper marking risks delays/marking duties.",
         treatment="Bundle-wrap marking assumed, no extra cost.", evidence="Broker confirmation or CBP ruling.", who="US customs broker", blocks="SHIPMENT", priority=13),
    dict(id="G14", fact="State-specific packaging obligations for target buyers (NY/MD PFAS, TPCH heavy-metals certificate, packaging EPR)",
         why="Several East-Coast states regulate food packaging.", impact="Documentation cost; sales restrictions if non-compliant.",
         treatment="Testing budget included in selling costs.", evidence="Buyer compliance requirements; legal review.", who="Buyers; regulatory counsel", blocks="SHIPMENT", priority=14),
    dict(id="G15", fact="Insurance quote (rate, deductible, exclusions, minimum premium)", why="Small but mandatory risk transfer.", impact=f"{_money(_F['ins'][0])}–{_money(_F['ins'][2])} per shipment in the model" + (" (the minimum premium binds)." if _F["ins_binds"] else "."),
         treatment=f"{_F['ins_rate'][1]:.2%} of (CIF + {_F['ins_up'][1]:.0%}), minimum {_money(_F['ins_min'][1])} (BASE).", evidence="Insurer/forwarder quote.", who="Cargo insurer / forwarder", blocks="PRECISION", priority=15),
    dict(id="G16", fact="Statistical suffix (4819.10.0020 'sanitary food containers' vs .0040) and broker classification confirmation",
         why="Correct entry data; no duty difference (both Free).", impact="Nil on duty; compliance accuracy.",
         treatment="4819.10.0020 provisionally.", evidence="Broker classification note; optional binding ruling.", who="US customs broker", blocks="PRECISION", priority=16),
    dict(id="G17", fact="Lead time, capacity, QC procedure and tolerances", why="Drives cash timing and quality risk.", impact=f"Lead time {_F['lead'][0]}–{_F['lead'][2]} days in model.",
         treatment=f"{_F['lead'][1]} days BASE.", evidence="NFC production plan, QC checklist.", who="NFC", blocks="PRECISION", priority=17),
    dict(id="G18", fact="Tooling/plate/die and printing charges", why="Not stated on quote.", impact=f"EGP {_F['tool'][0]:,}–{_F['tool'][2]:,} one-off.",
         treatment=f"EGP {_F['tool'][1]:,} BASE; EGP {_F['tool'][2]:,} STRESS.", evidence="Re-quote line items.", who="NFC", blocks="PRECISION", priority=18),
    dict(id="G19", fact="Developments in the AD/CVD case on pizza boxes from China, Malaysia and Türkiye",
         why="Duties on those origins could lift US import prices (opportunity) but an Egyptian surge could attract a new petition (risk).",
         impact="Market-price and trade-remedy exposure.", treatment="Not modelled numerically; tracked as risk.",
         evidence="ITC preliminary vote (~Oct 2026), Commerce initiation/preliminary determinations.", who="Trade counsel / monitoring", blocks="PRICING", priority=19),
]

# ----------------------------------------------------------------------------- risks
RISKS = [
    ("R01", "Achievable selling price below delivered cost", "Market", 5, 5, "Do not ship without written buyer prices ≥ break-even; target full containers; renegotiate NFC price.", "BigBoxPizza", "Open – BASE GM negative"),
    ("R02", "Section 301 duty changes (CIT ruling, new actions or rate increase)", "Trade law", 3, 3, "Broker monitoring; price clauses that pass through duty changes; keep entries refund-ready.", "Broker / counsel", "Open"),
    ("R03", "New AD/CVD petition naming Egypt if Egyptian pizza-box imports surge", "Trade remedy", 2, 4, "Monitor petition scope; avoid positioning as low-price dumping substitute; document normal-value pricing.", "Counsel", "Watch"),
    ("R04", "Supplier identity or payment fraud (unverified NFC, bank-name typo, signatory mismatch)", "Counterparty", 2, 5, "Registry extract, video audit, bank verification by call-back, use LC or escrow / pay against documents.", "BigBoxPizza", "Open – blocking"),
    ("R05", "Expired quote – price increase on re-quote", "Commercial", 4, 3, "Obtain dated re-quote; index clauses tied to kraft paper price.", "BigBoxPizza", "Open"),
    ("R06", "Specification mismatch: E-flute too light for 14\"/16\" US use; outside dims too small", "Product", 3, 5, "Samples, fit test with real pizzas, ECT/stacking tests before PO.", "BigBoxPizza / lab", "Open – blocking"),
    ("R07", "Food-contact non-compliance (recycled-fibre contaminants, inks, adhesives)", "Regulatory", 2, 5, "Supplier compliance declaration vs 21 CFR 176.170/176.260; lab tests; supplier liability clause.", "NFC / lab", "Open – blocking"),
    ("R08", "PFAS / heavy-metal certificates missing → buyer rejection in NY/MD and TPCH states", "Regulatory", 3, 4, "PFAS-free declaration + total-fluorine test; TPCH certificate of compliance.", "NFC / lab", "Open"),
    ("R09", "Egyptian export structure unworkable under EXW (exporter registration, clearance)", "Origin", 4, 3, "Switch to FCA (named factory) with NFC as exporter; or use a registered Egyptian exporter.", "NFC / forwarder", "Open"),
    ("R10", "VAT refund delay or denial (if VAT is charged)", "Tax", 3, 2, "Zero-rated direct export; tax adviser opinion; bank-routed proceeds.", "Tax adviser", "Open"),
    ("R11", "Ocean freight spike / GRIs / rate-restoration surcharges / routing disruption", "Logistics", 3, 3, "Lock quotes with validity; flexible gateway; avoid peak season.", "Forwarder", "Open"),
    ("R12", "EGP appreciation vs USD (EGP-priced purchase)", "FX", 2, 2, "Price in USD or hedge timing; FX clause.", "BigBoxPizza", "Watch"),
    ("R13", "Actual bundle geometry worse than estimated (fewer units per container)", "Engineering", 3, 2, "Obtain NFC load plan before booking; prefer 40' HC for the quoted order.", "NFC / forwarder", "Open"),
    ("R14", "Moisture / condensation damage to corrugated board in transit", "Quality", 2, 3, "Desiccants, container liners, dry boxes; insurance ICC(A).", "NFC / forwarder", "Open"),
    ("R15", "Customer refuses floor-loaded container or charges unloading/detention", "Delivery", 3, 2, "Agree receiving terms in RFQ 4; price unloading in.", "BigBoxPizza", "Open"),
    ("R16", "Demurrage/detention from exams, appointments or late paperwork", "Delivery", 3, 2, "Pre-clear entries; ISF on time; appointment booking at arrival.", "Broker / trucker", "Open"),
    ("R17", "CBP exam or hold on first shipment", "Customs", 3, 2, "Complete documentation; budget exam costs (stress case).", "Broker", "Open"),
    ("R18", "Origin-marking deficiency (no 'Made in Egypt' on outer wraps)", "Customs", 2, 3, "Specify marking in PO; photo evidence pre-shipment.", "NFC / broker", "Open"),
    ("R19", "Importer-of-record liability for classification/valuation errors", "Customs", 2, 4, "Broker review; reasonable-care file (spec sheets, invoices, payment proof).", "IOR / broker", "Open"),
    ("R20", "Buyer credit default / late payment", "Credit", 2, 4, "Credit checks; deposit or LC from buyer; credit insurance.", "BigBoxPizza", "Open"),
    ("R21", "Quality defects → claims, returns or rejected lots", "Quality", 3, 3, "Pre-shipment inspection; AQL sampling; supplier warranty.", "BigBoxPizza / QC firm", "Open"),
    ("R22", "Working-capital strain from 50% advance and prepaid freight", "Finance", 3, 3, "Negotiate 30/70 or payment against documents; LC.", "BigBoxPizza", "Open"),
    ("R23", "ISF late or inaccurate ($5,000 liquidated damages)", "Customs", 2, 2, "Forwarder sends ISF data ≥72 h before loading.", "Broker / forwarder", "Open"),
    ("R24", "Lead-time slippage / capacity at NFC", "Supply", 3, 2, "Production schedule with penalties; buffer in buyer delivery promise.", "NFC", "Open"),
]

# ----------------------------------------------------------------------------- competitor / market listings
COMPETITORS = [
    dict(supplier="WebstaurantStore (Choice)", product="12\"×12\"×2\" kraft E-flute pizza box, item 245CPB12EPRINT", url="https://www.webstaurantstore.com/choice-12-x-12-x-2-kraft-corrugated-e-flute-pizza-box-bundle/245CPB12EPRINT.html",
         dims='12 × 12 × 2 in', board="E-flute corrugated, 100% recycled; no intentionally added PFAS", printing="Stock print", per_pack=50, moq="1 bundle",
         price="$15.99 (1) / $14.99 (2+) per 50", ppb=0.30, shipping="Not included (varies)", tax="Excluded", ptype="Online restaurant-supply, small volume", avail="Ships in 1 business day",
         date="2026-10-16", comparability=5, sid="S074", note="Closest equivalent to SKU 3460; bundle 15 lb (≈136 g/box)."),
    dict(supplier="WebstaurantStore (Choice)", product="12\"×12\"×2\" kraft B-flute pizza box, 245CPB12PRINT", url="https://www.webstaurantstore.com/choice-12-x-12-x-2-kraft-corrugated-pizza-box-50-case/245CPB12PRINT.html",
         dims='12 × 12 × 2 in', board="B-flute 1/8\"", printing="Stock print", per_pack=50, moq="1 bundle", price="$19.99 (1), $18.99 (3–9), $14.99 (10+)", ppb=0.30,
         shipping="Not included (varies)", tax="Excluded", ptype="Online restaurant-supply, volume tiers", avail="In stock", date="2026-10-16", comparability=3, sid="S075",
         note="E vs B price ratio at single bundle = 0.80 (basis for E-flute discount)."),
    dict(supplier="WebstaurantStore (Choice)", product="14\"×14\"×2\" kraft B-flute pizza box, 245CPB14PRINT", url="https://www.webstaurantstore.com/choice-14-x-14-x-2-kraft-corrugated-pizza-box-50-case/245CPB14PRINT.html",
         dims='14 × 14 × 2 in', board="B-flute 1/8\", recycled", printing="Stock print", per_pack=50, moq="1 bundle", price="$20.99 list / $19.49 per 50", ppb=0.39,
         shipping="Not included (varies)", tax="Excluded", ptype="Online restaurant-supply", avail="In stock", date="2026-10-16", comparability=3, sid="S073",
         note="Shipping weight 20.85 lb per 50 (≈189 g/box)."),
    dict(supplier="WebstaurantStore (Choice)", product="14\"×14\"×2\" kraft plain customizable, 245CB14PLN", url="https://www.webstaurantstore.com/search/16x16-pizza-box.html",
         dims='14 × 14 × 2 in', board="B-flute (assumed from range)", printing="Plain", per_pack=50, moq="1 bundle", price="$18.99 per 50", ppb=0.38,
         shipping="Not included", tax="Excluded", ptype="Online restaurant-supply", avail="n/a", date="2026-10-16", comparability=3, sid="S076", note="Search-page snapshot."),
    dict(supplier="WebstaurantStore (Choice)", product="16\"×16\"×2\" white / kraft corrugated pizza box", url="https://www.webstaurantstore.com/search/16x16-pizza-box.html",
         dims='16 × 16 × 2 in', board="Corrugated (B-flute class)", printing="Stock print", per_pack=50, moq="1 bundle", price="$22.99 (white) / $22.49 (kraft) per 50", ppb=0.45,
         shipping="Not included", tax="Excluded", ptype="Online restaurant-supply", avail="n/a", date="2026-10-16", comparability=3, sid="S076", note="Search-page snapshot."),
    dict(supplier="Uline", product="Plain pizza box 14×14×2\" white, S-17593", url="https://www.uline.com/Product/Detail/S-17593/Take-Out-Containers/Plain-Pizza-Boxes-14-x-14-x-2-White",
         dims='14 × 14 × 2 in', board="Corrugated, white exterior/kraft interior", printing="Plain", per_pack=50, moq="1 bundle", price="$54 (1) / $51 (2+) per 50", ppb=1.02,
         shipping="Extra", tax="Excluded", ptype="Industrial catalogue (premium)", avail="In stock", date="2026-10-12", comparability=2, sid="S077", note="Price ceiling, not a wholesale benchmark."),
    dict(supplier="Uline", product="Plain pizza box 12×12×2\" white, S-17592", url="https://www.uline.com/Product/Detail/S-17592/Take-Out-Containers/Plain-Pizza-Boxes-12-x-12-x-2-White",
         dims='12 × 12 × 2 in', board="Corrugated, white", printing="Plain", per_pack=50, moq="1 bundle", price="$41 (1) / $39 (2+) per 50", ppb=0.78,
         shipping="Extra", tax="Excluded", ptype="Industrial catalogue (premium)", avail="In stock", date="2026-10-12", comparability=2, sid="S077", note=""),
    dict(supplier="Costco Business Center (Vital International Solutions)", product="Pre-printed pizza box 14\", 50 ct", url="https://app.warehouserunner.com/costco/1984293-vital-solutions-14-pizza-box-50-ct",
         dims='14 in', board="B-flute, 60% recycled", printing="Pre-printed", per_pack=50, moq="1 case", price="$21.39–$28.29 (avg $23.25) per 50", ppb=0.465,
         shipping="Delivered (Business Delivery)", tax="Excluded", ptype="Cash-and-carry club (member)", avail="Varies", date="2026 (tracker)", comparability=3, sid="S078", note="Third-party price tracker."),
    dict(supplier="Costco Business Center", product="Plain pizza box 16\", 50 ct", url="https://app.warehouserunner.com/costco/2041320-vital-solutions-16-pizza-box-50-ct",
         dims='16 in', board="Corrugated", printing="Plain", per_pack=50, moq="1 case", price="$24.15 per 50 (17-Apr-2026)", ppb=0.483,
         shipping="Delivered/club", tax="Excluded", ptype="Cash-and-carry club (member)", avail="Out of stock at capture", date="2026-04-17", comparability=3, sid="S078", note=""),
    dict(supplier="Imperial Dade (Arvco Container Corp.)", product="14×14×1.88\" and 16×16×1.88\" kraft E-flute pizza boxes, 50 ct", url="https://www.imperialdade.com/catalog/product-detail/16-in-kraft-kraft-square-corrugated-cardboard-e-flute-pizza-box-microwave-safe-ov?id=360983",
         dims='14/16 × 1.88 in', board="E-flute kraft/kraft", printing="Plain", per_pack=50, moq="Account", price="Login required", ppb=None,
         shipping="Distributor terms", tax="n/a", ptype="Broadline distributor", avail="n/a", date="2026-10-16", comparability=4, sid="S079", note="Shows 14\"/16\" E-flute exists in US distribution."),
    dict(supplier="Aztec (Arvco)", product="14\" kraft fluted pizza box, 50/pack", url="https://www.aztekc.com/boxpizzaflute14kft50-arvco-containers/p",
         dims='14 × 14 × 1.75 in', board="Fluted kraft", printing="Plain", per_pack=50, moq="1 pack", price="n/a (weight 20 lb; 36×6×18 in)", ppb=None,
         shipping="n/a", tax="n/a", ptype="Distributor listing", avail="n/a", date="2026-10-16", comparability=3, sid="S080", note="Used to calibrate blank geometry."),
    dict(supplier="PMQ Think Tank (operators, anecdotal)", product="16\" boxes: franchise $0.442; importer container-scale B-flute $9.87/50", url="https://thinktank.pmq.com/t/corrugated-pizza-box-prices/1288",
         dims='16 in', board="B-flute / white", printing="Various", per_pack=50, moq="Container (importer)", price="$0.442 (franchise); $0.197 FOB-type (importer)", ppb=0.197,
         shipping="Before freight (importer)", tax="n/a", ptype="Forum anecdote (undated)", avail="n/a", date="undated", comparability=2, sid="S081", note="UNVERIFIED; indicates import competition at ~$0.20 FOB."),
    dict(supplier="Subject imports (China, Malaysia, Türkiye) – petition data", product="Corrugated pizza boxes, landed duty-paid value", url="https://www.paperadvance.com/news/industry-news/u-s-opens-probe-into-pizza-box-imports.html",
         dims='Mixed', board="Mixed", printing="Mixed", per_pack=None, moq="Container", price="$68.3m / 92.4m lb (2025) = $0.739/lb landed duty-paid", ppb=None,
         shipping="Landed duty-paid at port", tax="n/a", ptype="Import statistic (petitioner)", avail="n/a", date="2025 data", comparability=3, sid="S099",
         note="Import-parity cross-check per lb; allegedly dumped 97–569%."),
]

# ----------------------------------------------------------------------------- RFQ tracker
# Quotation clarification checklist for NFC (workbook Supplier Quotation §5; every item is asked in RFQ 1)
NFC_CLARIFICATIONS = [
    "Confirm the quotation is re-issued, dated and valid ≥30 days; state whether prices change with kraft-paper prices.",
    "Confirm Incoterm 2020 and named place: FCA [factory address, 6th of October] preferred (NFC loads and clears export). Quote EXW and FCA separately.",
    "Confirm whether NFC (as a registered exporter) will invoice the foreign buyer directly with VAT zero-rating, or whether VAT 14% will be charged.",
    "Issue the quote to the actual buying entity (the quote is addressed to 'ا/ انيس شركة توريدات', Alexandria, tax ID blank).",
    "Confirm SKU 3464 nominal size (document: 5*35.5*35.5; brief: '5 × 5 × 5.5 inch') and whether 305/355/405 × 50 mm are INSIDE or OUTSIDE dimensions.",
    "Confirm SKU 3460 is a complete pizza box (description lacks 'علبة').",
    "Explain why 3464 (355 mm) is priced at EGP 8.365 versus EGP 7.900 for the larger 3463 (405 mm).",
    "Define 'SINGLE-E': flute profile, liner and medium grammage, recycled content, food-contact surface, total g/m², caliper, ECT.",
    "Provide die-line drawings, flat blank dimensions, blanks per bundle, bundle size and weight, palletisation options.",
    "Provide container load plan: units per 20', 40', 40' HC for each SKU and for the 60,000 mix.",
    "Confirm payment terms: is 'advance_50' a 50% advance with balance against documents? Accept LC or escrow?",
    "Confirm tooling, die, plate, printing, sampling, packing or loading charges not shown on the quote.",
    "Confirm loading of export container at factory, labour included, loading time window.",
    "Provide food-contact documentation: declaration of compliance with 21 CFR 176.170/176.260, PFAS-free statement, heavy-metal (TPCH) certificate, test reports.",
    "Confirm 'Made in Egypt' marking on every bundle wrap/outer pack.",
    "Confirm production lead time, capacity per week and QC/AQL procedure; accept third-party pre-shipment inspection.",
    "Provide company registration documents (commercial registry extract, tax card, industrial registry) and a bank letter confirming the beneficiary account.",
    "Confirm the authorised signatory (signature 'Abdelrahman Darwish' vs printed name 'Mahmoud Bakr').",
]

RFQS = [
    ("RFQ 1", "Egyptian factory (NFC + 3 alternatives)", "Specs, current prices, packaging, load plan, documentation", "Not sent", "NFC, New Golden Pack, Cepack Group, WePack"),
    ("RFQ 2", "Egyptian freight forwarders (≥3)", "Itemised FCA/EXW collection, export clearance, ocean, destination, door delivery", "Not sent", "Forwarders with Egypt–USEC services"),
    ("RFQ 3", "US customs brokers (≥2)", "HTS, Section 301 status, valuation, fees, IOR/bond, marking, FDA/state compliance", "Not sent", "Licensed brokers at NY/NJ, Savannah"),
    ("RFQ 4", "US wholesale buyers (≥5)", "Demand, current prices, specs, volumes, receiving terms", "Not sent", "Pizza-segment distributors, cash-and-carry, regional chains"),
]
