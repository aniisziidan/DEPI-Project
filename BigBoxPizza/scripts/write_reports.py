"""Generate BigBoxPizza_US_Market_and_Landed_Cost_Report.md from the engine (no hand-typed results)."""
import json
import math
import os

import charts as CH
import engine as E
import inputs as I
import loading_model as LM
import registers as R
import sources_data as SD

SC = I.SCENARIOS
CODES = [k["code"] for k in I.SKUS]
NOM = {"3464": '14"', "3463": '16"', "3460": '12"'}


def usd(x, d=2):
    if x is None:
        return "n/a"
    s = f"{abs(x):,.{d}f}"
    return ("−$" if x < 0 else "$") + s


def pct(x, d=1, sign=False):
    if x is None:
        return "n/a"
    return (f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%").replace("-", "−")


def num(x, d=0):
    return f"{x:,.{d}f}".replace("-", "−")


def v(inp, s=1):
    return inp["v"][s]


def table(hdr, rows, align=None):
    out = ["| " + " | ".join(hdr) + " |", "|" + "|".join([(":---" if (align and align[i] == "l") else "---:") if align else "---" for i in range(len(hdr))]) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def max_exw(r, gm):
    """EGP per box (quote basis) for target GM at benchmark price – same linearisation as the workbook."""
    s = r["s"]
    out = {}
    for code in CODES:
        u = r["units"][code]
        if not u:
            out[code] = None
            continue
        sup = r["sup"][code]
        vat_e = sup * v(I.SUPPLIER["vat_rate"], s) if r["drivers"]["vatmode"] == 3 else 0.0
        cv = sup + vat_e + r["tooling"] * u / r["U"]
        duty = cv * (v(I.CUSTOMS["mfn"], s) + r["drivers"]["s301"])
        a = (vat_e + duty + (r["MPF"] + r["HMF"]) * cv / r["CV"] + r["INS"] * sup / r["SUP"]) / sup
        o = (r["cost"][code] - sup * (1 + a)) / u
        p = (r["price"][code] * (1 - gm) * (1 - r["drivers"]["dmg"]) - o) / (1 + a)
        out[code] = p * r["drivers"]["fx"] / ((1 + v(I.SUPPLIER["requote"], s)) * r["drivers"]["supfac"])
    return out


def url_block_note():
    """Sentence on source-site access, from the last check_urls.py run (outputs/url_check.json) if there is one."""
    up = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs", "url_check.json")
    if not os.path.exists(up):
        return "direct access to official websites was blocked by the network policy"
    u = json.load(open(up, encoding="utf-8"))
    web = [r for r in u["rows"] if r["host"] != "(local file)"]
    blocked = {r["host"] for r in web if r["result"] == "blocked_by_policy"}
    reach = sum(r["result"] == "reachable" for r in web)
    n = len({r["host"] for r in web})
    head = (f"the network policy blocked direct access to all {n} source websites" if len(blocked) == n and not reach
            else f"the network policy blocked direct access to {len(blocked)} of the {n} source websites ({reach} could be opened)")
    return head + f" (check of {u['checked_at'][:10]}) and to hts.usitc.gov, api.census.gov and NFC's domain nilecarton.com (tested 2026-10-15)"


def ctx():
    rows, base, sens, combos = E.run_all()
    idx = {(r["s"], r["ci"], r["di"]): r for r in rows}
    val = {}
    vp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs", "validation_report.json")
    if os.path.exists(vp):
        val = json.load(open(vp, encoding="utf-8"))
    return rows, base, sens, combos, idx, val


def report():
    rows, base, sens, combos, idx, val = ctx()
    b = base
    fx_cbe = v(I.FX["cbe"])
    fx = b["drivers"]["fx"]
    S = b["SALE"]
    comps = CH.cost_components(b)
    c4, c7 = idx[(1, 3, 0)], idx[(1, 6, 0)]
    # Guards: the narrative below states these model facts in words; the build stops if a model change contradicts them.
    lenient = lambda r: r["GM"] >= 0.05 and r["CM"] >= 0.0  # noqa: E731
    assert not any(lenient(r) for k, r in idx.items() if k[0] == 1), "narrative: every BASE configuration/destination fails lenient thresholds"
    assert any(lenient(r) for k, r in idx.items() if k[0] == 0), "narrative: the LOW scenario passes"
    assert max((r for k, r in idx.items() if k[0] == 1 and k[2] == 0), key=lambda r: r["CM"]) is c7, "narrative: C7 is the best BASE option"
    low1, st1 = idx[(0, 0, 0)], idx[(2, 0, 0)]
    rep = [r for l, r in sens if l.startswith("Repeat")][0]
    direct = [r for l, r in sens if l.startswith("Sell direct")][0]
    parity = [r for l, r in sens if "import-parity" in l][0]
    s301_0 = [r for l, r in sens if l.startswith("Section 301 duty 0%")][0]
    best_base = max((idx[(1, ci, 0)] for ci in range(len(I.CONFIGS))), key=lambda r: r["CONTRIB"])
    # geometry
    geo = {}
    for k in I.SKUS:
        for ck in ("20GP", "40GP", "40HC"):
            geo[(k["code"], ck)] = LM.capacity(k, LM.container_by_key(ck), 1)
    fits = {(ci, s): LM.config_feasibility(I.CONFIGS[ci], s) for ci in range(3) for s in range(3)}
    eqmix = {(ck, s): LM.best_equal_mix(LM.container_by_key(ck), s) for ck in ("20GP", "40GP", "40HC") for s in range(3)}
    m_c1 = LM.mixed_load({k["code"]: k["qty"] for k in I.SKUS}, LM.container_by_key("40HC"), 1)
    # LCL breakeven (BASE, D1) – same formula as Shipment Configuration sheet
    d1 = I.DESTINATIONS[0]
    fcl20 = (v(I.ORIGIN["truck_20"]) / fx + v(I.ORIGIN["terminal"]) + v(I.ORIGIN["othc_20"]) + v(I.ORIGIN["seal"]) + v(I.OCEAN["rate_20"])
             + d1["line"][1] * (1 + v(I.DRAY["fsc"])) + d1["tolls"][1] + v(I.DRAY["chassis_days"]) * d1["chassis"][1] + v(I.DRAY["unload_20"]))
    lclfix = v(I.ORIGIN["lcl_truck"]) / fx + v(I.ORIGIN["lcl_cfs_o"]) + v(I.DRAY["lcl_cfs_d"]) + v(I.DRAY["lcl_deliv"])
    be_m3 = max(0, (fcl20 - lclfix) / (v(I.OCEAN["lcl_rate"]) * v(I.OCEAN["lcl_factor"])))
    vpu_avg = sum(E.unit_props(1)[c]["vol"] for c in CODES) / 3
    be_units = be_m3 / vpu_avg
    up = E.unit_props(1)
    ldp_lb = 68.3 / 92.4
    clear_lb = (b["COGS"] - b["DELIV"] - b["UNLOAD"]) / (b["kg"] / 0.45359237)
    mx25_c1 = max_exw(b, 0.25)
    mx0_c1 = max_exw(b, 0.0)
    mx25_full = {c: max_exw(idx[(1, ci, 0)], 0.25)[c] for c, ci in (("3464", 4), ("3463", 5), ("3460", 6))}
    mx0_full = {c: max_exw(idx[(1, ci, 0)], 0.0)[c] for c, ci in (("3464", 4), ("3463", 5), ("3460", 6))}
    nsrc = len(SD.SOURCES)
    ev_counts = {}
    for s in SD.SOURCES:
        key = s["evidence"].split(" ")[0]
        ev_counts[key] = ev_counts.get(key, 0) + 1
    thr = I.THRESHOLDS

    L = []
    w = L.append
    w("# BigBoxPizza — Egypt → US East Coast pizza-box import")
    w("## Market validation, landed-cost model and commercial decision report\n")
    w(table(["Item", "Detail"], [
        ["Client", "BigBoxPizza (Egyptian-origin pizza-box export business)"],
        ["Supplier quotation", "Nile Factory Carton (NFC), offer NFC-OFFER-2026-0120 dated 23-Sep-2026, valid until 30-Sep-2026 (expired) [S001]"],
        ["Valuation date", "16-Oct-2026 (research started 2026-10-15 23:47 UTC)"],
        ["Deliverables", "This report; `BigBoxPizza_US_Landed_Cost_Model.xlsx`; `BigBoxPizza_Source_Register.csv`; `BigBoxPizza_Assumptions_and_Gaps.md`; `BigBoxPizza_RFQ_Pack.md`; `BigBoxPizza_Calculation_Audit.md`; `scripts/`"],
        ["Original quotation (preserved)", "`BigBoxPizza/evidence/NFC-OFFER-2026-0120_original.pdf` (SHA-256 ecfdf33b…f91b0); transcription `evidence/NFC-OFFER-2026-0120_transcription.md`"],
        ["Model status", f"Validated: recalculated in LibreOffice; {val.get('engine_rows_compared', 'n/a')} engine cases match an independent Python engine; {val.get('error_count', 'n/a')} formula errors"],
    ], align="ll"))
    w("")
    w("> **Evidence notice.** No written freight, broker, trucking, supplier re-quote or buyer quotations were available, so every logistics and market figure is an **estimate built from documented sources**, not a quoted or paid amount. "
      f"In this research environment {url_block_note()}; sources were read through search-engine extracts and are recorded as such in the source register. "
      "Re-verify every VERIFIED_OFFICIAL item on the live site before any shipment. This report is not legal or tax advice.\n")

    # ---------------------------------------------------------------- 1
    w("## 1. Executive verdict\n")
    w("**Verdict: NO-GO under the modeled conditions.** Do not pay the 50% advance and do not place the quoted 60,000-box order.\n")
    w("Why:\n")
    w(f"1. **Delivered cost is above what a US wholesale buyer can pay.** In the BASE case, the quoted order (one 40' high-cube to a customer in Edison, NJ) costs "
      f"**{usd(b['avg_cpb'], 3)} per saleable box delivered**. The evidence-based achievable wholesale price is **{usd(b['avg_price'], 3)}**. "
      f"That is a gross margin of **{pct(b['GM'])}** and a contribution of **{usd(b['CONTRIB'], 0)}** ({pct(b['CM'])}) on a cash outlay of {usd(b['CASH_TOTAL'], 0)}.")
    w(f"2. **No shipment configuration fixes it.** The best BASE option, a full 40' high-cube of 12\" boxes only, reaches a gross margin of {pct(c7['GM'], sign=True)} "
      f"and a contribution margin of {pct(c7['CM'])}. Every configuration fails even lenient thresholds (gross margin ≥5%, contribution ≥0). Only the LOW scenario, where every uncertain input turns favourable at once, passes.")
    w(f"3. **The gap is structural, not a rounding issue.** The NFC price alone is {pct(b['SUP'] / b['REV'])} of the achievable revenue. Ocean freight "
      f"({usd(b['OCEAN'] / S, 3)}/box), the 12.5% Section 301 duty on Egyptian goods ({usd(b['DUTY'] / S, 3)}/box) and delivery to the customer use up the rest. "
      f"NFC would have to cut its price by {pct(-b['chg_gm_0'], 0)} just to break even at gross-profit level, and by {pct(-b['chg_gm_t'], 0)} to reach a 25% gross margin on the quoted mix. "
      f"Alternatively, selling prices would need to be {pct(b['f_be'] - 1, 0)} higher than the benchmark.")
    w("4. **Several facts that are prerequisites for any shipment are missing.** The quote has expired and states no Incoterm. NFC's identity and bank beneficiary could not be verified "
      "(no independent public record was found [S088]). The board specification and food-contact/PFAS documentation are absent. "
      "\"SINGLE-E\" 14\" and 16\" boxes are lighter than the US B-flute norm for those sizes [S073][S082], and it is unclear whether the quoted dimensions are inside or outside measurements.\n")
    w("**What would have to change before re-opening the file (re-entry conditions; all are needed together, see §18–19):**")
    w(f"- Written buyer offers for container lots that clear the break-even prices in §13: about **{usd(b['avg_price'] * b['f_be'], 3)}/box** for the quoted mix, or about **{usd(c7['avg_price'] * c7['f_be'], 3)}/box** for full containers of 12\" boxes.")
    w(f"- A dated NFC re-quote on FCA terms, zero-rated for VAT, at or below the maximum prices in §16. For a full 40' HC of 12\" boxes and a 25% gross margin that maximum is **EGP {mx25_full['3460']:.2f}/box**, against EGP 6.90 quoted.")
    w("- Broker confirmation of the duty position. Removing the 12.5% duty alone is not enough (§13).")
    w("- Verified supplier identity, specifications and compliance documents.\n")
    tst = I.SELLING["testing"]["v"]
    w(f"**Recommended next step:** stop the transaction. If BigBoxPizza wants to keep the option open, run a low-cost \"paper pilot\" (§17) costing about the model's sample, courier and lab-testing budget ({usd(tst[1], 0)}; range {usd(tst[0], 0)}–{usd(tst[2], 0)}, ESTIMATED). "
      "It covers samples to US buyers, written buyer prices, an FCA re-quote and forwarder/broker quotes. Re-run this model with those quotes before any money is committed to a shipment.\n")

    # ---------------------------------------------------------------- 2
    w("## 2. One-page decision summary\n")
    qa = [
        ["1. Is the NFC quotation still valid?", "No. It expired on 30-Sep-2026. Reconfirm the price, validity, Incoterm (FCA preferred), the buying entity, VAT treatment, payment milestones and inclusions in writing (RFQ 1)."],
        ["2. Are the quoted prices competitive?", f"Not for the US. At {usd(b['SUP'] / b['U'], 3)}/box ex-works (CBE rate), NFC's price alone already absorbs {pct(b['SUP'] / b['REV'], 0)} of the achievable US wholesale revenue. 3464 (355 mm) is priced above the larger 3463 (405 mm), which is an anomaly."],
        ["3. Are the specifications sufficient?", "No. 'SINGLE-E' does not establish flute, grammage, recycled content, coatings, strength or food-contact compliance. Inside versus outside dimensions are unknown."],
        ["4. How many boxes fit per container?", f"Provisional (BASE): an equal mix of the three sizes tops out at about {3 * eqmix[('40HC', 1)]:,} boxes per 40' HC ({eqmix[('40HC', 1)]:,} of each size), "
                                                   f"{3 * eqmix[('40GP', 1)]:,} per 40' GP ({eqmix[('40GP', 1)]:,} each) and {3 * eqmix[('20GP', 1)]:,} per 20' ({eqmix[('20GP', 1)]:,} each). Single SKU per 40' HC: 14\" {geo[('3464', '40HC')]['real_units']:,}, 16\" {geo[('3463', '40HC')]['real_units']:,}, 12\" {geo[('3460', '40HC')]['real_units']:,}. Volume always binds, never weight."],
        ["5. Can the quoted 60,000 mix ship economically?", f"It fits one 40' HC in every scenario (a 40' GP fails under STRESS bundle thickness), but at {pct(b['GM'])} gross margin it is not economic."],
        ["6. Delivered cost per box by SKU (BASE)?", f"3464 {usd(b['cpb']['3464'], 4)}; 3463 {usd(b['cpb']['3463'], 4)}; 3460 {usd(b['cpb']['3460'], 4)}; average {usd(b['avg_cpb'], 4)} (quoted order, NY/NJ → Edison)."],
        ["7. Total cash needed?", f"{usd(b['CASH_TOTAL'], 0)} in total; peak working capital {usd(b['PEAK'], 0)}; {usd(b['out0'], 0)} before shipment. Recoverable VAT is shown as cash, not cost."],
        ["8. Tariff treatment supported by evidence?", "HTS 4819.10.00 at Free MFN, plus Section 301 forced-labor duty of 12.5% on products of Egypt (9903.05.36) from 24-Jul-2026 unless an Annex II exemption applies [S014–S018]. IEEPA tariffs were struck down and the Section 122 surcharge has expired."],
        ["9. Best gateway (risk-adjusted)?", f"New York/New Jersey → Edison, NJ: {usd(idx[(1, 0, 0)]['avg_cpb'], 4)}/box, with direct Egypt–NY services. Baltimore → Jessup is {usd(idx[(1, 0, 2)]['avg_cpb'], 4)}, slightly cheaper, but rests on an assumed port differential and fewer Med services."],
        ["10. Price needed for target margins?", f"25% GM on the quoted mix needs an average of {usd(b['avg_cpb'] / 0.75, 3)}/box, against the {usd(b['avg_price'], 3)} benchmark (see §13)."],
        ["11. What do comparable US products sell for?", "Online restaurant-supply price for 12\" E-flute is about $0.30–0.32. For 14\"/16\" B-flute it is $0.38–0.46, and $0.47–0.48 at club stores. These are asking prices, not transaction prices; reliability is medium."],
        ["12. Can BigBoxPizza compete?", f"Not at NFC's quoted prices. Cleared at the port, the quoted order costs about {usd(clear_lb, 2)}/lb, against {usd(ldp_lb, 2)}/lb for imports that the US industry alleges are dumped by 97–569% [S098][S099]."],
        ["13. Expected contribution per shipment?", f"BASE, quoted order: {usd(b['CONTRIB'], 0)} on a first shipment and {usd(rep['CONTRIB'], 0)} on a repeat shipment. LOW: {usd(low1['CONTRIB'], 0)}. STRESS: {usd(st1['CONTRIB'], 0)}."],
        ["14. What could reverse the decision?", "Only a combination of four things: much higher written buyer prices, a far lower NFC price, no Section 301 duty and low freight (§13 path to viability)."],
        ["15. What to negotiate with NFC?", "FCA terms with a zero-rated USD invoice, price cuts toward the maxima in §16, single-size full loads, specs and documents, 30/70 or LC payment, and validity."],
        ["16. What must the forwarder and broker confirm?", "Itemised door rates per gateway, free time and inclusions; HTS, Section 301 applicability, valuation, marking, bond and IOR set-up."],
        ["17. Buyer evidence needed first?", "Written prices or LOIs from at least 3 buyers for specified boxes, covering at least 70% of a container at or above break-even, after sample approval."],
        ["18. Next step?", "NO-GO now. Optional paper pilot, then re-run the model with real quotes."],
    ]
    w(table(["Question", "Answer"], qa, align="ll"))
    w("")

    # ---------------------------------------------------------------- 3
    w("## 3. Quotation assessment\n")
    w("**What the document actually says** (verbatim transcription in `evidence/NFC-OFFER-2026-0120_transcription.md`):\n")
    qrows = []
    for k in I.SKUS:
        qrows.append([k["code"], k["desc_ar"], k["desc_brief"], "SINGLE-E", f"{k['L']}×{k['W']}×{k['H']}", f"{k['qty']:,}", f"{k['price_egp']:.3f}",
                      f"{k['line_total']:,.0f}", usd(k['price_egp'] / fx, 4)])
    w(table(["Code", "Description (printed, Arabic)", "Brief's transcription", "Spec", "L×W×H mm", "Qty", "EGP/box", "Line EGP", "USD/box*"], qrows))
    w(f"\n\\*At the effective rate of {fx:.4f} EGP/USD (CBE buy rate {fx_cbe} on 15-Oct-2026 [S063], less a 0.5% bank spread).\n")
    w(f"- Totals reconcile: subtotal EGP 463,300; 14% tax EGP 64,862; total EGP 528,162; 60,000 pcs. The arithmetic checks are automated in the workbook.")
    w(f"- **The brief's description of SKU 3464 (\"5 × 5 × 5.5 inch\") does not match the document.** The document prints \"علبة بيتزا 5\\*35.5\\*35.5\" (pizza box 5×35.5×35.5), which is consistent with 355×355×50 mm. "
      "No description states a unit, and SKU 3460 lacks the word for \"box\". These points are flagged, not corrected.")
    w("- **No Incoterm is printed**, and \"Shipping\" is a dash. EXW is only the brief's working assumption.")
    w("- **Addressee:** the offer is made to a domestic buyer, \"ا/ انيس شركة توريدات\" (Alexandria, client code C330, tax ID blank), with 14% Egyptian VAT added. A direct export sale by a registered exporter would normally be zero-rated [S060][S062].")
    w("- **Validity:** expired 16 days before the valuation date. The prices are historical reference values (BASE re-quote change 0%; LOW −5%; STRESS +10%).")
    w(f"- **Payment:** \"advance_50\" is read provisionally as a 50% advance. The bank block prints \"FAP MISR BANK\" with SWIFT NBADEGCAXXX (the NBAD prefix historically belongs to First Abu Dhabi Bank, so the name may be a typo for \"FAB Misr\"). "
      "The IBAN passes the mod-97 check, which validates the format only. The signature reads \"Abdelrahman Darwish\" while the printed name is \"Mahmoud Bakr\". **Verify the beneficiary independently before any transfer.**")
    pa = []
    for k in I.SKUS:
        bl = LM.blank(k, 1)
        pa.append([k["code"], NOM[k["code"]], f"{k['L'] * k['W'] / 1e6:.4f}", f"{k['price_egp'] / (k['L'] * k['W'] / 1e6):.2f}", f"{bl['area'] * 0.92:.4f}",
                   f"{k['price_egp'] / (bl['area'] * 0.92):.2f}", f"{k['price_egp'] * 1000:,.0f}"])
    w("\nPrice sanity check. Plan area is a preliminary measure only; board area uses the provisional blank estimate in §5.\n")
    w(table(["SKU", "Nominal", "Plan area m²", "EGP per m² plan", "Est. board m²", "EGP per m² board", "EGP per 1,000"], pa))
    board = {k["code"]: k["price_egp"] / (LM.blank(k, 1)["area"] * 0.92) for k in I.SKUS}
    oth = [board[c] for c in CODES if c != "3463"]
    w(f"\nThe 16\" box (3463) is the cheapest per m² of board (≈EGP {board['3463']:.1f}, against {min(oth):.1f}–{max(oth):.1f} for the others), and the 14\" box costs more per unit than the 16\". "
      f"This needs an explanation (different board or print, a mis-key, or loss-leading) before the quote can be relied on. The weighted average is EGP {463300 / 60000:.2f}/box, "
      f"or {usd(463300 / 60000 / fx, 4)}. The {len(R.NFC_CLARIFICATIONS)}-item clarification checklist is in the workbook (Supplier Quotation §5); RFQ 1 covers every item.\n")
    w("**Tax views modelled (no double counting):**")
    w(table(["Mode", "Treatment", "Cash effect", "Economic cost", "When it applies"], [
        ["1", "Zero-rated direct export", "No VAT", "Nil", "NFC (a registered exporter) invoices the foreign buyer and exports [S060][S062]"],
        ["2 (BASE)", "VAT paid, refunded", f"{usd(b['VAT_CASH'], 0)} out, refund about {v(I.SUPPLIER['vat_lag'])} days after export", "Financing cost only", "An Egyptian trading company buys domestically and exports. Statutory 45-day refund [S060]; ETA target 20 days [S061]"],
        ["3 (STRESS)", "VAT paid, not recovered", "Out, no refund", f"+{usd(b['SUP'] * 0.14 / S, 4)}/box; also enters customs value", "Buyer is not a registered exporter or cannot claim"],
    ], align="lllll"))
    w("")

    # ---------------------------------------------------------------- 4
    w("## 4. Product specification assessment\n")
    w("- **\"SINGLE-E\"** most plausibly means single-wall E-flute corrugated board: about 1/16\" (1.2–1.8 mm) thick with 90–100 flutes per foot. "
      "US 14\"–18\" pizza boxes are normally **B-flute** (about 1/8\", 47–53 flutes per foot), which is stiffer and insulates better [S082][S073]. "
      "E-flute is mainstream for 10\"–12\" (for example the WebstaurantStore E-flute 12\" [S074]) and niche for 14\"/16\" (Arvco E-flute via Imperial Dade [S079]).")
    w("- **Fit:** 305/355/405 mm = 12.0/13.98/15.94 in. US boxes are specified by inside size. If NFC's figures are outside dimensions, the 16\" box may not accept a 16\" pizza.")
    w("- **Food-contact suitability is unproven.** Pizza is a fatty food, so the food-contact surface must consist of substances permitted under 21 CFR 176.170 [S030]. "
      "Recycled fibre must meet the reclaimed-fibre conditions, and adhesives and inks must also be covered. No declaration or test data was supplied.")
    w("- **Weight benchmarks (calibration):** WebstaurantStore 12\" E-flute ≈136 g/box [S074] and 14\" B-flute ≈189 g/box [S073]. "
      f"The model estimates NFC blanks at {LM.blank(I.SKUS[2], 1)['weight'] * 1000:.0f}/{LM.blank(I.SKUS[0], 1)['weight'] * 1000:.0f}/{LM.blank(I.SKUS[1], 1)['weight'] * 1000:.0f} g (12\"/14\"/16\", about 420 g/m²).")
    w("- **Minimum pre-shipment testing plan** (workbook, Technical Specifications §4):")
    w("  - dimension and real-pizza fit;")
    w("  - grammage and caliper;")
    w("  - edge-crush and flat-crush strength;")
    w("  - Cobb water absorption and grease resistance;")
    w("  - PFAS total-fluorine screen, legally relevant in New York and Maryland;")
    w("  - TPCH heavy-metals test;")
    w("  - review of the supplier's food-contact declaration;")
    w("  - odour test and an assembly trial.")
    w("  The methods cited (ISO 536/3034/3037/3035/535, TAPPI T 811/T 441/T 559, EN 1230) are commonly used, not legally mandatory. Budget: $1,000–4,000 per shipment (PFAS screens cost a few hundred dollars per sample [S092]).\n")

    # ---------------------------------------------------------------- 5
    w("## 5. Container-loading feasibility (critical gate)\n")
    w("**Method.** The finished footprint is *not* used as the flat size. The model:")
    w("1. Estimates each flat blank with a parametric die-line rule calibrated on a US 14\" box listed at 36×18 in [S080]: length = 2L + 4.5H, width = W + 2H + 13 mm.")
    w("2. Assumes 50 blanks per bundle and a 1.6 mm stacking pitch (BASE).")
    w("3. Floor-packs bundles with a row-mix pattern implemented as formulas. An exhaustive guillotine dynamic program validates it and finds no better layout in any of the 27 cases.")
    w("4. Stacks full-height columns, limited by the lower of usable height and door height.")
    w("5. Gives each SKU its own block of container length for mixed loads.")
    w("6. Divides required bundles by an operational loading efficiency (97/95/90%) before the geometric test.")
    w("7. Tests weight separately against US road limits of about 17.2 t for a 20' and 20.0 t for a 40' [S043][S096].")
    w("Container data are DSV representative specifications [S041]. **All of this is PROVISIONAL until NFC supplies die-lines, bundle data and a load plan.**\n")
    cap_rows = []
    for k in I.SKUS:
        for ck in ("20GP", "40GP", "40HC"):
            g = geo[(k["code"], ck)]
            bd = g["bundle"]
            cap_rows.append([k["code"], ck, f"{bd['a']:.0f}×{bd['b']:.0f}×{bd['h']:.0f}", g["positions"], g["layers"], f"{g['theo_units']:,}", f"{g['real_units']:,}",
                             g["binding"], pct(g["cube_util"], 0), pct(g["payload_util"], 0)])
    w(table(["SKU", "Container", "Bundle mm (est.)", "Floor stacks", "Layers", "Geometric max", "Realistic units", "Binding", "Cube util", "Road-payload util"], cap_rows))
    w("\n**Does the quoted 60,000 mix fit?**\n")
    fr = []
    for ci, name in ((0, "One 40' HC"), (1, "One 40' GP"), (2, "Two 20' GP")):
        cells = []
        for s in range(3):
            f = fits[(ci, s)]
            pc = f["per_container"]
            cells.append(("Yes" if f["fits"] else "**No**") + f" ({pc['tot_len'] / 1000:.2f} of {pc['Lu'] / 1000:.2f} m)")
        fr.append([name] + cells)
    w(table(["Equipment", "LOW (1.5 mm)", "BASE (1.6 mm)", "STRESS (1.8 mm)"], fr))
    w(f"\nIn BASE the quoted order uses {m_c1['tot_len'] / 1000:.2f} m of the 40' HC's {m_c1['Lu'] / 1000:.2f} m usable length "
      f"({pct(m_c1['len_util'], 0)} length, {pct(m_c1['cube_util'], 0)} cube, {m_c1['tot_kg']:,.0f} kg against a {m_c1['road_kg']:,} kg road limit). "
      "**Recommended equipment for the quoted order: one 40' high-cube.** A 40' GP is about $100 cheaper but fails if bundles are thicker (STRESS). "
      "Two 20' GPs cost more and fail under STRESS.\n")
    w(table(["Maximum equal-units mix per container", "LOW", "BASE", "STRESS"], [
        [ck, *[f"{3 * eqmix[(ck, s)]:,} ({eqmix[(ck, s)]:,} per SKU)" for s in range(3)]] for ck in ("40HC", "40GP", "20GP")]))
    eq20 = 3 * eqmix[("20GP", 1)]
    w(f"\n**Dedicated container vs LCL:** with the assumed all-in LCL rate of {usd(v(I.OCEAN['lcl_rate']), 0)}/W-M (no LCL quote was found), a 20' FCL becomes cheaper than LCL at about "
      f"**{be_m3:.0f} m³ of bundles ≈ {be_units:,.0f} boxes** of an equal mix, about {pct(be_units / eq20, 0)} of a full equal-mix 20' ({eq20:,} boxes). "
      "Below that, LCL is cheaper per shipment, but every small shipment loses money (see §14). A container is never economically *attractive* at BASE prices.\n")
    w("![Quoted order in one 40' HC](outputs/loading_quoted_40HC_BASE.png)\n")
    w("![Quoted order in one 40' GP under STRESS – does not fit](outputs/loading_quoted_40GP_STRESS.png)\n")
    w("Handling implications: floor-loaded flat bundles (about 1,200 bundles and 10.3 t for the quoted order) need hand unloading, typically 3–4 hours. Moisture protection (liners, desiccants) is advisable. "
      "If the buyer requires pallets, they must be ISPM-15 heat-treated [S090], and pallets reduce container capacity.\n")

    # ---------------------------------------------------------------- 6
    w("## 6. Import classification and tariff findings\n")
    w(table(["Layer", "Finding", "Evidence"], [
        ["Classification", "**HTS 4819.10.00**, cartons, boxes and cases of corrugated paper or paperboard; flat die-cut blanks are classified as the box (GRI 2(a)). Statistical suffix probably **.0020** (sanitary food containers), otherwise .0040", "[S010][S011][S012][S013]"],
        ["MFN duty", "**Free.** Alternatives 4819.20, 4823.90.86 and 4808.10 are also Free, so classification does not move ordinary duty", "[S010][S101]"],
        ["Section 301 forced-labor action", "**12.5% additional ad valorem on products of Egypt, heading 9903.05.36, from 24-Jul-2026** (FR 28-Jul-2026). Exempt only if listed in Annex II Part A (2,120 codes: energy, critical minerals, precious metals, certain agricultural inputs, aircraft/pharma end-use), Section 232 goods, Ch. 98 or USMCA. No evidence that 4819.10 is exempt. CIT challenge argued 30-Sep-2026, no ruling", "[S014][S015][S016][S017][S018][S020]"],
        ["IEEPA \"reciprocal\" 10%", "Struck down by the Supreme Court on 20-Feb-2026 (Learning Resources v. Trump); collection stopped 23-Feb-2026", "[S021]"],
        ["Section 122 surcharge 10%", "Ran 24-Feb to 24-Jul-2026; expired at the statutory 150-day limit", "[S022]"],
        ["Section 232 (timber and derivatives)", "Covers lumber, certain furniture and cabinets. Chapter 48 boxes not covered per summaries", "[S023]"],
        ["AD/CVD", "Petitions filed 9-Sep-2026 against corrugated die-cut (pizza) boxes from **China, Malaysia and Türkiye** (Smurfit Westrock, Pratt and the USW). **Egypt is not named**", "[S097][S098][S100]"],
        ["QIZ preference", "Requires a QIZ-registered producer and 10.5% Israeli content; interaction with Section 301 unconfirmed. Not modelled", "[S071]"],
    ], align="lll"))
    w("\n**Distinguishing the five layers the brief asks for (quoted order, BASE):**\n")
    w(table(["Layer", "Value"], [
        ["Statutory rate", "MFN Free + 12.5% Section 301 (Egypt)"],
        ["Legally applicable treatment", "12.5% probable, pending broker confirmation of no Annex II exemption"],
        ["Amount calculated", f"{usd(b['DUTY'])} duty on a customs value of {usd(b['CV'])}; MPF {usd(b['MPF'])} (FY2027 minimum applies); HMF {usd(b['HMF'])}"],
        ["Amount quoted by a provider", "No quote obtained yet (RFQ 3)"],
        ["Final amount paid", "Unknown until entry"],
    ], align="ll"))
    w("\n**Customs value** = the price actually paid. For a proven ex-factory/FCA-factory purchase, Egyptian inland freight is not added [S026], and international freight and insurance are excluded. "
      "Additions would be buyer-paid packing, assists such as tooling, commissions and royalties. Non-recoverable Egyptian VAT (mode 3) is part of the price paid; refunded or zero-rated VAT is not. "
      "**Fees:**")
    w("- MPF 0.3464% with a FY2027 minimum of $34.58 and maximum of $670.86 [S024];")
    w("- HMF 0.125% [S025];")
    w("- single-transaction bond at about $4–7 per $1,000 of face value (minimum $50–75) [S038];")
    w("- ISF 10+2 filing, due at least 24 hours before lading, with $5,000 liquidated damages for failures [S037];")
    w("- broker entry fee $150–300 [S039].")
    w("A broker classification note is sufficient for a first shipment. A binding ruling (CBP) is optional, because no MFN difference is at stake.\n")

    # ---------------------------------------------------------------- 7
    w("## 7. U.S. compliance requirements\n")
    w(table(["Requirement", "Applies?", "What to obtain from NFC / do", "Evidence"], [
        ["FDA food-additive regulations for paper/paperboard food-contact surfaces (fatty food: 21 CFR 176.170; dry food: 176.180; recycled fibre; adhesives)", "Yes – legal requirement on the product", "Supplier declaration of compliance listing the regulations; supporting test or extraction data", "[S030]"],
        ["FDA food-facility registration and prior notice", "No – food-contact substances are excluded from 'food' for these rules", "Broker to confirm that HTS 4819.10 is not FDA-flagged", "[S036]"],
        ["PFAS in food packaging", "Prohibited (intentionally added) in **New York** (ECL 37-0209, since 31-Dec-2022) and **Maryland** (from 1-Jan-2024); FDA reports PFAS grease-proofers off the US market", "PFAS-free declaration and total-fluorine test", "[S031][S032][S033][S034]"],
        ["Toxics in Packaging (Pb+Cd+Hg+Cr⁶⁺ ≤ 100 ppm)", "Yes in TPCH states (e.g., NY, NJ, CT, RI)", "Certificate of compliance plus a metals test of board and inks", "[S035]"],
        ["Country-of-origin marking", "Yes – 'Made in Egypt'. Outer-pack marking likely suffices where restaurants that fill the boxes are the ultimate purchasers", "Marking on every bundle wrap; broker confirmation", "[S027][S028]"],
        ["Wood packaging (ISPM-15)", "Only if pallets are used", "HT-stamped pallets", "[S090]"],
        ["ISF 10+2, customs bond, IOR identity (CBP Form 5106)", "Yes", "IOR set-up before booking", "[S037][S038][S040]"],
    ], align="llll"))
    w("\nA generic certificate or a statement of 'FDA approval' does not prove compliance: FDA does not approve packaging items. Buyers will ask for the declaration and test data.\n")

    # ---------------------------------------------------------------- 8
    w("## 8. Origin cost analysis (Egypt)\n")
    w("EXW leaves loading and export clearance to the buyer. But only parties registered in Egypt's Exporters Register may export [S062], and the ICC itself encourages FCA instead of EXW for cross-border sales [S072]. "
      "**Request FCA [NFC factory] Incoterms 2020 with NFC as exporter of record**, and an EXW price for comparison. The model keeps the EXW price and adds origin costs explicitly.\n")
    orow = [
        ["Inland trucking factory → Alexandria/Dekheila (EGP 14,000)", usd(v(I.ORIGIN['truck_40']) / fx), "ESTIMATED", "S066 S067 S068"],
        ["Terminal receiving + VGM weighing", usd(v(I.ORIGIN['terminal'])), "VERIFIED_MARKET", "S069"],
        ["Origin THC (40')", usd(v(I.ORIGIN['othc_40'])), "VERIFIED_MARKET", "S050"],
        ["Seal", usd(v(I.ORIGIN['seal'])), "ASSUMED", "–"],
        ["Export clearance and documents (EGP 6,000)", usd(v(I.ORIGIN['clearance']) / fx), "ASSUMED", "S062"],
        ["Certificate of origin (EGP 1,000, optional)", usd(v(I.ORIGIN['coo']) / fx), "ASSUMED", "–"],
        ["B/L & documentation", usd(v(I.ORIGIN['bl_fee'])), "ASSUMED", "S050"],
        ["Forwarder origin handling", usd(v(I.ORIGIN['fwd_fee'])), "ASSUMED", "–"],
        ["Pre-shipment QC inspection", usd(v(I.ORIGIN['qc'])), "ASSUMED", "–"],
        ["Bank wires (4)", usd(v(I.ORIGIN['wires']) * v(I.ORIGIN['wire_fee'])), "ASSUMED", "–"],
        ["**Total origin (one 40' HC)**", f"**{usd(b['ORIGIN'])}** = {usd(b['ORIGIN'] / S, 4)}/box", "", ""],
    ]
    w(table(["Line (BASE)", "USD", "Evidence", "Source"], orow, align="lrll"))
    w("\nSTRESS adds an export inspection ($64), 3 days of origin detention (at $28/day [S070]), factory loading labour and higher trucking. Excluded with justification: Egypt's ACI regime (import-only) and the export rebate programme (not assessed).\n")

    # ---------------------------------------------------------------- 9
    w("## 9. Freight and port comparison\n")
    w("Routing: Alexandria, Dekheila or Damietta to the US East Coast, with Hapag-Lloyd, MSC and ONE indicating 25–33 days to New York [S049]. Most services transship at a Mediterranean hub (22–35 days) [S051]. "
      "No written quote was obtained, so the ocean rate is **ESTIMATED** from documented anchors:\n")
    w(table(["Anchor", "Value", "Date", "Use"], [
        ["CMA CGM FAK Genoa→New York (incl. origin/destination THC, excl. bunker/AMS/ETS/peak surcharges)", "$2,750 per 20' / $3,600 per 40'", "from 1-Apr-2026", "BASE anchor [S047]"],
        ["Hapag-Lloyd GRI Egypt→North America", "+$300 per 20' / +$600 per 40' and HC", "from 1-Jul-2026", "STRESS add-on [S048]"],
        ["FBX22 Europe→USEC", "$2,723/FEU", "2-Oct-2026", "LOW anchor [S045]"],
        ["Drewry WCI Rotterdam→New York", "≈$3,116/40'", "8-Oct-2026", "Cross-check [S044]"],
        ["Xeneta N. Europe→USEC", "$2,741/FEU", "12-Aug-2026", "Cross-check [S046]"],
    ], align="llll"))
    w(f"\nModel (USD per container, excluding origin THC): 20' {'/'.join(num(x) for x in I.OCEAN['rate_20']['v'])}; 40' {'/'.join(num(x) for x in I.OCEAN['rate_40']['v'])}; "
      f"40' HC {'/'.join(num(x) for x in I.OCEAN['rate_hc']['v'])} (LOW/BASE/STRESS). Port differentials (BASE): Baltimore +$150 (ASSUMED), Savannah +$100 [S053], NY/NJ and Norfolk +$0. "
      f"Insurance is ICC(A) at 0.25% of (CIF + 10%) with a $75 minimum [S089]; it is not included in EXW/FCA or in freight. Ocean freight is {pct(b['OCEAN'] / b['COGS'], 0)} of delivered cost "
      f"({usd(b['OCEAN'] / S, 4)}/box), the largest cost after the product.\n")

    # ---------------------------------------------------------------- 10
    w("## 10. Destination delivery comparison\n")
    drows = []
    for di, d in enumerate(I.DESTINATIONS):
        r = idx[(1, 0, di)]
        drows.append([f"{d['port_name']} → {d['city']}", d["miles"], usd(r["DELIV"], 0), usd(r["UNLOAD"], 0), usd(r["OCEAN"], 0), usd(r["avg_cpb"], 4), pct(r["GM"])])
    w(table(["Gateway → representative customer location", "Miles", "Drayage + accessorials", "Unloading", "Ocean incl. port diff", "Delivered cost/box", "GM"], drows, align="lrrrrrr"))
    w("\nDrayage covers linehaul, a fuel surcharge (20%), tolls, 2 chassis days and 2 hours of waiting while floor-loaded bundles are hand-unloaded, plus unloading at $450 per 40'. "
      "These are distance-band estimates [S052][S053][S054][S055], **not quotes**. The disruption case (STRESS) adds a CBP exam, 3 days of demurrage, pre-pull/storage, a dry run and 5 chassis days. "
      "The choice of gateway moves cost by only about 1–2 cents a box; it does not change the verdict. **Risk-adjusted preference:** NY/NJ → Edison. It has the direct Egypt–New York services and the lowest cost among well-served gateways; Baltimore → Jessup is a close alternative. "
      "Savannah → Atlanta is the most expensive because of its 250-mile inland haul.\n")

    # ---------------------------------------------------------------- 11
    w("## 11. Competitor price benchmarking\n")
    crow = []
    for c in R.COMPETITORS:
        crow.append([c["supplier"], c["product"], c["price"], (usd(c["ppb"], 3) if c["ppb"] else "n/a"), c["ptype"], f"{c['comparability']}/5", f"[{c['sid']}]"])
    w(table(["Supplier", "Product", "Published price", "$/box", "Price type", "Comparability", "Src"], crow, align="lllrlll"))
    mrows = []
    for k in I.SKUS:
        c = k["code"]
        vals = []
        for s in range(3):
            lst = I.MARKET["listing"][c]["v"][s]
            disc = I.MARKET["eflute_disc"]["v"][s] if k["bench_flute"] == "B" else 0
            vals.append(lst * (1 - disc) * (1 - I.MARKET["dist_margin"]["v"][s]))
        mrows.append([f"{c} ({NOM[c]})", k["bench_flute"], *[usd(x, 3) for x in vals]])
    w("\n**Achievable wholesale price.** This is the most a container-lot buyer could pay and still resell at the observed listing price:\n\n"
      "Achievable price = listing × (1 − E-flute discount, applied only to B-flute listings) × (1 − buyer's resale margin).\n\n"
      "The 20% E-flute discount is derived from WebstaurantStore's own E-flute vs B-flute 12\" prices ($15.99 against $19.99) [S074][S075]. The buyer's resale margin is ASSUMED at 20/25/30%.\n")
    w(table(["SKU", "Benchmark listing flute", "LOW", "BASE", "STRESS"], mrows))
    par_box = (ldp_lb * b["kg"] / 0.45359237 + b["DELIV"] + b["UNLOAD"]) / b["SALE"]
    w(f"\n**Import-parity cross-check.** The pizza-box AD/CVD petition reports 92.4 million lb of subject imports with a landed duty-paid value of $68.3 million in 2025, about **${ldp_lb:.3f}/lb** [S099]. "
      f"BigBoxPizza's quoted order would land, cleared at the port, at **${clear_lb:.3f}/lb**. That is no better than imports the US industry calls dumped, and it still excludes delivery, selling costs and margin. "
      f"Applied to the quoted mix's weight and adding delivery to the buyer, that import price is about {usd(par_box, 3)}/box, {pct(par_box / b['avg_price'] - 1, 0)} above the benchmark "
      f"(before any importer margin). Even pricing 25% above the benchmark gives only {pct(parity['GM'], sign=True)} GM and {pct(parity['CM'])} CM on the quoted order.\n")
    w("**Market structure and buyers:**")
    w("- **Size:** about 75,700 US pizzerias, ~$49.5bn revenue [S083]. The top four chains run about 28% of units and buy custom-printed boxes under contract [S084].")
    w("- **Supply:** US production is about 3 billion pizza boxes a year, led by integrated mills including Smurfit Westrock and Pratt [S098].")
    w("- **Channels:** independents buy through broadline and pizza-specialist distributors (e.g., PFG's Roma, Elizabeth NJ [S085]), disposables distributors, cash-and-carry and online restaurant supply.")
    w("- **Realistic first buyers:** regional pizza-segment distributors, disposables distributors and multi-unit pizza groups that can take a full container and unload it.")
    w("- **Demand evidence:** none was obtained, and none is assumed. A 20,000-per-size lot is small for a distributor (a few weeks' supply) but large for a single pizzeria.\n")
    w("**Competitive position:**")
    w("- **Price:** NFC's product, delivered, is not cheaper than US or imported alternatives.")
    w("- **Quality:** E-flute is weaker and lighter than the B-flute norm at 14\"/16\".")
    w("- **Documentation:** missing.")
    w("- **Lead time:** about 2–3 months door to door against days domestically.")
    w("- **Conclusion:** Egyptian manufacturing offers no credible delivered-cost advantage at these prices.\n")

    # ---------------------------------------------------------------- 12
    w("## 12. Landed cost by SKU (quoted order, one 40' HC, NY/NJ → Edison NJ, BASE)\n")
    lab = ["Supplier price (EXW)", "Egypt origin", "Ocean freight + insurance", "Duty (§301) + MPF + HMF", "US entry & port fees", "Delivery & unloading"]
    lrows = []
    for j, l in enumerate(lab):
        lrows.append([l] + [usd(comps[c][j], 4) for c in CODES])
    lrows.append(["**Delivered cost per saleable box**"] + [f"**{usd(b['cpb'][c], 4)}**" for c in CODES])
    lrows.append(["per 1,000 boxes"] + [usd(b["cpb"][c] * 1000, 2) for c in CODES])
    lrows.append(["in EGP (scenario FX)"] + [f"EGP {b['cpb'][c] * fx:.3f}" for c in CODES])
    lrows.append(["Achievable wholesale price"] + [usd(b["price"][c], 4) for c in CODES])
    lrows.append(["Gross margin"] + [pct((b["price"][c] - b["cpb"][c]) / b["price"][c]) for c in CODES])
    w(table(["Per saleable box (USD)", "3464 (14\")", "3463 (16\")", "3460 (12\")"], lrows, align="lrrr"))
    w("\nAllocation: the supplier price and duty are assigned directly by SKU, MPF/HMF by customs value and insurance by supplier value. Container-driven costs (origin per container, ocean, port, drayage, unloading) are allocated by bundle volume, and per-shipment admin by units. "
      "Damage and rejection (1.5%) reduce saleable units.\n")
    w("![Delivered cost vs achievable price](outputs/chart_cost_stack_vs_price.png)\n")
    w("**The eight measures, which are not interchangeable:**\n")
    w(table(["#", "Measure", "USD", "USD/saleable box"], [
        ["1", "Supplier invoice value (excl. VAT)", usd(b["SUP"]), usd(b["SUP"] / S, 4)],
        ["2", "Customs value", usd(b["CV"]), usd(b["CV"] / S, 4)],
        ["3", "Duty (MFN Free + §301 12.5%)", usd(b["DUTY"]), usd(b["DUTY"] / S, 4)],
        ["4", "Port-arrival cost", usd(b["SUP"] + b["VAT_ECON"] + b["tooling"] + b["ORIGIN"] + b["OCEAN"] + b["INS"]), usd((b["SUP"] + b["ORIGIN"] + b["OCEAN"] + b["INS"]) / S, 4)],
        ["5", "Cleared-port cost", usd(b["COGS"] - b["DELIV"] - b["UNLOAD"]), usd((b["COGS"] - b["DELIV"] - b["UNLOAD"]) / S, 4)],
        ["6", "Customer-delivered cost (COGS)", usd(b["COGS"]), usd(b["avg_cpb"], 4)],
        ["7", "Fully burdened economic cost (+ selling, testing, admin, financing)", usd(b["COGS"] + b["SELL_VAR"] + b["SELL_FIX"] + b["FIN"]), usd((b["COGS"] + b["SELL_VAR"] + b["SELL_FIX"] + b["FIN"]) / S, 4)],
        ["8", "Total transaction cash (incl. recoverable VAT)", usd(b["CASH_TOTAL"]), usd(b["CASH_TOTAL"] / S, 4)],
    ], align="llrr"))
    w("")

    # ---------------------------------------------------------------- 13
    w("## 13. Pricing and profit analysis\n")
    w("Definitions: gross margin = (price − COGS)/price; markup = (price − COGS)/COGS; contribution deducts commission, payment processing, bad debt, samples/testing, sales admin and financing from gross profit.\n")
    prow = []
    for gm in I.GM_TARGETS:
        prow.append([pct(gm, 0)] + [usd(b["cpb"][c] / (1 - gm), 4) for c in CODES] + [usd(b["avg_cpb"] / (1 - gm), 4)])
    prow.append(["**Benchmark**"] + [f"**{usd(b['price'][c], 4)}**" for c in CODES] + [f"**{usd(b['avg_price'], 4)}**"])
    w(table(["Target GM", "3464", "3463", "3460", "Average"], prow))
    w(f"\nGross margin at the benchmark is **{pct(b['GM'])}**; markup is {pct(b['GP'] / b['COGS'])}; price headroom is {usd(b['avg_price'] - b['avg_cpb'], 4)}/box (negative).\n")
    w("**Shipment P&L (quoted order, BASE, first shipment):**\n")
    w(table(["Line", "USD"], [
        ["Revenue at benchmark price (59,100 saleable boxes)", usd(b["REV"])],
        ["− Delivered COGS", usd(-b["COGS"])],
        ["= Gross profit", usd(b["GP"])],
        ["− Commission 5%, processing 0.3%, bad debt 0.5%", usd(-b["SELL_VAR"])],
        ["− Samples, courier and lab testing (first shipment) + sales admin", usd(-b["SELL_FIX"])],
        ["− Financing (10% p.a. on cash outstanding until customer pays)", usd(-b["FIN"])],
        ["= **Contribution**", f"**{usd(b['CONTRIB'])}** ({pct(b['CM'])})"],
        ["Repeat shipment (no testing)", f"{usd(rep['CONTRIB'])} ({pct(rep['CM'])})"],
    ], align="lr"))
    w("\n**Container profitability – all configurations (BASE, NY/NJ → Edison):**\n")
    crows = []
    for ci, c in enumerate(I.CONFIGS):
        r = idx[(1, ci, 0)]
        crows.append([c["key"], c["name"], f"{r['U']:,.0f}", "Yes" if LM.config_feasibility(c, 1)["fits"] else "No", usd(r["avg_cpb"], 4), usd(r["avg_price"], 4), pct(r["GM"]),
                      usd(r["CONTRIB"], 0), pct(r["CM"]), usd(r["PEAK"], 0), pct(r["f_be"] - 1, 0, sign=True)])
    w(table(["#", "Configuration", "Units", "Fits", "Cost/box", "Price/box", "GM", "Contribution", "CM", "Peak WC", "Break-even price Δ"], crows, align="llrlrrrrrrr"))
    w("\n![Configurations](outputs/chart_configs_cost_vs_price.png)\n")
    w("**Cash and working capital (quoted order, BASE):**\n")
    w(table(["Timing", "Day", "USD"], [
        ["Before shipment (50% advance + VAT + testing)", 0, usd(b["out0"])],
        ["At export (balance + VAT + origin + prepaid freight + insurance)", b["t1"], usd(b["out1"])],
        ["Before US release (duty, MPF, HMF, broker, bonds, port)", b["t2"], usd(b["out2"])],
        ["At delivery (drayage, unloading)", b["t3"], usd(b["out3"])],
        ["**Total cash outflow**", "", f"**{usd(b['CASH_TOTAL'])}**"],
        ["VAT refund inflow (mode 2)", b["t_ref"], usd(b["vat_ref"])],
        ["Customer payment (45-day terms)", b["t4"], usd(b["REV"])],
        ["**Peak working capital**", "", f"**{usd(b['PEAK'])}**"],
    ], align="lrr"))
    w(f"\n**Break-even conditions (quoted order, BASE):**")
    w(f"- **Selling price:** must rise {pct(b['f_be'] - 1, 1)} for zero contribution.")
    w(f"- **NFC price:** must fall {pct(-b['chg_gm_0'], 1)} for zero gross margin and {pct(-b['chg_gm_t'], 1)} for 25%.")
    w(f"- **Ocean freight:** the maximum compatible with a 25% gross margin is {usd(b['max_ocean'], 0)} per container. **No freight level reaches 25%.**")
    w(f"- **Volume:** gross-margin break-even needs {num(b['u_be_0'])} boxes in one shipment, more than the {eqmix[('40HC', 1)] * 3:,}-box capacity of a 40' HC.")
    w("")
    w("![Tornado](outputs/chart_tornado_cm.png)\n")
    trows = []
    for i in range(0, 30, 2):
        l1, r1 = sens[i]
        l2, r2 = sens[i + 1]
        trows.append((abs(r1["CM"] - r2["CM"]), l1, r1, l2, r2))
    trows.sort(key=lambda x: -x[0])
    w(table(["Driver (low / high)", "CM low case", "CM high case", "Swing (pts)"], [[f"{t[1]} / {t[3]}", pct(t[2]["CM"]), pct(t[4]["CM"]), f"{t[0] * 100:.1f}"] for t in trows[:12]], align="lrrr"))
    w(f"\nOther single changes: repeat shipment CM {pct(rep['CM'])}; selling direct to end users at restaurant-supply prices CM {pct(direct['CM'])}; Section 301 at 0% CM {pct(s301_0['CM'])}. "
      "No single change makes the quoted order profitable.\n")
    w("**Path to viability (full 40' HC equal mix, BASE, each step cumulative):**\n")
    w(table(["Step", "Cost/box", "Price/box", "GM", "CM", "Contribution"], [[lab, usd(r["avg_cpb"], 4), usd(r["avg_price"], 4), pct(r["GM"]), pct(r["CM"]), usd(r["CONTRIB"], 0)] for lab, r in combos], align="lrrrrr"))
    w("\n![Path to viability](outputs/chart_path_to_viability.png)\n")
    w("Four independent favourable outcomes are needed at once, plus repeat volume, before the 12% contribution threshold is met.\n")

    # ---------------------------------------------------------------- 14
    w("## 14. Scenario comparison\n")
    srow = []
    for ci in (0, 3, 6):
        for s in range(3):
            r = idx[(s, ci, 0)]
            srow.append([I.CONFIGS[ci]["key"], SC[s], f"{r['U']:,.0f}", usd(r["avg_cpb"], 4), usd(r["avg_price"], 4), pct(r["GM"]), pct(r["CM"]), usd(r["CONTRIB"], 0), usd(r["PEAK"], 0)])
    w(table(["Config", "Scenario", "Units", "Cost/box", "Price/box", "GM", "CM", "Contribution", "Peak WC"], srow))
    w("\n**Scenario definitions:**")
    w("- **LOW (optimistic but defensible):** 0% Section 301; North-Europe-parity freight; a weaker EGP (54.6); NFC −5%; zero-rated VAT; tighter bundles; higher listing prices; 20% buyer margin.")
    w("- **STRESS:** EGP at 49.0 (Reuters poll); freight with the Egypt GRI and surcharges; NFC +10%; non-recoverable VAT; 1.8 mm pitch and 90% loading efficiency; exam, demurrage and delivery disruption; lower listings and a 30% buyer margin; 4% damage.\n")
    tv = []
    for name, (g, c) in {"Strict (GM≥25%, CM≥12%) – model default": (0.25, 0.12), "Moderate (GM≥15%, CM≥5%)": (0.15, 0.05), "Lenient (GM≥5%, CM≥0%)": (0.05, 0.0)}.items():
        cells = []
        for s in range(3):
            ok = [I.CONFIGS[ci]["key"] for ci in range(len(I.CONFIGS)) if idx[(s, ci, 0)]["GM"] >= g and idx[(s, ci, 0)]["CM"] >= c and LM.config_feasibility(I.CONFIGS[ci], s)["fits"]]
            cells.append(", ".join(ok) if ok else "none")
        tv.append([name] + cells)
    w("**Configurations that pass under alternative thresholds** (NY/NJ → Edison):\n")
    w(table(["Threshold set", "LOW", "BASE", "STRESS"], tv, align="llll"))
    w("\nThe multi-criteria ranking in the workbook (Scenario Comparison §E) ranks options against each other. A top rank does not mean an option is viable.\n")

    # ---------------------------------------------------------------- 15
    w("## 15. Main uncertainties (ranked by ability to reverse the decision)\n")
    for g in sorted(R.GAPS, key=lambda x: x["priority"])[:10]:
        w(f"{g['priority']}. **{g['fact']}**: {g['impact']} *Now:* {g['treatment']}")
    be_px = {c: b["price"][c] * b["f_be"] for c in CODES}
    lst = {c: I.MARKET["listing"][c]["v"][1] for c in CODES}
    w(f"\nCould any single uncertainty reverse the verdict? Only the selling price could, and only if written buyer prices are at least {pct(b['f_be'] - 1, 0)} above the benchmark for the quoted mix: "
      f"about {usd(be_px['3464'], 3)} (14\"), {usd(be_px['3463'], 3)} (16\") and {usd(be_px['3460'], 3)} (12\") per box. Container-lot buyers would then pay about "
      f"{pct(be_px['3464'] / lst['3464'], 0)} (14\") and {pct(be_px['3463'] / lst['3463'], 0)} (16\") of the single-bundle online price of heavier B-flute boxes, "
      f"and {pct(be_px['3460'] / lst['3460'], 0)} of the online price of an equivalent 12\" E-flute box. That is implausible for E-flute boxes from an unknown supplier.\n")

    # ---------------------------------------------------------------- 16
    w("## 16. Supplier negotiation strategy\n")
    w("Maximum NFC price per box (EGP, same basis as the quote) that still delivers the target gross margin at the BASE benchmark price:\n")
    w(table(["SKU", "Quoted", "Max for GM 0% – quoted mix", "Max for GM 25% – quoted mix", "Max for GM 0% – full 40' HC of that SKU", "Max for GM 25% – full 40' HC of that SKU"], [
        [c, f"{[k['price_egp'] for k in I.SKUS if k['code'] == c][0]:.3f}", f"{mx0_c1[c]:.2f}", f"{mx25_c1[c]:.2f}", f"{mx0_full[c]:.2f}", f"{mx25_full[c]:.2f}"] for c in CODES]))
    w("\nNegotiation plan:")
    w("1. **Re-quote on FCA [factory], USD-denominated, zero-rated for VAT**, with NFC as exporter. This removes 14% VAT cash and the EXW export problem.")
    w("2. **Price.** Use the table above as the walk-away line. Normal negotiation (5–10%) cannot close a gap of 30–70%. "
      "Request benchmark quotes from established Egyptian converters (e.g., Cepack Group [S087], New Golden Pack, WePack [S086]) on the same RFQ to test whether NFC's price is market level.")
    w("3. **Volume structure.** Single-size full 40' HC loads of the most competitive size (12\" boxes have the best economics) rather than 20,000 of each size.")
    w("4. **Specification and documents.** A spec sheet per SKU, die-lines, bundle data and a load plan, plus the food-contact declaration, PFAS and heavy-metal certificates, and \"Made in Egypt\" on every bundle.")
    w("5. **Payment.** 30% deposit / 70% against copy B/L, or an irrevocable LC. Independent bank-account verification. Third-party pre-shipment inspection with AQL sampling.")
    w("6. **Validity and price review.** At least 30 days; a kraft-paper price index clause; free replacement for defective lots.\n")

    # ---------------------------------------------------------------- 17
    w("## 17. Recommended pilot shipment\n")
    lcl = idx[(1, 9, 0)]
    c9 = idx[(1, 8, 0)]
    w(f"**A physical pilot shipment is not recommended.** It would lose money and would not test the decisive question (price):")
    w(f"- a 10,000-box LCL pilot: {usd(lcl['avg_cpb'], 3)}/box, contribution {usd(lcl['CONTRIB'], 0)};")
    w(f"- a full 20' equal mix: {usd(c9['avg_cpb'], 3)}/box, contribution {usd(c9['CONTRIB'], 0)}.\n")
    tst = I.SELLING["testing"]["v"]
    w(f"Recommended instead, a **paper pilot over 4–6 weeks**, costing about the model's sample, courier and lab-testing budget: **{usd(tst[1], 0)}** "
      f"(ESTIMATED range {usd(tst[0], 0)}–{usd(tst[2], 0)}; PFAS screens cost a few hundred dollars per sample [S092]). The RFQs themselves cost nothing.")
    w("1. Courier samples of each SKU (and of 1–2 alternative suppliers) to 3–5 target US buyers (RFQ 4). Run the minimum lab screen (PFAS total fluorine, heavy metals) and a real-pizza trial.")
    w("2. Send RFQ 1 (NFC FCA re-quote and documents), RFQ 2 (at least 3 Egyptian forwarders, door to Edison NJ / Jessup MD) and RFQ 3 (2 US brokers).")
    w("3. Verify NFC's identity and bank account.")
    w("4. Re-run the workbook with the quotes (replace ESTIMATED/ASSUMED inputs).")
    w("5. Proceed only if every condition in §19 holds. The first shipment should then be **one full 40' HC** (single size or equal mix), with buyer POs covering at least 70% before the balance is paid.\n")

    # ---------------------------------------------------------------- 18
    w("## 18. Go/no-go decision\n")
    n_block = sum(1 for g in R.GAPS if g["blocks"] == "SHIPMENT")
    w(table(["Threshold (provisional; no client targets supplied)", "Value", "Quoted order, BASE", "Result"], [
        ["Gross margin at benchmark price", f"≥ {pct(thr['gm_go'], 0)} (GO) / ≥ {pct(thr['gm_conditional'], 0)} (CONDITIONAL)", pct(b["GM"]),
         "PASS" if b["GM"] >= thr["gm_go"] else ("CONDITIONAL" if b["GM"] >= thr["gm_conditional"] else "FAIL")],
        ["Contribution margin after selling and financing", f"≥ {pct(thr['cm_min'], 0)}", pct(b["CM"]), "PASS" if b["CM"] >= thr["cm_min"] else "FAIL"],
        ["Delivered cost vs benchmark price", f"≤ {pct(thr['cost_ratio_max'], 0)} of benchmark", pct(b["avg_cpb"] / b["avg_price"], 0),
         "PASS" if b["avg_cpb"] / b["avg_price"] <= thr["cost_ratio_max"] else "FAIL"],
        ["Container utilisation (length)", f"≥ {pct(thr['util_min'], 0)}", pct(m_c1["len_util"], 0), "PASS" if m_c1["len_util"] >= thr["util_min"] else "FAIL"],
        ["Written buyer demand at or above break-even", f"≥ {pct(thr['demand_min'], 0)} of the shipment", "0%", "FAIL"],
        ["Unresolved shipment-blocking items (supplier identity, specs/compliance, Incoterm/VAT, IOR, marking)", "0", str(n_block), "PASS" if n_block <= thr["compliance_blockers"] else "FAIL"],
    ], align="llrl"))
    w("\n**Decision: NO-GO under the modeled conditions.** The opportunity fails on economics in every BASE configuration and destination, and under strict, moderate and lenient thresholds alike. "
      "It also fails on evidence: the supplier is unverified, the quote has expired, specifications are missing and no buyer demand exists. "
      "\"RENEGOTIATE\" was considered and rejected: the price cuts required (§16) are far outside any normal negotiation range, and the Section 301 duty is outside NFC's control. "
      f"\"INSUFFICIENT EVIDENCE\" was considered and rejected: the missing quotes would have to move inputs far beyond their plausible ranges in the same favourable direction to change the outcome "
      f"(on its own, selling prices {pct(b['f_be'] - 1, 0)} above the benchmark, or an NFC price {pct(-b['chg_gm_0'], 0)} lower just to reach zero gross margin). "
      "The verdict changes to **PILOT ONLY** or **CONDITIONAL GO** only if the re-entry conditions below are met in writing.\n")

    # ---------------------------------------------------------------- 19
    w("## 19. Conditions that must be satisfied before payment\n")
    w("**A. Economic re-entry conditions** (re-run the workbook with real quotes; all must hold):")
    w(f"- Written buyer prices covering at least 70% of a full container at or above the 25%-GM prices in §13. For reference: quoted mix ≈ {usd(b['avg_cpb'] / 0.75, 3)}/box; full 40' HC of 12\" ≈ {usd(c7['avg_cpb'] / 0.75, 3)}/box (BASE costs).")
    w("- An NFC FCA price at or below the §16 maxima for the shipped configuration.")
    w(f"- Itemised freight and door-delivery quotes no worse than the BASE assumptions (40' HC ≤ ${v(I.OCEAN['rate_hc']):,.0f} ocean; total origin ≤ {usd(b['ORIGIN'], 0)}).")
    w("- Contribution margin of at least 12% in BASE, and not negative in STRESS.\n")
    w("**B. Compliance and counterparty conditions:**")
    for t in ["NFC identity verified (commercial registry extract, tax card, industrial registry, factory video audit) and bank beneficiary confirmed by independent call-back.",
              "Signed re-quote naming the buying entity, FCA Incoterms 2020, named place, validity, VAT treatment, inclusions and payment milestones.",
              "Specification sheet, die-lines, inside/outside dimensions, bundle and load plan.",
              "Food-contact declaration (21 CFR 176.170 and related), PFAS-free declaration with a total-fluorine test, and a TPCH heavy-metal certificate. Approved samples with a real-pizza trial.",
              "Customs broker written opinion: HTS 4819.10.00(20), Section 301 9903.05.36 applicability or exemption, valuation, marking method, ISF/bond. IOR established (CBP Form 5106, bond, POA).",
              "Cargo insurance bound (ICC(A)), a moisture-protection plan, and a pre-shipment inspection booked.",
              "Payment security: LC or 30/70 against documents. No unsecured 50% advance to an unverified account."]:
        w(f"- [ ] {t}")
    w("")

    # ---------------------------------------------------------------- 20
    w("## 20. Sources and appendices\n")
    w(f"**Source register:** {nsrc} sources in `BigBoxPizza_Source_Register.csv`; the workbook's Source Register sheet has the same content. Evidence classes: "
      + ", ".join(f"{k} {n}" for k, n in sorted(ev_counts.items())) + ". "
      "The most decision-relevant sources:")
    for sid in ["S001", "S014", "S015", "S016", "S024", "S026", "S027", "S030", "S032", "S047", "S048", "S060", "S062", "S063", "S073", "S074", "S097", "S099"]:
        s = [x for x in SD.SOURCES if x["id"] == sid][0]
        w(f"- [{sid}] {s['title']} — {s['org']} — {s['url']} ({s['evidence']}; {s['confidence']})")
    w("\n**Appendix A – Capability and input audit:**")
    w("- **Project files at the start:** the client's README and an unrelated PDF, plus the uploaded quotation (image-only PDF; transcribed visually at 400 dpi).")
    w("- **Tools:** Python 3.13, openpyxl 3.1.5, pandas, pypdf/pdfplumber, LibreOffice 24.2 (headless recalculation through UNO) and matplotlib.")
    w(f"- **Research access:** web search worked. In this environment {url_block_note()}; the page-fetch tool could not resolve hosts. "
      "Details are in `working/01_capability_audit_and_project_plan.md`.")
    w("\n**Appendix B – File map:**")
    w("- `BigBoxPizza_US_Landed_Cost_Model.xlsx` – 25 required sheets + Calc Engine + Model Checks.")
    w("- `BigBoxPizza_Assumptions_and_Gaps.md`")
    w("- `BigBoxPizza_RFQ_Pack.md`")
    w("- `BigBoxPizza_Calculation_Audit.md`")
    w("- `BigBoxPizza_Source_Register.csv`")
    w("- `scripts/` – `build_all.py` rebuilds everything.")
    w("- `evidence/` – original quotation, page render and transcription.")
    w("- `outputs/` – charts, loading schematics, `validation_report.md` (workbook recalculation) and `qa_validation_checklist.md` (formal QA, brief §21).")
    w("- `working/` – capability audit, project plan, research log.")
    if val:
        mc_open = [a for a, b in val.get("model_checks", []) if not str(b).startswith("OK") and a != "OVERALL STATUS"]
        w(f"\n**Appendix C – Validation:** workbook status {val.get('status')}; {val.get('formula_cells_total', 0):,} formula cells; {val.get('error_count')} error values after LibreOffice recalculation; "
          f"{val.get('engine_rows_compared')} engine cases compared with the independent Python engine, with {val.get('engine_mismatch_count')} mismatches. "
          + ("Every Model Checks item is OK except the informational warning for the expired quotation. " if mc_open == ["Supplier quotation expired (information)"]
             else f"Model Checks items not OK: {', '.join(mc_open) or 'none'}. ")
          + "The formal QA checklist (research, engineering, financial and deliverable validation) is in `outputs/qa_validation_checklist.md`.")
    return "\n".join(L) + "\n"


def main(proj):
    p = os.path.join(proj, "BigBoxPizza_US_Market_and_Landed_Cost_Report.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(report())
    return p


if __name__ == "__main__":
    print(main(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
