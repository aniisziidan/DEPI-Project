"""Generate the Assumptions & Gaps register, RFQ pack, Calculation Audit, README and working notes."""
import json
import math
import os

import engine as E
import inputs as I
import loading_model as LM
import registers as R
import sources_data as SD
from write_reports import usd, pct, num, table, max_exw

CODES = [k["code"] for k in I.SKUS]
NOM = {"3464": '14"', "3463": '16"', "3460": '12"'}


def _val(proj):
    p = os.path.join(proj, "outputs", "validation_report.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


# ----------------------------------------------------------------------------- assumptions & gaps
def assumptions_and_gaps():
    L = []
    w = L.append
    w("# BigBoxPizza – Assumptions and Unresolved Questions\n")
    w("Valuation date 16-Oct-2026. Companion to the decision report and the workbook (sheets **Assumptions Register** and **Quote Requests & Missing Data**). "
      "Issues are ranked by impact on the decision and by urgency. **Blocks**: SHIPMENT = must be resolved before paying or shipping; PRICING = changes the go/no-go economics; PRECISION = improves accuracy only.\n")
    w("## 1. Ranked missing facts\n")
    for g in sorted(R.GAPS, key=lambda x: x["priority"]):
        w(f"### {g['priority']}. {g['id']} – {g['fact']}\n")
        w(table(["Field", "Detail"], [
            ["Why it matters", g["why"]], ["Potential financial / legal impact", g["impact"]], ["Current provisional treatment", g["treatment"]],
            ["Evidence required", g["evidence"]], ["Best placed to supply", g["who"]], ["Blocks", g["blocks"]]], align="ll"))
        w("")
    w("## 2. Quotation discrepancies (flagged, not corrected)\n")
    w(table(["#", "Discrepancy", "Action"], [
        ["D1", "Brief describes SKU 3464 as '5 × 5 × 5.5 inch'; document prints 'علبة بيتزا 5*35.5*35.5' (consistent with 355×355×50 mm)", "Confirm nominal size and unit"],
        ["D2", "Dimensions not identified as inside or outside", "Request internal/external dims and die-lines"],
        ["D3", "SKU 3460 description lacks 'علبة' (box)", "Confirm it is a complete box"],
        ["D4", "No Incoterm printed; shipping '—'", "Confirm FCA/EXW and named place"],
        ["D5", "Addressed to domestic buyer 'ا/ انيس شركة توريدات', Alexandria; tax ID blank; 14% VAT added", "Re-issue to the actual buying/exporting entity; confirm VAT treatment"],
        ["D6", "3464 (355 mm) EGP 8.365 > 3463 (405 mm) EGP 7.900", "Explain price relationship"],
        ["D7", "Bank name 'FAP MISR BANK' with SWIFT NBADEGCAXXX", "Verify beneficiary bank and account independently"],
        ["D8", "Signature 'Abdelrahman Darwish' vs printed name 'Mahmoud Bakr'", "Confirm authorised signatory"],
        ["D9", "Quote expired 30-Sep-2026", "Obtain dated re-quote"],
        ["D10", "Payment 'advance_50' undefined", "Define milestones; prefer LC or 30/70"],
    ], align="lll"))
    w("\n## 3. Assumptions register (all model inputs)\n")
    w("Values are LOW / BASE / STRESS. ⚠ marks decision-relevant inputs that are not verified. The same register is in the workbook with live links to the input cells.\n")
    w("Evidence classes used here and in the source register:\n")
    w(table(["Class", "Meaning"], [
        ["VERIFIED_OFFICIAL", "Stated in a government or legal source: statute, regulation, tariff schedule, official notice or central-bank rate."],
        ["VERIFIED_QUOTE", "Stated in a written commercial quotation (here only the expired NFC offer)."],
        ["VERIFIED_SUPPLIER", "Stated in a supplier's or service provider's own documentation (e.g. carrier equipment data)."],
        ["VERIFIED_MARKET", "Observed in current market data: price listings, rate indices, published carrier tariffs or announcements."],
        ["CALCULATED", "Derived by formula from verified inputs."],
        ["ESTIMATED", "Derived from proxies, guides or analogous data, with the reasoning stated."],
        ["ASSUMED", "Analyst judgement without direct evidence; to be replaced by quotes."],
        ["UNRESOLVED", "Unknown, unverified or contradictory; a decision-relevant gap."],
    ], align="ll"))
    w("")
    import build_views as BV
    rows = []
    for grp, key, d in I.all_inputs():
        imp = BV.IMPACT.get(key, "Low")
        flag = "⚠" if imp == "High" and d["evidence"] in ("ASSUMED", "ESTIMATED", "UNRESOLVED") else ""
        vals = " / ".join(f"{x:g}" for x in d["v"])
        rows.append([grp, d["name"], d["unit"], vals, d["evidence"], d["sources"] or "–", imp, flag, d.get("note", "")])
    for dd in I.DESTINATIONS:
        rows.append(["Destination", f"Drayage linehaul {dd['port_name']} → {dd['city']}", "USD/ctr", " / ".join(str(x) for x in dd["line"]), "ESTIMATED", "S052;S053;S054;S094", "High", "⚠", f"{dd['miles']} miles"])
    for pk, vals in I.PORT_DIFF.items():
        rows.append(["Ocean", f"Port differential {pk}", "USD/ctr", " / ".join(str(x) for x in vals), "ESTIMATED" if pk == "SAV" else "ASSUMED", "S053" if pk == "SAV" else "–", "Low", "", ""])
    w(table(["Group", "Input", "Unit", "LOW / BASE / STRESS", "Evidence", "Sources", "Impact", "Flag", "Notes"], rows, align="lllllllll"))
    w("\n## 4. Structural assumptions\n")
    for t in [
        "One formal US entry and one bill of lading per shipment; customs value based on the EXW/FCA product price (foreign inland freight not added for a proven ex-factory sale).",
        "Delivery directly from the port to one wholesale customer per container; floor-loaded bundles; live unload; no long-term storage (storage appears only in the sell-through analysis on the workbook's Container Profitability sheet, §2).",
        "Achievable price = online listing × (1 − E-flute discount for B-flute listings) × (1 − buyer resale margin). It is a ceiling estimate, not a buyer quote.",
        "Container-driven costs are allocated by bundle volume, per-shipment admin by units, and ad-valorem items by value.",
        "Recoverable VAT (mode 2) is cash only and carries a financing cost; VAT is an economic cost only in mode 3.",
        "FX: EGP-denominated items convert at the CBE buy rate less a bank spread; USD-denominated items are not converted.",
        "Damage/rejection reduces saleable units with no salvage value.",
    ]:
        w(f"- {t}")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- RFQ pack
def rfq_pack():
    f60 = LM.config_feasibility(I.CONFIGS[0], 1)
    kg60, vol60 = f60["kg"], f60["vol"]
    full = {k["code"]: LM.capacity(k, LM.container_by_key("40HC"), 1)["real_units"] for k in I.SKUS}
    kgfull = max(full[c] * E.unit_props(1)[c]["kg"] for c in full)
    lclf = LM.config_feasibility(I.CONFIGS[9], 1)
    r3 = [E.compute(s, 0, 0) for s in range(3)]
    eq_hc = LM.best_equal_mix(LM.container_by_key("40HC"), 1)
    full4 = {c: round(u, -3) for c, u in full.items()}
    fmix = LM.config_feasibility(I.CONFIGS[3], 1)  # the plan: full 40' HC, equal numbers of each size (C4)
    rmix = E.compute(1, 3, 0)
    L = []
    w = L.append
    w("# BigBoxPizza – Supplier and Logistics RFQ Pack\n")
    w("Four ready-to-send requests. Replace the bracketed fields before sending. Specifications marked **(UNCONFIRMED)** come from the expired NFC quotation and must not be presented to buyers as verified. "
      "Ask every respondent to complete the response table so the replies are comparable.\n")
    w("Sender block for all RFQs: **[Name] · BigBoxPizza · [Company address] · [Email] · [Phone/WhatsApp]** · Reference: BBP-RFQ-2026-10 · Date: [date] · Please respond by: [date + 10 working days].\n")
    # RFQ1
    w("---\n\n## RFQ 1 – Egyptian factory (NFC and alternative manufacturers)\n")
    w("**Subject:** Request for quotation – flat-packed corrugated pizza boxes for export to the USA (ref. NFC-OFFER-2026-0120)\n")
    w("Dear [Name],\n\nThank you for offer NFC-OFFER-2026-0120 of 23 September 2026. It expired on 30 September 2026, so we ask for a fresh, signed quotation for export to the United States, "
      "together with the technical and logistics data below. We are inviting comparable quotations from other manufacturers.\n")
    w("**1. Products** (please confirm or correct every value):\n")
    w(table(["Our code", "Your code", "Description on your offer", "Size on offer (mm)", "Nominal pizza size", "Board on offer"], [
        [f"BBP-{NOM[k['code']].strip(chr(34))}", k["code"], k["desc_ar"], f"{k['L']}×{k['W']}×{k['H']}", NOM[k["code"]], "SINGLE-E (UNCONFIRMED)"] for k in I.SKUS], align="llllll"))
    w(f"\n**2. Quantities to price separately:** (a) **our planned order:** a full 40' high-cube with equal quantities of the three sizes "
      f"(our estimate is about {eq_hc:,} of each, {3 * eq_hc:,} in total; please confirm how many fit); (b) 60,000 pcs, 20,000 of each size, as in your offer; "
      "(c) a full 40' high-cube of one size only (please state the quantity per size); (d) a 20' container trial; (e) your minimum order quantity per size.\n")
    w("**3. Prices requested** (per 1,000 pcs, in USD *and* EGP, excluding VAT):")
    w("- **FCA your factory, Incoterms 2020**: export-cleared and loaded into our forwarder's container, with your company as exporter of record;")
    w("- **EXW**, for comparison;")
    w("- **FOB Alexandria / Dekheila / Damietta**, if available.")
    w("Please state whether the invoice to a foreign buyer is VAT zero-rated as an export, and whether any tooling, die, plate, printing, sampling, packing or loading charges apply. Validity of at least 30 days; please state whether prices are fixed for that period or linked to kraft-paper prices.\n")
    w("**4. Technical data per size (mandatory):**")
    for t in ["Internal and external dimensions; lid and base heights; tolerances.",
              "Die-line / flat-pattern drawing (PDF/DXF) with flat blank dimensions.",
              "Board construction (your offer states only 'SINGLE-E'): flute profile, liner and medium grades and g/m², total g/m², caliper, recycled vs virgin fibre, food-contact surface, coatings, inks, adhesives.",
              "Strength data: ECT and/or flat crush; Cobb value; grease resistance (if claimed).",
              "Unit weight (g) and production tolerance."]:
        w(f"- {t}")
    w("\n**5. Packing and loading data (mandatory):**")
    for t in ["Blanks per bundle; bundle dimensions (L×W×H mm) and gross weight; strapping/wrap material; moisture protection.",
              "Palletisation option: pallet size, bundles per pallet, pallet height and weight, ISPM-15 heat-treated pallets.",
              "Container load plan with pcs per 20', 40' and 40' HC for each size, for a full 40' HC with equal quantities of the three sizes, and for the mixed 60,000 order; floor-loaded vs palletised; loading time at your factory.",
              "'Made in Egypt' marking on every bundle wrap / outer pack."]:
        w(f"- {t}")
    w("\n**6. Compliance documents (mandatory for a US food-contact product):**")
    for t in ["Declaration of compliance with US FDA 21 CFR 176.170 (paper/paperboard in contact with aqueous and fatty foods) and related sections for recycled fibre, inks and adhesives.",
              "Statement that no PFAS are intentionally added, supported by a recent total-fluorine test report.",
              "Heavy-metal (lead, cadmium, mercury, hexavalent chromium; sum ≤100 ppm) certificate of compliance or test report.",
              "Quality certifications (e.g., ISO 9001, ISO 22000/FSSC 22000, BRCGS Packaging) if held."]:
        w(f"- {t}")
    w("\n**7. Company and commercial information:**")
    for t in ["Commercial registry extract, tax card, industrial registry / licence, Exporters Register number.",
              "Bank letter confirming the beneficiary name and account. We will verify it by calling back on an independently obtained number.",
              "Payment terms. We propose 30% deposit and 70% against copy bill of lading, or an irrevocable letter of credit.",
              "Lead time from order and approved samples; weekly capacity; QC/AQL procedure; acceptance of third-party pre-shipment inspection.",
              "Samples: 10 pcs of each size by courier (please quote courier cost), plus photos of bundles and loading."]:
        w(f"- {t}")
    w("\n**8. Clarifications on your previous offer:**")
    for t in ["Your previous offer was addressed to a domestic buyer in Alexandria (tax ID blank) with 14% VAT added. Please address the new quotation to [buying entity legal name, country and address].",
              "Code 3464 is described as 5*35.5*35.5. Please confirm the nominal size and the unit, and whether 355×355×50 is the inside or outside dimension.",
              "Code 3460's description has no word for 'box'. Please confirm it is a complete pizza box.",
              "Please explain why 3464 (355 mm) is priced above 3463 (405 mm).",
              "Please explain 'advance_50' and confirm the authorised signatory (the signature reads 'Abdelrahman Darwish'; the printed name is 'Mahmoud Bakr')."]:
        w(f"- {t}")
    w("\n**Response table (one row per size and quantity option):**\n")
    w(table(["Size", "Qty option", "FCA USD/1,000", "EXW USD/1,000", "FOB USD/1,000", "VAT treatment", "Lead time", "Pcs/bundle", "Bundle mm & kg", "Pcs per 40' HC", "Validity"], [["", "", "", "", "", "", "", "", "", "", ""]]))
    w("\nKind regards,\n[Name]\n")
    # RFQ2
    w("---\n\n## RFQ 2 – Egyptian freight forwarders (minimum three)\n")
    w("**Subject:** RFQ – FCL/LCL Egypt (6th of October) to US East Coast, door delivery – flat-packed corrugated pizza boxes\n")
    w("Dear [Name],\n\nPlease quote itemised all-in costs for the shipments below. We need every charge listed separately, with currency, basis (per container, B/L or shipment), what is included and what is excluded.\n")
    w(table(["Item", "Detail"], [
        ["Commodity", "Flat-packed (unassembled) corrugated paperboard pizza boxes, HS 4819.10, non-hazardous, food-contact packaging (empty)"],
        ["Pick-up", "Nile Factory Carton, 199 6th Ext. Industrial Zone, 6th of October City, Giza (FCA factory – shipper loads); or the alternative supplier's factory"],
        ["Cargo (planned, provisional)", f"A full 40' HC: about {3 * eq_hc:,} pcs ({eq_hc:,} of each size) in about {3 * eq_hc // 50:,} bundles, ≈{fmix['kg'] / 1000:.1f} t gross and ≈{fmix['vol']:.0f} m³ of bundles; "
                                         "floor-loaded (please also price palletised)"],
        ["Scenarios", f"A) full 40' HC, equal mix of the three sizes (the plan); A2) the quoted 60,000 mix in 1×40' HC (≈{kg60 / 1000:.1f} t, ≈{vol60:.0f} m³); "
                      f"B) full 40' HC single size (about {min(full.values()):,}–{max(full.values()):,} pcs, up to ≈{kgfull / 1000:.1f} t); C) 1×40' GP; D) 1×20' GP; "
                      f"E) LCL about 10,000 pcs (≈{lclf['vol']:.1f} m³ of bundles, ≈{lclf['kg'] / 1000:.1f} t)"],
        ["Ports of loading", "Alexandria / Dekheila / Damietta – recommend the best service"],
        ["Destinations (port)", "New York/New Jersey, Baltimore, Norfolk, Savannah"],
        ["Destinations (door, live unload)", "Edison NJ 08837; Bronx NY 10474; Jessup MD 20794; Richmond VA 23230; Atlanta GA 30336"],
        ["Required date", "Cargo ready ~[date]; quote validity ≥30 days"],
    ], align="ll"))
    w("\n**Itemise (per scenario and destination):**")
    for t in ["Origin: empty container positioning, trucking 6th of October → port, loading supervision, export customs clearance, documentation/B/L fee, VGM/weighing, terminal handling (THC), seal, inspection charges, origin free time and detention tariff.",
              "Ocean: basic freight, BAF/bunker, GRI/peak season, rate-restoration or other surcharges, AMS/ISF filing, carrier, routing (direct or transshipment port), transit time, sailing frequency, rate validity.",
              "Insurance: ICC(A) premium rate, minimum premium, deductible, exclusions (wetting/condensation, insufficient packing).",
              "Destination: THC (included?), delivery order, PANYNJ CFC (if NY/NJ), terminal fees, customs brokerage (if offered), drayage to each door address, fuel surcharge, chassis (days and rate), tolls, waiting time (free hours and hourly rate), unloading (if offered), pre-pull/storage, demurrage and detention free time and tariffs."]:
        w(f"- {t}")
    w("\n**Response table:**\n")
    w(table(["Scenario", "POL → POD", "Origin total", "Ocean total", "Destination port charges", "Door delivery (address)", "Free time O/D", "Transit days", "Validity", "Exclusions"], [["", "", "", "", "", "", "", "", "", ""]]))
    w("\nKind regards,\n[Name]\n")
    # RFQ3
    w("---\n\n## RFQ 3 – US licensed customs brokers (minimum two)\n")
    w("**Subject:** Classification, duty and entry quotation – corrugated pizza boxes of Egyptian origin (first-time importer)\n")
    w("Dear [Name],\n\nWe are evaluating imports of empty, flat-packed corrugated pizza boxes made in Egypt, for sale to US foodservice distributors on the East Coast. "
      "We have **not yet established an importer of record**. Please provide your written opinion and fee schedule on the points below, and tell us what further evidence you need before you can confirm classification and duty treatment.\n")
    w(table(["Item", "Detail"], [
        ["Product", "Die-cut, scored, unassembled corrugated paperboard pizza boxes (single-wall, believed E-flute – to be confirmed), plain kraft, no printing (to be confirmed); for packing hot pizza (food contact)"],
        ["Sizes", "305×305×50, 355×355×50, 405×405×50 mm (inside/outside unconfirmed)"],
        ["Origin / manufacturer", "Egypt – Nile Factory Carton, 6th of October City (or an alternative Egyptian converter)"],
        ["Value", f"≈ USD {r3[0]['SUP'] / r3[0]['U']:.3f}–{r3[2]['SUP'] / r3[2]['U']:.3f} per box ex-factory (BASE {r3[1]['SUP'] / r3[1]['U']:.3f}); ≈ USD {rmix['SUP']:,.0f} per planned full-container shipment "
                  f"of {rmix['U']:,.0f} boxes (≈ USD {r3[1]['SUP']:,.0f} for the quoted 60,000)"],
        ["Terms", "FCA factory (preferred) or EXW; ocean to NY/NJ (also Baltimore, Norfolk, Savannah)"],
        ["Documents available", "Supplier quotation (expired); specifications pending (will be sent)"],
    ], align="ll"))
    w("\n**Questions:**")
    for i, t in enumerate([
        "Classification: HTS 4819.10.00 – statistical suffix .0020 (sanitary food containers) or .0040? Would you recommend a CBP binding ruling?",
        "Section 301 forced-labor action: does 9903.05.36 (Egypt, 12.5%) apply to 4819.10, or is the product exempt under the July-2026 notice's Annex II? How are refunds handled if the CIT invalidates the action?",
        "Any other measures (Section 232, AD/CVD)? Could the pending AD/CVD case on corrugated die-cut pizza boxes from China, Malaysia and Türkiye affect Egyptian-origin boxes (scope, circumvention, future petitions)?",
        "Valuation: an EXW/FCA price paid in EGP or USD; treatment of Egyptian VAT (zero-rated vs refunded vs not recovered); tooling paid to the supplier; documentation needed to prove an ex-factory sale.",
        "MPF and HMF basis, and any other entry fees.",
        "Country-of-origin marking: is 'Made in Egypt' on each bundle wrap / outer pack sufficient (19 CFR 134.24), or must each box be marked?",
        "FDA: confirm that no prior notice or facility registration is required for empty food-contact packaging, and whether the HTS line is FDA-flagged in ACE.",
        "State requirements relevant to buyers in NY, NJ, MD, VA and GA (PFAS, Toxics in Packaging certificates).",
        "Importer of record: can a foreign company act as IOR (CBP Form 5106 / CBP-assigned number)? What do you need (POA, KYC, bond)? Would you act as a non-resident importer's broker?",
        "Bond: single-transaction bond rate and minimum vs a continuous bond; ISF bond.",
        "Fee schedule: entry, ISF, bond, DO, delivery coordination, exam handling, disbursement and ACH terms.",
        "Exam risk for a first shipment from Egypt; typical VACIS/tailgate/CES costs at your port.",
    ], 1):
        w(f"{i}. {t}")
    w("\n**Response table:**\n")
    w(table(["Item", "Your answer / fee", "Evidence you need from us"], [["HTS & suffix", "", ""], ["Section 301 status", "", ""], ["Other duties", "", ""], ["Valuation notes", "", ""],
                                                                       ["Marking", "", ""], ["FDA / state", "", ""], ["IOR set-up", "", ""], ["Bond", "", ""], ["Fees (entry, ISF, DO…)", "", ""]], align="lll"))
    w("\nKind regards,\n[Name]\n")
    # RFQ4
    w("---\n\n## RFQ 4 – US wholesale buyers (demand test)\n")
    w("**Subject:** Request for information and indicative pricing – plain kraft corrugated pizza boxes, container quantities delivered to your dock\n")
    w("Dear [Name],\n\nWe are assessing a supply programme of plain kraft corrugated pizza boxes manufactured in Egypt and delivered by full container to our customers' warehouses on the US East Coast. "
      "Before committing, we would like to understand your requirements and current buying prices. **No commitment is requested at this stage.** Samples can be sent once received from the factory.\n")
    w(table(["Item", "What we can offer (provisional)", "Status"], [
        ["Sizes", "≈12\", ≈14\", ≈16\" square, ~2\" (50 mm) deep", "Inside/outside dimensions UNCONFIRMED"],
        ["Board", "Single-wall corrugated, believed E-flute, kraft", "UNCONFIRMED – spec sheet to follow"],
        ["Food contact", "Supplier declaration under 21 CFR 176.170, PFAS-free statement, heavy-metal certificate", "To be obtained before any sale"],
        ["Packing", "Flat, in bundles (≈50 pcs/bundle), floor-loaded in containers; pallets on request", "Bundle count UNCONFIRMED"],
        ["Quantities", f"Full 40' high-cube: ≈{eq_hc:,} per size in a 3-size mix (≈{3 * eq_hc:,} total) or ≈{min(full4.values()):,}–{max(full4.values()):,} of one size", "Provisional load estimates"],
        ["Delivery", "Container delivered to your dock (NY/NJ, MD, VA, GA areas), live unload", f"≈{r3[1]['t3'] / 7:.0f}–{r3[2]['t3'] / 7:.0f} weeks from order (BASE–STRESS), after sample approval"],
        ["Marking", "'Made in Egypt' on bundles", ""],
    ], align="lll"))
    w("\n**Questions:**")
    for i, t in enumerate([
        "Which pizza-box sizes do you buy? Please give inside dimensions, depth, flute (B/E), colour (kraft/white), print, and annual volume per size.",
        "Current purchase price per box by size (delivered to your warehouse), and the volume tier it applies to (case, pallet, truckload).",
        "At what delivered price per box would you consider a full-container purchase of E-flute boxes of acceptable quality?",
        "Required packing (bundle count, palletised or floor-loaded) and receiving capability (dock, floor-loaded unloading, appointment windows, unloading fees).",
        "Documentation you require (PFAS, FDA food-contact declaration, TPCH, insurance, vendor set-up).",
        "Payment terms you expect and your usual supplier qualification steps.",
        "Would you evaluate samples? Who should receive them and what tests do you run?",
        "Minimum and typical order quantities; preferred delivery locations.",
    ], 1):
        w(f"{i}. {t}")
    w("\n**Response table:**\n")
    w(table(["Size", "Spec you buy", "Annual volume", "Current delivered $/box & tier", "Price at which you'd buy E-flute in container lots", "Packing/receiving needs", "Docs required"], [["12\"", "", "", "", "", "", ""], ["14\"", "", "", "", "", "", ""], ["16\"", "", "", "", "", "", ""]]))
    w("\nThank you,\n[Name]\n")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- calculation audit
def calc_audit(val):
    rows, base, sens, combos = E.run_all()
    L = []
    w = L.append
    w("# BigBoxPizza – Calculation Audit Trail\n")
    w("This document explains how every number in the workbook and report is produced, so that it can be reproduced and checked independently. "
      "Notation: *s* = scenario (LOW/BASE/STRESS), *k* = SKU (3464, 3463, 3460), *n* = number of containers, FX = EGP per USD after bank spread.\n")
    w("## 1. Calculation sequence\n")
    for i, t in enumerate([
        "**Inputs** (input sheets; LOW/BASE/STRESS columns; evidence class and sources per row) → `inputs.py` is the build source.",
        "**Blank & bundle geometry** (Loading Geometry §A) → bundle a×b×h, bundle kg, m³ and kg per box.",
        "**Usable container envelope** (§B) → usable L, W, H; road-weight limit; efficiency.",
        "**Single-SKU capacity** (§C) → floor positions (row-mix pattern) × layers → theoretical → operational (× efficiency) → MIN(volume, weight).",
        "**Shipment configurations** (Shipment Configuration) → units per SKU per scenario; zone-layout feasibility per container.",
        "**Calc Engine**: one row per scenario × configuration × destination (150), plus 33 sensitivity and 6 combination rows → every cost, revenue, margin, cash and break-even figure.",
        "**Views** (Landed Cost ledger & SKU allocation, Pricing, Profitability, Sensitivity, Scenario Comparison, Cash Flow, Dashboard) read the engine by INDEX/MATCH.",
        "**Checks** (Model Checks) reconcile the ledger, allocation, quotation, customs value and double-count flags.",
    ], 1):
        w(f"{i}. {t}")
    w("\n## 2. Principal formulas\n")
    formulas = [
        ("Supplier value (USD)", "SUP_k = units_k × price_EGP_k × (1 + re-quote) × supplier factor / FX"),
        ("VAT cash / economic", "VAT_cash = 14% × SUP if mode ∈ {2,3}; VAT_econ = VAT_cash if mode = 3 else 0"),
        ("Origin per container", "n × [truck/FX + terminal + OTHC × (1 − OTHC-in-freight) + seal + inspection + detention days × rate + loading/FX]"),
        ("Origin per shipment", "(clearance + CoO)/FX + B/L + forwarder + QC + wires × fee"),
        ("Ocean", "n × (rate_container,s + port differential) × ocean factor + AMS   (LCL: max(m³ × factor, t, 1) × all-in rate/W-M)"),
        ("Customs value", "CV_k = SUP_k × (1 + 14% if mode 3) + tooling × units_k/U"),
        ("Insurance", "MAX(min, rate × 1.10 × (SUP + tooling + origin + ocean)) × (1 − included-elsewhere flag)"),
        ("Duty", "CV × (MFN 0% + Section 301 rate)"),
        ("MPF", "MIN(MAX(CV × 0.3464%, $34.58), $670.86)"),
        ("HMF", "CV × 0.125%"),
        ("Bond (STB)", "MAX(min, rate/1000 × (CV + duty + MPF + HMF))"),
        ("Delivery", "n × [line × dray factor × (1 + FSC) + tolls + chassis days × rate × (1 − chassis-included) + waiting + split + pre-pull + dry run]"),
        ("Unloading", "n × unload rate × (1 − unloading-included)"),
        ("COGS (delivered economic)", "SUP + VAT_econ + tooling + origin + ocean + insurance + duty + MPF + HMF + US per-shipment + US per-container + delivery + unloading"),
        ("Saleable units", "units_k × (1 − damage rate)"),
        ("Price", "listing_k × (1 − E-flute discount if listing is B-flute) × (1 − buyer margin) × price factor"),
        ("Gross margin / markup", "GM = (REV − COGS)/REV;  markup = (REV − COGS)/COGS"),
        ("Contribution", "GP − REV × (commission + processing + bad debt) − testing × first-shipment flag − admin − financing"),
        ("Financing", "rate/365 × Σ outflow_i × (day customer pays − day_i), VAT (mode 2) financed until refund day"),
        ("Peak working capital", "MAX of cumulative outflows at days 0, export, entry, delivery, less VAT refund if received by then"),
        ("Break-even price factor", "(COGS + fixed selling + financing) / (REV × (1 − variable selling %))"),
        ("Supplier change for GM target", "g = (REV(1 − GM) − (COGS − A))/A, A = (SUP + VAT_econ)(1 + duty + HMF + marginal MPF) + marginal insurance; change = (1 + re-quote) × g − 1"),
        ("Max EXW price for GM target", "p_k = [price_k(1 − GM)(1 − dmg) − o_k] / (1 + a_k) × FX / (1 + re-quote); a_k, o_k from the SKU cost split"),
        ("Break-even units", "U = fixed / (price per unit × (1 − GM) − variable per unit)"),
    ]
    w(table(["Quantity", "Formula"], formulas, align="ll"))
    w("\n## 3. Cost allocation to SKUs\n")
    w(table(["Cost", "Driver", "Rationale"], [
        ["Supplier price, VAT", "Direct", "Invoiced per SKU"],
        ["Duty", "Direct via customs value", "Ad valorem on each line"],
        ["MPF + HMF", "Customs value share", "Ad valorem at entry level"],
        ["Insurance", "Supplier value share", "Insured value driven by product value"],
        ["Tooling", "Units", "One-off, no better driver"],
        ["Origin per container, ocean, US per container (CFC, exam, demurrage), drayage, unloading", "Bundle volume (cube)", "Container space and time are the cost cause"],
        ["Origin per shipment, broker, ISF, bonds, DO", "Units", "Administrative, shipment-level"],
        ["Selling costs (profitability view)", "Revenue share", "Commission and credit costs scale with revenue"],
    ], align="lll"))
    w("\nThe check `Σ_k cost_k − COGS = 0` is evaluated on every engine row (Model Checks #7).\n")
    w("## 4. Customs value and duty logic\n")
    for t in ["Basis: transaction value = price actually paid or payable (19 U.S.C. 1401a; 19 CFR 152.103). Additions: buyer-paid packing, assists (tooling), commissions, royalties (none assumed except tooling).",
              "Exclusions: international freight and insurance; Egyptian inland freight for a proven ex-factory sale (19 CFR 152.103(a)(5)(i)).",
              "VAT: zero-rated or refunded VAT is not part of the price paid; non-recoverable VAT (mode 3) is added to customs value (conservative).",
              "Duty layers: HTS 4819.10.00 MFN Free + Section 301 (Egypt) 9903.05.36 12.5% (BASE/STRESS) or 0% (LOW, i.e. exemption or invalidation). No AD/CVD or Section 232 applies to Egypt-origin 4819.10 on the research date.",
              f"BASE quoted order: CV {usd(base['CV'])}; duty {usd(base['DUTY'])}; MPF {usd(base['MPF'])} (minimum binds); HMF {usd(base['HMF'])}."]:
        w(f"- {t}")
    w("\n## 5. Container-loading logic\n")
    for t in ["Blank: length = 2L + k·H (k = 4.5), width = W + 2H + 13 mm, calibrated on a US 14×14×1.75 in box listed with a 36×18 in pack [S080]. Net board = 92% of the bounding rectangle; weight = net area × g/m².",
              "Bundle: a = blank length + 5 mm, b = blank width + 5 mm, h = blanks per bundle (50) × pitch (1.5/1.6/1.8 mm).",
              "Usable envelope: L − 100 mm, W − 20 mm, MIN(H − 90 mm, door height).",
              "Floor pattern (Excel formulas): for n2 = 0..2 rows with the long side across the container, n1 = INT((W − n2·a)/b); positions = n1·INT(L/a) + n2·INT(L/b); best of three. "
              "Validated by an exhaustive two-dimensional guillotine dynamic program over raster points (`loading_model.dp_positions`); it equals the formula optimum in all 27 SKU × container × scenario cases.",
              "Layers = INT(usable height / bundle height); theoretical = positions × layers × 50; operational = INT(theoretical bundles × efficiency) × 50; weight-limited = INT(road limit / bundle kg) × 50; realistic = MIN.",
              "Mixed loads: each SKU occupies a block of container length. Stacks_k = ROUNDUP(bundles_k / (efficiency × layers)); minimum block length found from candidate lengths (multiples of a and b around the continuous estimate; the Excel method equals the exact search in every case); fits if Σ block lengths ≤ usable length and Σ kg ≤ road limit.",
              "Equal-mix maxima are solved by bisection in `loading_model.best_equal_mix` and written as orange values; the workbook re-tests them with formulas (Model Checks #20)."]:
        w(f"- {t}")
    w("\n## 6. Scenario assumptions (summary)\n")
    key_inputs = [("FX (EGP/USD, CBE)", I.FX["cbe"]), ("Re-quote change", I.SUPPLIER["requote"]), ("VAT mode", I.SUPPLIER["vat_mode"]), ("Section 301 rate", I.CUSTOMS["s301"]),
                  ("Ocean 40' HC (USD)", I.OCEAN["rate_hc"]), ("Stacking pitch (mm)", I.BLANK["pitch"]), ("Loading efficiency", I.USABLE["efficiency"]),
                  ("Buyer resale margin", I.MARKET["dist_margin"]), ("E-flute discount", I.MARKET["eflute_disc"]), ("Damage rate", I.SELLING["damage"]),
                  ("Exam (USD/ctr)", I.CUSTOMS["exam"]), ("Demurrage days", I.CUSTOMS["dem_days"])]
    fmt = lambda d, x: f"{x:.1%}".replace(".0%", "%").replace("-", "−") if d["unit"] in ("%", "ratio") else f"{x:,g}"  # noqa: E731
    w(table(["Input", "LOW", "BASE", "STRESS", "Evidence"], [[n, *[fmt(d, x) for x in d["v"]], d["evidence"]] for n, d in key_inputs]))
    w("\n## 7. Validation performed\n")
    if val:
        w(f"- Workbook rebuilt by `scripts/build_model.py`, recalculated in {val.get('libreoffice', 'LibreOffice')} (headless, UNO `calculateAll`) and re-opened with openpyxl: status **{val.get('status')}**.")
        w(f"- Worksheets: {len(val.get('sheets', []))}; missing required sheets: {val.get('missing_required_sheets') or 'none'}; formula cells: {val.get('formula_cells_total', 0):,}.")
        w(f"- Error values after recalculation: {val.get('error_count')}.")
        w(f"- Independent cross-check: {val.get('engine_rows_compared')} Calc Engine rows compared with `scripts/engine.py` on {val.get('engine_values_per_row')} values each (cost, revenue, margin, cash and break-even outputs, per-SKU cost, price and maximum EXW, and the container-fit flag; tolerance 1e-6, relative above 1): {val.get('engine_mismatch_count')} mismatches. Geometry capacities: {len(val.get('geometry_mismatches', []))} mismatches.")
        w("- Formal QA checklist (brief §21: research, engineering, financial and deliverable validation) with the evidence for each item: `outputs/qa_validation_checklist.md`.")
        w("\nModel Checks sheet after recalculation:\n")
        w(table(["Check", "Status"], [[a, b] for a, b in val.get("model_checks", [])], align="ll"))
    w("\n## 8. Limitations\n")
    for t in ["No written quotations (supplier re-quote, freight, broker, trucking, insurance, buyers). All logistics and market inputs are ESTIMATED or ASSUMED from documented proxies.",
              "Official websites could not be opened directly from the research environment; facts were taken from search-engine extracts of those pages. Re-verify before use.",
              "Blank geometry, grammage and bundle data are estimates; NFC data will change container capacity.",
              "Achievable prices are derived from advertised small-quantity prices, not negotiated container-lot prices.",
              "Financing uses simple interest on a 5-event timeline; no tax on profits; no US sales tax (B2B resale).",
              "The workbook recalculates in Excel/LibreOffice; the equal-mix maxima (orange) need `build_all.py` to be re-run if geometry inputs change. The checks flag this."]:
        w(f"- {t}")
    w("\n## 9. Reproduction\n")
    w("```bash\npython3 BigBoxPizza/scripts/build_all.py   # charts, workbook, LibreOffice recalculation + validation, CSV, Markdown, QA checklist\n"
      "python3 BigBoxPizza/scripts/engine.py      # prints the reference engine results\n"
      "python3 BigBoxPizza/scripts/check_urls.py  # optional, needs network: source URL reachability → outputs/url_check.json\n```\n")
    return "\n".join(L) + "\n"


# ----------------------------------------------------------------------------- README & working notes
def readme(val):
    return f"""# BigBoxPizza – Egypt → US pizza-box import: due-diligence package

**Verdict: NO-GO under modeled conditions** (see the report §1 and §18).

| Deliverable | File |
|---|---|
| 1. Executive decision report | `BigBoxPizza_US_Market_and_Landed_Cost_Report.md` |
| 2. Excel financial model (formula-driven, recalculated) | `BigBoxPizza_US_Landed_Cost_Model.xlsx` |
| 3. Source register (UTF-8 CSV) | `BigBoxPizza_Source_Register.csv` |
| 4. Assumptions and unresolved questions | `BigBoxPizza_Assumptions_and_Gaps.md` |
| 5. Supplier and logistics RFQ pack | `BigBoxPizza_RFQ_Pack.md` |
| 6. Calculation audit trail | `BigBoxPizza_Calculation_Audit.md` |
| 7. Scripts (reproducible build) | `scripts/` – run `python3 BigBoxPizza/scripts/build_all.py` |
| Evidence | `evidence/` – original NFC quotation PDF (SHA-256 ecfdf33b…f91b0), page render, verbatim transcription |
| Outputs | `outputs/` – charts, loading schematics, `validation_report.md` (workbook recalculation), `qa_validation_checklist.md` (formal QA, brief §21), `url_check.json` (source URL check) |
| US price check data | `data/us_pizza_box_prices_2026-10-16.csv` – 65 US pizza-box case prices from 28 sellers (16 Oct 2026), source S102 |
| Working notes | `working/` – capability audit, project plan, research log, US pizza-box price check (`03_us_pizza_box_price_check.md`), full-container plan (`04_full_container_plan.md`) |

Workbook validation: {val.get('status', 'n/a')} – {val.get('formula_cells_total', 0):,} formula cells, {val.get('error_count', 'n/a')} errors, {val.get('engine_rows_compared', 'n/a')} engine cases equal to the independent Python engine.

Requirements to rebuild: Python 3.11+, openpyxl, matplotlib, LibreOffice (headless, with python3-uno).
"""


def capability(val):
    return f"""# Capability & input audit, project plan

## Research start
- Started: **{I.RESEARCH_START_UTC}** (UTC). Valuation date used in the model: {I.VALUATION_DATE}.

## Project files found at start
- `README.md` (client repository readme), `ezstart_network write up.pdf` (unrelated to this project).
- Uploaded quotation: one-page image PDF (no text layer; "Microsoft: Print To PDF", author "Mahmoud Bakr", created 2026-09-23 16:04 +03:00). Preserved as `evidence/NFC-OFFER-2026-0120_original.pdf` (SHA-256 identical to the upload) and transcribed visually from a 400-dpi render.
- No existing spreadsheets or calculations.

## Tools available
- Python 3.13, openpyxl 3.1.5, pandas, pypdf, pdfplumber, Pillow; matplotlib installed from PyPI.
- LibreOffice 24.2 with Python-UNO, used for headless recalculation of the workbook.
- poppler (pdftoppm, pdftotext).

## Research capabilities tested
| Method | Result |
|---|---|
| Web search tool | Worked; returns page titles, URLs and extracts. Used for all research |
| Page-fetch tool | Failed for every host tried (DNS resolution error, including Wikipedia) |
| Direct HTTP (curl) to hts.usitc.gov, ecfr.gov, federalregister.gov, api.census.gov, cbp.gov, rulings.cbp.gov, cbe.org.eg, nilecarton.com | Blocked by the environment's network policy (403 at the egress proxy) |
| Package registry (PyPI) | Worked |
| One-shot reachability check of every source URL (`scripts/check_urls.py`, 16-Oct-2026) | All 70 source hosts denied by the egress policy (proxy CONNECT 403); no source page could be opened |

Consequence: official documents were read through search-engine extracts, never by opening the page. Every source records this access method, and confidence levels are capped accordingly. Census trade statistics (USA Trade Online / API) could not be queried; import-unit values were taken from the AD/CVD petition data instead.

## Project plan (executed)
| Step | Workstreams | Status |
|---|---|---|
| 1 | Audit, quotation extraction, structure | Done |
| 2 | Supplier & quotation (A), product engineering (B) | Done – supplier identity UNVERIFIED |
| 3 | Classification & tariffs (F), compliance (G) | Done – broker confirmation pending |
| 4 | Containers (C), origin (D), freight (E), destination (H) | Done – estimates, no quotes |
| 5 | Market & competitors (I), suppliers (M) | Done – listings, no buyer quotes |
| 6 | Landed cost (J), pricing (K), IOR structures (L) | Done (workbook) |
| 7 | RFQ pack (N), workbook (O), deliverables | Done |
| 8 | QA validation | Done – workbook validation {val.get('status', 'n/a')}; formal checklist in `outputs/qa_validation_checklist.md` |

## Missing-information register
See `BigBoxPizza_Assumptions_and_Gaps.md` and the workbook sheet "Quote Requests & Missing Data" (19 items, ranked).

## Network note for the client
The environment's network policy denied direct access to the official hosts above. To allow direct retrieval in a future session, add those domains under the cloud environment's network settings (Allowed domains).
"""


def research_log():
    L = ["# Research log (source-level summary)\n",
         "Each line: source ID – what was found. Full fields in `BigBoxPizza_Source_Register.csv`. All web sources were accessed through search-engine extracts (direct fetch blocked).\n"]
    for s in sorted(SD.SOURCES, key=lambda x: x["id"]):
        L.append(f"- **{s['id']}** {s['title']} ({s['org']}; {s['pub_date']}) – {s['extract']}")
    L.append("\n## Searches that returned no usable evidence (recorded so they are not repeated blindly)\n")
    for t in ["'Nile Factory Carton' / 'nilecarton' / phone +2 01224494481 / tax ID 552-782-209 / Arabic name – no independent public record.",
              "Egypt export clearance agent and chamber certificate-of-origin fee schedules (English and Arabic) – none published.",
              "Census/USITC partner-level US imports of HS 481910 – not reachable; petition data used instead.",
              "Mediterranean/Egypt → US East Coast spot index – no public index; CMA CGM FAK and Hapag-Lloyd GRI used.",
              "Lane-level drayage rates for NY/NJ, Baltimore, Norfolk, Savannah destinations – only distance-band guides found.",
              "Virginia, New Jersey, Pennsylvania, Georgia PFAS food-packaging statutes – not confirmed in this session."]:
        L.append(f"- {t}")
    return "\n".join(L) + "\n"


def main(proj):
    val = _val(proj)
    files = {
        "BigBoxPizza_Assumptions_and_Gaps.md": assumptions_and_gaps(),
        "BigBoxPizza_RFQ_Pack.md": rfq_pack(),
        "BigBoxPizza_Calculation_Audit.md": calc_audit(val),
        "README.md": readme(val),
        os.path.join("working", "01_capability_audit_and_project_plan.md"): capability(val),
        os.path.join("working", "02_research_log.md"): research_log(),
    }
    os.makedirs(os.path.join(proj, "working"), exist_ok=True)
    for name, content in files.items():
        with open(os.path.join(proj, name), "w", encoding="utf-8") as f:
            f.write(content)
    return list(files)


if __name__ == "__main__":
    print(main(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
