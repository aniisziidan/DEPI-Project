"""Reference cost / margin / cash engine (pure Python).

It mirrors, line for line, the formulas written into the Excel "Engine" sheet by
build_model.py.  validate_model.py recalculates the workbook in LibreOffice and
compares every engine row with this module, so the report and the workbook can
never silently diverge.

Conventions
- Scenario index s: 0 LOW, 1 BASE, 2 STRESS.  Config/destination use list order in inputs.py.
- Currency USD unless the name ends in _egp.
- Per-SKU dicts are keyed by SKU code in quote order.
"""
import json
import math

import inputs as I
import loading_model as LM

CT_INDEX = {"20GP": 1, "40GP": 2, "40HC": 3, "LCL": 4}
DEFAULT_DRIVERS = ("fx", "supfac", "vatmode", "s301", "oceanfac", "pricefac", "unitsfac", "drayfac",
                   "unloadfac", "dmg", "distm", "edisc", "credit", "truckfac", "comm", "testfac")


def val(inp, s):
    return inp["v"][s]


def base_drivers(s):
    return dict(
        fx=val(I.FX["cbe"], s) * (1 - val(I.FX["spread"], s)),
        supfac=1.0,
        vatmode=val(I.SUPPLIER["vat_mode"], s),
        s301=val(I.CUSTOMS["s301"], s),
        oceanfac=1.0,
        pricefac=1.0,
        unitsfac=1.0,
        drayfac=1.0,
        unloadfac=1.0,
        dmg=val(I.SELLING["damage"], s),
        distm=val(I.MARKET["dist_margin"], s),
        edisc=val(I.MARKET["eflute_disc"], s),
        credit=val(I.SELLING["credit_days"], s),
        truckfac=1.0,
        comm=val(I.SELLING["commission"], s),
        testfac=1.0,
    )


def unit_props(s):
    """Per-unit volume (m³) and weight (kg) of bundled blanks, by SKU, for scenario s."""
    out = {}
    for sku in I.SKUS:
        bd = LM.bundle(sku, s)
        out[sku["code"]] = dict(vol=bd["vol"] / bd["n"], kg=bd["weight"] / bd["n"])
    return out


_UNITS_CACHE = {}


def config_units(ci, s):
    key = (ci, s)
    if key not in _UNITS_CACHE:
        _UNITS_CACHE[key] = LM.config_units(I.CONFIGS[ci], s)
    return _UNITS_CACHE[key]


def compute(s, ci, di, drivers=None):
    """Compute one engine row. s scenario idx, ci config idx, di destination idx."""
    d = base_drivers(s)
    if drivers:
        d.update(drivers)
    cfg = I.CONFIGS[ci]
    dest = I.DESTINATIONS[di]
    ctype = cfg["ctype"]
    is_lcl = ctype == "LCL"
    n = cfg["n"]
    up = unit_props(s)
    skus = [k["code"] for k in I.SKUS]

    units = {k: config_units(ci, s)[k] * d["unitsfac"] for k in skus}
    U = sum(units.values())
    vol = {k: units[k] * up[k]["vol"] for k in skus}
    V = sum(vol.values())
    kg = sum(units[k] * up[k]["kg"] for k in skus)

    fx = d["fx"]
    req = val(I.SUPPLIER["requote"], s)
    price_egp = {k["code"]: k["price_egp"] * (1 + req) * d["supfac"] for k in I.SKUS}
    sup_egp = {k: units[k] * price_egp[k] for k in skus}
    sup = {k: sup_egp[k] / fx for k in skus}
    SUP = sum(sup.values())
    vrate = val(I.SUPPLIER["vat_rate"], s)
    vm = d["vatmode"]
    vat_cash = {k: (sup[k] * vrate if vm in (2, 3) else 0.0) for k in skus}
    VAT_CASH = sum(vat_cash.values())
    vat_econ = {k: (vat_cash[k] if vm == 3 else 0.0) for k in skus}
    VAT_ECON = sum(vat_econ.values())
    tooling = val(I.SUPPLIER["tooling_egp"], s) / fx

    # ---------------- origin
    if is_lcl:
        orig_ctr_each = 0.0
        orig_lcl = val(I.ORIGIN["lcl_truck"], s) * d["truckfac"] / fx + val(I.ORIGIN["lcl_cfs_o"], s)
    else:
        truck = val(I.ORIGIN["truck_20"] if ctype == "20GP" else I.ORIGIN["truck_40"], s) * d["truckfac"] / fx
        othc = val(I.ORIGIN["othc_20"] if ctype == "20GP" else I.ORIGIN["othc_40"], s) * (1 - val(I.ORIGIN["othc_in_freight"], s))
        ddr = val(I.ORIGIN["dd_20"] if ctype == "20GP" else I.ORIGIN["dd_40"], s)
        orig_ctr_each = (truck + val(I.ORIGIN["terminal"], s) + othc + val(I.ORIGIN["seal"], s)
                         + val(I.ORIGIN["inspection"], s) + val(I.ORIGIN["dd_days"], s) * ddr
                         + val(I.ORIGIN["loading_egp"], s) / fx)
        orig_lcl = 0.0
    orig_ctr = orig_ctr_each * n + orig_lcl
    orig_shp = ((val(I.ORIGIN["clearance"], s) + val(I.ORIGIN["coo"], s)) / fx + val(I.ORIGIN["bl_fee"], s)
                + val(I.ORIGIN["fwd_fee"], s) + val(I.ORIGIN["qc"], s) + val(I.ORIGIN["wires"], s) * val(I.ORIGIN["wire_fee"], s))
    ORIGIN = orig_ctr + orig_shp

    # ---------------- ocean
    pdiff = I.PORT_DIFF[dest["port"]][s]
    if is_lcl:
        wm = max(V * val(I.OCEAN["lcl_factor"], s), kg / 1000.0, 1.0)
        ocean_ctr = wm * val(I.OCEAN["lcl_rate"], s) * d["oceanfac"]
    else:
        rate = {"20GP": I.OCEAN["rate_20"], "40GP": I.OCEAN["rate_40"], "40HC": I.OCEAN["rate_hc"]}[ctype]
        ocean_ctr = n * (val(rate, s) + pdiff) * d["oceanfac"]
    OCEAN = ocean_ctr + val(I.OCEAN["ams"], s)

    # ---------------- customs value, insurance, duty, fees
    cv = {k: sup[k] + vat_econ[k] + tooling * (units[k] / U) for k in skus}
    CV = sum(cv.values())
    INS = max(val(I.OCEAN["ins_min"], s),
              val(I.OCEAN["ins_rate"], s) * (1 + val(I.OCEAN["ins_uplift"], s)) * (SUP + tooling + ORIGIN + OCEAN)) * (1 - val(I.OCEAN["ins_in_other"], s))
    duty_rate = val(I.CUSTOMS["mfn"], s) + d["s301"]
    duty = {k: cv[k] * duty_rate for k in skus}
    DUTY = sum(duty.values())
    MPF = min(max(CV * val(I.CUSTOMS["mpf_rate"], s), val(I.CUSTOMS["mpf_min"], s)), val(I.CUSTOMS["mpf_max"], s))
    HMF = CV * val(I.CUSTOMS["hmf"], s)
    STB = max(val(I.CUSTOMS["stb_min"], s), val(I.CUSTOMS["stb_rate"], s) / 1000.0 * (CV + DUTY + MPF + HMF))
    US_SHP = (val(I.CUSTOMS["broker"], s) + val(I.CUSTOMS["isf"], s) + val(I.CUSTOMS["do_fee"], s)
              + STB + val(I.CUSTOMS["isf_bond"], s))
    ct_teu = {"20GP": 1, "40GP": 2, "40HC": 2, "LCL": 0}[ctype]
    CFC = (val(I.CUSTOMS["cfc"], s) * ct_teu * n * (1 - val(I.CUSTOMS["cfc_in_freight"], s))) if dest["port"] == "NYNJ" else 0.0
    n_eff = 1 if is_lcl else n
    EXAM = n_eff * (val(I.CUSTOMS["exam"], s) + val(I.CUSTOMS["exam_dray"], s))
    DEM = n_eff * val(I.CUSTOMS["dem_days"], s) * val(I.CUSTOMS["dem_rate"], s)
    US_CTR = CFC + EXAM + DEM

    # ---------------- destination delivery
    if is_lcl:
        DELIV = (val(I.DRAY["lcl_cfs_d"], s) + val(I.DRAY["lcl_deliv"], s)) * d["drayfac"]
        UNLOAD = 0.0
    else:
        line = dest["line"][s] * d["drayfac"]
        dray_each = (line * (1 + val(I.DRAY["fsc"], s)) + dest["tolls"][s]
                     + val(I.DRAY["chassis_days"], s) * dest["chassis"][s] * (1 - val(I.DRAY["chassis_in_dray"], s))
                     + val(I.DRAY["wait_hours"], s) * val(I.DRAY["wait_rate"], s) + val(I.DRAY["split"], s)
                     + val(I.DRAY["prepull"], s) + val(I.DRAY["dryrun"], s))
        DELIV = n * dray_each
        UNLOAD = n * val(I.DRAY["unload_20"] if ctype == "20GP" else I.DRAY["unload_40"], s) * d["unloadfac"] * (1 - val(I.DRAY["unload_in_dray"], s))

    COGS = SUP + VAT_ECON + tooling + ORIGIN + OCEAN + INS + DUTY + MPF + HMF + US_SHP + US_CTR + DELIV + UNLOAD

    # ---------------- per-SKU allocation
    shared_space = orig_ctr + OCEAN + US_CTR + DELIV + UNLOAD          # cube-driven
    shared_admin = orig_shp + US_SHP                                     # per-shipment, unit-driven
    cost = {}
    for k in skus:
        cshare = vol[k] / V if V else 0
        ushare = units[k] / U if U else 0
        vshare = cv[k] / CV if CV else 0
        sshare = sup[k] / SUP if SUP else 0
        cost[k] = (sup[k] + vat_econ[k] + tooling * ushare + duty[k] + (MPF + HMF) * vshare + INS * sshare
                   + shared_space * cshare + shared_admin * ushare)
    sale_units = {k: units[k] * (1 - d["dmg"]) for k in skus}
    SALE = sum(sale_units.values())
    cpb = {k: (cost[k] / sale_units[k] if sale_units[k] else 0.0) for k in skus}

    # ---------------- revenue & margins
    price = {}
    for sk in I.SKUS:
        k = sk["code"]
        lst = val(I.MARKET["listing"][k], s)
        disc = d["edisc"] if sk["bench_flute"] == "B" else 0.0
        price[k] = lst * (1 - disc) * (1 - d["distm"]) * d["pricefac"]
    rev = {k: sale_units[k] * price[k] for k in skus}
    REV = sum(rev.values())
    GP = REV - COGS
    GM = GP / REV if REV else 0.0
    var_pct = d["comm"] + val(I.SELLING["processing"], s) + val(I.SELLING["bad_debt"], s)
    SELL_VAR = REV * var_pct
    SELL_FIX = val(I.SELLING["testing"], s) * d["testfac"] + val(I.SELLING["admin"], s)

    # ---------------- cash timeline
    lead = val(I.SUPPLIER["lead_days"], s)
    transit = val(I.OCEAN["transit"], s) + (val(I.OCEAN["lcl_extra_days"], s) if is_lcl else 0)
    t0, t1 = 0, lead
    t2 = t1 + transit
    t3 = t2 + 2 + val(I.CUSTOMS["dem_days"], s)
    t4 = t3 + d["credit"]
    adv = val(I.SUPPLIER["advance"], s)
    out0 = adv * (SUP + VAT_CASH) + tooling + val(I.SELLING["testing"], s) * d["testfac"]
    out1 = (1 - adv) * (SUP + VAT_CASH) + ORIGIN + OCEAN + INS
    out2 = DUTY + MPF + HMF + US_SHP + US_CTR
    out3 = DELIV + UNLOAD
    vat_ref = VAT_CASH if vm == 2 else 0.0
    t_ref = t1 + val(I.SUPPLIER["vat_lag"], s)
    fin_rate = val(I.SELLING["fin_rate"], s)
    vat_days = (adv * VAT_CASH * (t_ref - t0) + (1 - adv) * VAT_CASH * (t_ref - t1)) if vm == 2 else 0.0
    nonvat_days = ((out0 - adv * (VAT_CASH if vm == 2 else 0)) * (t4 - t0)
                   + (out1 - (1 - adv) * (VAT_CASH if vm == 2 else 0)) * (t4 - t1)
                   + out2 * (t4 - t2) + out3 * (t4 - t3))
    FIN = fin_rate / 365.0 * (nonvat_days + vat_days)
    cum0 = out0 - (vat_ref if t_ref <= t0 else 0)
    cum1 = out0 + out1 - (vat_ref if t_ref <= t1 else 0)
    cum2 = out0 + out1 + out2 - (vat_ref if t_ref <= t2 else 0)
    cum3 = out0 + out1 + out2 + out3 - (vat_ref if t_ref <= t3 else 0)
    PEAK = max(cum0, cum1, cum2, cum3)
    CASH_TOTAL = out0 + out1 + out2 + out3

    CONTRIB = GP - SELL_VAR - SELL_FIX - FIN
    CM = CONTRIB / REV if REV else 0.0
    f_be = (COGS + SELL_FIX + FIN) / (REV * (1 - var_pct)) if REV else 0.0

    # max EXW price (EGP, quote basis) per SKU for 25% GM at benchmark price (linearised)
    gm_t = I.THRESHOLDS["gm_go"]
    maxexw = {}
    for k in skus:
        sup_part = sup[k]
        a = ((vat_econ[k] + duty[k] + (MPF + HMF) * (cv[k] / CV if CV else 0) + INS * (sup[k] / SUP if SUP else 0)) / sup_part) if sup_part else 0
        o = (cost[k] - sup_part * (1 + a)) / units[k] if units[k] else 0
        p_usd = (price[k] * (1 - gm_t) * (1 - d["dmg"]) - o) / (1 + a)
        maxexw[k] = (p_usd * fx / ((1 + req) * d["supfac"])) if units[k] else None  # EGP, same basis as quoted price

    # supplier-price change needed (vs quoted price) for GM target and GM 0 — linearised as in Excel
    mpf_r = val(I.CUSTOMS["mpf_rate"], s)
    mpf_marg = mpf_r if (CV * mpf_r > val(I.CUSTOMS["mpf_min"], s) and CV * mpf_r < val(I.CUSTOMS["mpf_max"], s)) else 0.0
    ins_marg = (val(I.OCEAN["ins_rate"], s) * (1 + val(I.OCEAN["ins_uplift"], s)) * SUP) if INS > val(I.OCEAN["ins_min"], s) else 0.0
    A_lin = (SUP + VAT_ECON) * (1 + duty_rate + val(I.CUSTOMS["hmf"], s) + mpf_marg) + ins_marg
    g_t = (REV * (1 - gm_t) - (COGS - A_lin)) / A_lin if A_lin else 0.0
    g_0 = (REV - (COGS - A_lin)) / A_lin if A_lin else 0.0
    chg_gm_t = (1 + req) * d["supfac"] * g_t - 1
    chg_gm_0 = (1 + req) * d["supfac"] * g_0 - 1
    # maximum ocean freight per container for GM target (container configs only)
    max_ocean = ((REV * (1 - gm_t) - (COGS - ocean_ctr)) / n) if n > 0 else None
    # break-even units in the same configuration (fixed costs spread), GM target and GM 0
    var_u = (SUP + VAT_ECON + DUTY + MPF + HMF) / U if U else 0.0
    fixed = COGS - var_u * U
    p_u = REV / U if U else 0.0
    den_t = p_u * (1 - gm_t) - var_u
    den_0 = p_u - var_u
    u_be_t = fixed / den_t if den_t > 0 else None
    u_be_0 = fixed / den_0 if den_0 > 0 else None

    return dict(
        chg_gm_t=chg_gm_t, chg_gm_0=chg_gm_0, max_ocean=max_ocean, u_be_t=u_be_t, u_be_0=u_be_0, A_lin=A_lin,
        s=s, ci=ci, di=di, drivers=d, units=units, U=U, V=V, kg=kg, n=n, ctype=ctype,
        SUP=SUP, sup=sup, VAT_CASH=VAT_CASH, VAT_ECON=VAT_ECON, tooling=tooling,
        orig_ctr=orig_ctr, orig_shp=orig_shp, ORIGIN=ORIGIN, OCEAN=OCEAN, INS=INS, CV=CV,
        DUTY=DUTY, MPF=MPF, HMF=HMF, STB=STB, US_SHP=US_SHP, CFC=CFC, EXAM=EXAM, DEM=DEM, US_CTR=US_CTR,
        DELIV=DELIV, UNLOAD=UNLOAD, COGS=COGS, cost=cost, sale_units=sale_units, SALE=SALE, cpb=cpb,
        price=price, rev=rev, REV=REV, GP=GP, GM=GM, SELL_VAR=SELL_VAR, SELL_FIX=SELL_FIX, FIN=FIN,
        CONTRIB=CONTRIB, CM=CM, f_be=f_be, maxexw=maxexw,
        out0=out0, out1=out1, out2=out2, out3=out3, CASH_TOTAL=CASH_TOTAL, PEAK=PEAK, vat_ref=vat_ref,
        t1=t1, t2=t2, t3=t3, t4=t4, t_ref=t_ref,
        avg_cpb=COGS / SALE if SALE else 0.0, avg_price=REV / SALE if SALE else 0.0,
    )


# ----------------------------------------------------------------------------- sensitivity definitions
def sensitivity_cases(s):
    """(label, driver overrides) pairs; values are absolute replacements of the drivers."""
    lo, hi = 0, 2
    fx_eff = lambda si: val(I.FX["cbe"], si) * (1 - val(I.FX["spread"], s))
    return [
        ("FX: EGP weaker (54.60)", dict(fx=val(I.FX["cbe"], lo) * (1 - val(I.FX["spread"], s)))),
        ("FX: EGP stronger (49.00)", dict(fx=val(I.FX["cbe"], hi) * (1 - val(I.FX["spread"], s)))),
        ("Ocean freight −28% (LOW level)", dict(oceanfac=val(I.OCEAN["rate_hc"], lo) / val(I.OCEAN["rate_hc"], 1))),
        ("Ocean freight +25% (STRESS level)", dict(oceanfac=val(I.OCEAN["rate_hc"], hi) / val(I.OCEAN["rate_hc"], 1))),
        ("Section 301 duty 0% (exempt / struck down)", dict(s301=0.0)),
        ("Additional duty 25% (hypothetical escalation)", dict(s301=0.25)),
        ("Supplier price −10%", dict(supfac=0.90)),
        ("Supplier price +10%", dict(supfac=1.10)),
        ("Selling price −15%", dict(pricefac=0.85)),
        ("Selling price +15%", dict(pricefac=1.15)),
        ("Shipment quantity −20% (same container)", dict(unitsfac=0.80)),
        ("Shipment quantity +20% (if it fits)", dict(unitsfac=1.20)),
        ("Drayage linehaul ×0.75", dict(drayfac=0.75)),
        ("Drayage linehaul ×1.5", dict(drayfac=1.5)),
        ("Unloading free (customer unloads)", dict(unloadfac=0.0)),
        ("Unloading ×2", dict(unloadfac=2.0)),
        ("VAT zero-rated (direct export)", dict(vatmode=1)),
        ("VAT paid & not recoverable", dict(vatmode=3)),
        ("Damage/rejection 0.5%", dict(dmg=0.005)),
        ("Damage/rejection 4%", dict(dmg=0.04)),
        ("Buyer resale margin 20%", dict(distm=0.20)),
        ("Buyer resale margin 30%", dict(distm=0.30)),
        ("E-flute discount 15%", dict(edisc=0.15)),
        ("E-flute discount 25%", dict(edisc=0.25)),
        ("Credit terms 30 days", dict(credit=30)),
        ("Credit terms 90 days", dict(credit=90)),
        ("Egypt trucking −20%", dict(truckfac=0.8)),
        ("Egypt trucking +30%", dict(truckfac=1.3)),
        ("Commission 3%", dict(comm=0.03)),
        ("Commission 7%", dict(comm=0.07)),
        ("Repeat shipment (no sample/lab testing)", dict(testfac=0.0)),
        ("Sell direct to end users (no buyer resale margin)", dict(distm=0.0)),
        ("Selling price +25% (≈ import-parity $/lb cross-check)", dict(pricefac=1.25)),
    ]


def combo_cases():
    """Cumulative 'path to viability' cases (BASE scenario, destination D1). (label, cfg index, overrides)."""
    return [
        ("K1 Full 40' HC equal mix (C4), BASE", 3, {}),
        ("K2 K1 + Section 301 duty removed (0%)", 3, dict(s301=0.0)),
        ("K3 K2 + supplier price −15%", 3, dict(s301=0.0, supfac=0.85)),
        ("K4 K3 + selling price +15%", 3, dict(s301=0.0, supfac=0.85, pricefac=1.15)),
        ("K5 K4 + ocean freight at LOW level", 3, dict(s301=0.0, supfac=0.85, pricefac=1.15,
                                                       oceanfac=I.OCEAN["rate_hc"]["v"][0] / I.OCEAN["rate_hc"]["v"][1])),
        ("K6 K5 + repeat shipment (no testing)", 3, dict(s301=0.0, supfac=0.85, pricefac=1.15,
                                                         oceanfac=I.OCEAN["rate_hc"]["v"][0] / I.OCEAN["rate_hc"]["v"][1], testfac=0.0)),
    ]


SEL_DEFAULT = dict(s=1, ci=0, di=0)  # BASE, C1 quoted 60k in 40HC, D1 NY/NJ→Edison


def run_all():
    rows = []
    for s in range(3):
        for ci in range(len(I.CONFIGS)):
            for di in range(len(I.DESTINATIONS)):
                rows.append(compute(s, ci, di))
    sens = []
    sd = SEL_DEFAULT
    base = compute(sd["s"], sd["ci"], sd["di"])
    for label, ov in sensitivity_cases(sd["s"]):
        sens.append((label, compute(sd["s"], sd["ci"], sd["di"], ov)))
    combos = [(label, compute(1, ci, sd["di"], ov)) for label, ci, ov in combo_cases()]
    return rows, base, sens, combos


def _clean(o):
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, float):
        return round(o, 6)
    return o


if __name__ == "__main__":
    rows, base, sens, combos = run_all()
    print("BASE C1 D1:")
    for k in ("U", "SUP", "VAT_CASH", "ORIGIN", "OCEAN", "INS", "CV", "DUTY", "MPF", "HMF", "US_SHP", "US_CTR", "DELIV", "UNLOAD", "COGS",
              "REV", "GP", "GM", "SELL_VAR", "SELL_FIX", "FIN", "CONTRIB", "CM", "PEAK", "CASH_TOTAL", "avg_cpb", "avg_price", "f_be"):
        x = base[k]
        print(f"  {k:10s} {x:,.4f}" if isinstance(x, float) else f"  {k:10s} {x}")
    print("  cpb", {k: round(v, 4) for k, v in base["cpb"].items()})
    print("  price", {k: round(v, 4) for k, v in base["price"].items()})
    print("  maxexw", {k: round(v, 3) for k, v in base["maxexw"].items()})
    print()
    print("Scenario × config (D1) avg cost/box | avg price | GM | CM")
    for r in rows:
        if r["di"] == 0:
            print(f"  {I.SCENARIOS[r['s']]:6s} {I.CONFIGS[r['ci']]['key']:4s} U={r['U']:>9,.0f} cpb={r['avg_cpb']:.4f} p={r['avg_price']:.4f} GM={r['GM']:+.1%} CM={r['CM']:+.1%} peak=${r['PEAK']:,.0f}")
    print()
    print("Destinations (BASE, C1):")
    for r in rows:
        if r["s"] == 1 and r["ci"] == 0:
            print(f"  {I.DESTINATIONS[r['di']]['key']} {I.DESTINATIONS[r['di']]['city'][:30]:30s} cpb={r['avg_cpb']:.4f} GM={r['GM']:+.1%} CM={r['CM']:+.1%}")
    print("Break-evens BASE C1 D1: supplier chg for GM25", round(base["chg_gm_t"],3), "GM0", round(base["chg_gm_0"],3),
          "max ocean/ctr", base["max_ocean"], "U_be25", base["u_be_t"], "U_be0", base["u_be_0"])
    print("Combos:")
    for label, r in combos:
        print(f"  {label:45s} U={r['U']:,.0f} cpb={r['avg_cpb']:.4f} p={r['avg_price']:.4f} GM={r['GM']:+.1%} CM={r['CM']:+.1%}")
    print("Sensitivity (BASE C1 D1):")
    for label, r in sens:
        print(f"  {label:45s} cpb={r['avg_cpb']:.4f} GM={r['GM']:+.1%} CM={r['CM']:+.1%}")
