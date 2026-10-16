"""Full-container plan: one 40' high-cube filled with all three sizes, instead of the quoted 60,000 boxes.

    python3 BigBoxPizza/scripts/full_container.py     → BigBoxPizza/working/04_full_container_plan.md

The client plans to fill the container rather than ship the quoted 60,000. The model's configuration C4 is that load:
the largest equal number of each size, in whole bundles of 50, that fits one 40' HC. It is recomputed for each
scenario's bundle size, so thicker bundles mean fewer boxes. This script reports C4 next to the quoted order (C1),
tries other three-size mixes, and works out the one-at-a-time swings, the factory and buyer price targets and the
market-average prices of price_check.py [S102]. It changes no inputs.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import engine as E  # noqa: E402
import inputs as I  # noqa: E402
import loading_model as LM  # noqa: E402
import price_check as PC  # noqa: E402

C1, C4 = 0, 3
SKUS = [k["code"] for k in I.SKUS]
SIZE = {"3464": '14"', "3463": '16"', "3460": '12"'}
HC = LM.container_by_key("40HC")
MIXES = [("Equal numbers of each size (the plan)", {"3460": 1, "3464": 1, "3463": 1}),
         ("Half 12-inch, a quarter each of 14 and 16", {"3460": 2, "3464": 1, "3463": 1}),
         ("Half 16-inch, a quarter each of 12 and 14", {"3460": 1, "3464": 1, "3463": 2})]


def max_mix(weights, s=1):
    """Largest whole-bundle load with these unit proportions that fits one 40' HC (bisection on total bundles)."""
    n = I.BLANK["per_bundle"]["v"][s]
    tot = sum(weights.values())

    def units(tb):
        return {k: int(round(tb * weights[k] / tot)) * n for k in SKUS}

    lo, hi = 0, 6000
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if LM.mixed_load(units(mid), HC, s)["fits"]:
            lo = mid
        else:
            hi = mid - 1
    return units(lo)


def run_units(units, s=1, drivers=None):
    """Engine row for an arbitrary load in one 40' HC to destination D1 (temporary fixed configuration)."""
    I.CONFIGS.append(dict(key="TMP", name="temporary mix", ctype="40HC", n=1, kind="fixed", units=units))
    ci = len(I.CONFIGS) - 1
    try:
        return E.compute(s, ci, 0, drivers)
    finally:
        I.CONFIGS.pop()
        E._UNITS_CACHE.pop((ci, s), None)


def cost_steps(r):
    """Delivered cost per sellable box in six steps (the decision report's cost chart)."""
    S = r["SALE"]
    return [("factory", "Factory price", r["SUP"] / S),
            ("egypt", "Egypt: trucking, port and papers", (r["VAT_ECON"] + r["tooling"] + r["ORIGIN"]) / S),
            ("ocean", "Ocean freight and insurance", (r["OCEAN"] + r["INS"]) / S),
            ("duty", "US duty (12.5%) and customs fees", (r["DUTY"] + r["MPF"] + r["HMF"]) / S),
            ("broker", "Customs broker, filing and port", (r["US_SHP"] + r["US_CTR"]) / S),
            ("truck", "Truck to the buyer and unloading", (r["DELIV"] + r["UNLOAD"]) / S)]


def cash_steps(r):
    """Cash in and out by day for one shipment (commission and admin counted when the buyer pays)."""
    admin = I.SELLING["admin"]["v"][r["s"]]
    return [("order", 0, "Order: deposit and samples", -r["out0"]),
            ("export", r["t1"], "Factory balance, freight and Egypt costs", -r["out1"]),
            ("customs", r["t2"], "US duty and customs fees", -r["out2"]),
            ("delivery", r["t3"], "Delivery truck and unloading", -r["out3"]),
            ("vat", r["t_ref"], "VAT refund", r["vat_ref"]),
            ("paid", r["t4"], "Buyer pays", r["REV"] - r["SELL_VAR"] - admin)]


def swings(ci, s=1):
    """Change in margin after all costs (points) as each quoted number moves across its tested range."""
    b = E.compute(s, ci, 0)
    t = I.SELLING["testing"]["v"]
    hc = I.OCEAN["rate_hc"]["v"]
    cbe, spread = I.FX["cbe"]["v"], I.FX["spread"]["v"][s]
    u = {sc: sum(E.config_units(ci, sc).values()) for sc in range(3)}
    ufew, umore = u[2] / u[1], max(u[0] / u[1], 1.0)
    rows = [
        ("buyer-price", "Buyer prices", "quote 1", "15% lower to 15% higher", dict(pricefac=0.85), dict(pricefac=1.15)),
        ("boxes-per-container", "Boxes per container", "quote 2",
         f"{(1 - ufew) * 100:.0f}% fewer to {(umore - 1) * 100:.0f}% more", dict(unitsfac=ufew), dict(unitsfac=umore)),
        ("lab-tests", "Lab tests and samples", "quote 6", f"${t[2]:,.0f} to ${t[0]:,.0f}", dict(testfac=t[2] / t[1]), dict(testfac=t[0] / t[1])),
        ("us-duty", "US duty", "quote 4", "25% to none", dict(s301=0.25), dict(s301=0.0)),
        ("ocean", "Ocean freight", "quote 3", "dearest to cheapest found", dict(oceanfac=hc[2] / hc[1]), dict(oceanfac=hc[0] / hc[1])),
        ("factory-price", "Factory price", "quote 2", "10% higher to 10% lower", dict(supfac=1.1), dict(supfac=0.9)),
        ("trucking", "Trucking and unloading", "quote 7", "dearer to buyer unloads", dict(drayfac=1.5, unloadfac=2.0), dict(drayfac=0.75, unloadfac=0.0)),
        ("vat", "Egyptian VAT", "quote 5", "never refunded to VAT-free", dict(vatmode=3), dict(vatmode=1)),
        ("fx", "Exchange rate", "quote 9", f"EGP {cbe[2]:g} to EGP {cbe[0]:g} per dollar", dict(fx=cbe[2] * (1 - spread)), dict(fx=cbe[0] * (1 - spread))),
    ]
    out = []
    for slug, quote, q, rng, adv, fav in rows:
        out.append(dict(slug=slug, quote=quote, q=q, range=rng,
                        adv=(E.compute(s, ci, 0, adv)["CM"] - b["CM"]) * 100, fav=(E.compute(s, ci, 0, fav)["CM"] - b["CM"]) * 100))
    return b, out, dict(ufew=ufew, umore=umore, units=u)


def price_for_gm(ci, gm, s=1):
    """Selling-price factor that gives this gross margin (bisection), and the margin after all costs there."""
    lo, hi = 0.5, 3.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if E.compute(s, ci, 0, dict(pricefac=mid))["GM"] < gm:
            lo = mid
        else:
            hi = mid
    r = E.compute(s, ci, 0, dict(pricefac=hi))
    return hi, r["CM"]


def results():
    import write_reports as WR  # local import: write_reports also imports this module

    out = dict(c4={}, c1={})
    for s in range(3):
        out["c4"][s] = E.compute(s, C4, 0)
        out["c1"][s] = E.compute(s, C1, 0)
    out["c4_rep"] = E.compute(1, C4, 0, dict(testfac=0.0))
    out["c1_rep"] = E.compute(1, C1, 0, dict(testfac=0.0))
    out["load"] = {s: LM.mixed_load(E.config_units(C4, s), HC, s) for s in range(3)}
    out["load_c1"] = LM.mixed_load(E.config_units(C1, 1), HC, 1)
    b = out["c4"][1]
    out["steps"] = cost_steps(b)
    out["cash"] = cash_steps(b)
    out["swing_base"], out["swings"], out["swing_units"] = swings(C4)
    out["max_exw"] = {0.0: WR.max_exw(b, 0.0), 0.25: WR.max_exw(b, 0.25)}
    out["one_size"] = {code: E.compute(1, ci, 0) for code, ci in (("3464", 4), ("3463", 5), ("3460", 6))}
    out["one_size_exw"] = {g: {code: WR.max_exw(r, g)[code] for code, r in out["one_size"].items()} for g in (0.0, 0.25)}
    out["gm25_price"], out["gm25_cm"] = price_for_gm(C4, I.THRESHOLDS["gm_go"])
    out["free_ocean_gm"] = E.compute(1, C4, 0, dict(oceanfac=0.0))["GM"]
    out["no_duty_gm"] = E.compute(1, C4, 0, dict(s301=0.0))["GM"]
    pcs = PC.stats(PC.load())
    with PC.market_average(pcs):
        out["avg"] = E.compute(1, C4, 0)
        out["avg_rep"] = E.compute(1, C4, 0, dict(testfac=0.0))
        out["avg_c1"] = E.compute(1, C1, 0)
    mixes = []
    for label, w in MIXES:
        u = max_mix(w)
        r, rr = run_units(u), run_units(u, drivers=dict(testfac=0.0))
        with PC.market_average(pcs):
            a, ar = run_units(u), run_units(u, drivers=dict(testfac=0.0))
        mixes.append(dict(label=label, units=u, r=r, rep=rr, avg=a, avg_rep=ar))
    out["mixes"] = mixes
    fx = b["drivers"]["fx"]
    sub = sum(b["units"][k["code"]] * k["price_egp"] for k in I.SKUS)
    vat = sub * I.SUPPLIER["vat_rate"]["v"][1]
    out["order"] = dict(units=b["units"], sub_egp=sub, vat_egp=vat, total_egp=sub + vat, total_usd=(sub + vat) / fx, fx=fx)
    # Guards: the decision report states these in words
    assert all(m["units"] == E.config_units(C4, 1) for m in mixes[:1]), "equal mix matches configuration C4"
    assert b["CONTRIB"] < 0 and out["c4_rep"]["CONTRIB"] < 0, "narrative: the full mixed container loses money, first and repeat"
    assert out["avg_rep"]["CM"] < I.THRESHOLDS["cm_min"], "narrative: at market averages a full mixed container still misses the 12% minimum"
    return out


def usd(x, d=0):
    return ("−" if x < 0 else "") + f"${abs(x):,.{d}f}"


def pct(x, d=1):
    return ("−" if x < 0 else "+") + f"{abs(x) * 100:.{d}f}%"


def report(res):
    b, c1, rep = res["c4"][1], res["c1"][1], res["c4_rep"]
    L = ["# Full-container plan: one 40' high-cube of all three sizes\n",
         "The client plans to fill one 40' high-cube with a mix of the three sizes instead of ordering the quoted 60,000 boxes. "
         "The model's configuration C4 is that load: the largest equal number of each size, in whole bundles of 50, that fits. "
         "Middle case (BASE), New York/New Jersey → Edison NJ, unless stated. Generated by `scripts/full_container.py`; no inputs changed.\n",
         "## The load\n",
         "| Case | Boxes per size | Total boxes | Container length used | Weight (share of the US road limit) |", "|---|---:|---:|---:|---:|"]
    for s, nm in ((0, "LOW (thinner bundles)"), (1, "BASE"), (2, "STRESS (thicker bundles)")):
        u = E.config_units(C4, s)
        m = res["load"][s]
        L.append(f"| {nm} | {u['3464']:,} | {sum(u.values()):,} | {m['len_util'] * 100:.0f}% | {m['tot_kg'] / 1000:.1f} t ({m['payload_util'] * 100:.0f}%) |")
    o = res["order"]
    L.append(f"\nFactory order at the quoted prices: EGP {o['sub_egp']:,.0f} plus 14% VAT EGP {o['vat_egp']:,.0f} = EGP {o['total_egp']:,.0f}, "
             f"about {usd(o['total_usd'])} at EGP {o['fx']:.2f} per dollar (quoted order: EGP 528,162).\n")
    L += ["## Results against the quoted order\n",
          "| Measure | Quoted 60,000 (C1) | Full container (C4) |", "|---|---:|---:|"]
    rows = [("Boxes shipped", f"{c1['U']:,.0f}", f"{b['U']:,.0f}"),
            ("Delivered cost per sellable box", usd(c1["avg_cpb"], 3), usd(b["avg_cpb"], 3)),
            ("Buyer price (our estimate)", usd(c1["avg_price"], 3), usd(b["avg_price"], 3)),
            ("Gross margin", pct(c1["GM"]), pct(b["GM"])),
            ("Result, first shipment", usd(c1["CONTRIB"]), usd(b["CONTRIB"])),
            ("Margin after all costs", pct(c1["CM"]), pct(b["CM"])),
            ("Result, repeat shipment", usd(res["c1_rep"]["CONTRIB"]), usd(rep["CONTRIB"])),
            ("Best case (LOW), first shipment", usd(res["c1"][0]["CONTRIB"]), usd(res["c4"][0]["CONTRIB"])),
            ("Worst case (STRESS), first shipment", usd(res["c1"][2]["CONTRIB"]), usd(res["c4"][2]["CONTRIB"])),
            ("Peak cash tied up", usd(c1["PEAK"]), usd(b["PEAK"])),
            ("Buyer price rise needed to break even", pct(c1["f_be"] - 1, 0), pct(b["f_be"] - 1, 0)),
            ("Factory price cut needed to cover delivered cost", pct(c1["chg_gm_0"], 0), pct(b["chg_gm_0"], 0)),
            ("At average US prices [S102]: first shipment", usd(res["avg_c1"]["CONTRIB"]), usd(res["avg"]["CONTRIB"])),
            ("At average US prices: repeat shipment (margin after all costs)", "see price check", f"{usd(res['avg_rep']['CONTRIB'])} ({pct(res['avg_rep']['CM'])})")]
    L += [f"| {a} | {x} | {y} |" for a, x, y in rows]
    L += ["\n## Cost and price by size, full container\n", "| Size | Boxes | Delivered cost | Buyer price | Gain or loss per box | Gross margin |",
          "|---|---:|---:|---:|---:|---:|"]
    for k in ("3460", "3464", "3463"):
        c, p = b["cpb"][k], b["price"][k]
        L.append(f"| {SIZE[k]} | {b['units'][k]:,.0f} | {usd(c, 3)} | {usd(p, 3)} | {usd(p - c, 3)} | {pct((p - c) / p)} |")
    L += ["\n## Other three-size mixes (each fills the container)\n",
          "| Mix | 12\" / 14\" / 16\" boxes | Total | Result, first shipment | At average prices: first | repeat | gross margin | margin after all costs, repeat |",
          "|---|---|---:|---:|---:|---:|---:|---:|"]
    for m in res["mixes"]:
        u = m["units"]
        L.append(f"| {m['label']} | {u['3460']:,} / {u['3464']:,} / {u['3463']:,} | {sum(u.values()):,} | {usd(m['r']['CONTRIB'])} | "
                 f"{usd(m['avg']['CONTRIB'])} | {usd(m['avg_rep']['CONTRIB'])} | {pct(m['avg']['GM'])} | {pct(m['avg_rep']['CM'])} |")
    L += ["\n## Targets for the full container\n", "| Size | Quoted factory price (EGP) | Highest factory price, covers cost | Highest, 25% gross margin | Buyer price needed, 25% gross margin |",
          "|---|---:|---:|---:|---:|"]
    for k in I.SKUS:
        c = k["code"]
        L.append(f"| {SIZE[c]} | {k['price_egp']:.3f} | {res['max_exw'][0.0][c]:.2f} | {res['max_exw'][0.25][c]:.2f} | {usd(b['cpb'][c] / 0.75, 3)} |")
    L.append(f"\nAt a 25% gross margin the full container keeps {pct(res['gm25_cm'])} after all costs. Free ocean freight would give "
             f"{pct(res['free_ocean_gm'])} gross margin; removing the 12.5% duty adds {(res['no_duty_gm'] - b['GM']) * 100:.1f} points.\n")
    L += ["## One-at-a-time swings, full container (points of margin after all costs)\n", "| Quote | Range | Worse | Better |", "|---|---|---:|---:|"]
    for w in res["swings"]:
        L.append(f"| {w['quote']} ({w['q']}) | {w['range']} | {w['adv']:+.1f} | {w['fav']:+.1f} |")
    L.append(f"\nMargin after all costs today: {pct(b['CM'])}.\n")
    L += ["## Cost per sellable box, full container\n", "| Step | $/box |", "|---|---:|"]
    L += [f"| {lab} | {usd(v, 4)} |" for _, lab, v in res["steps"]]
    L.append(f"| Delivered cost | {usd(b['avg_cpb'], 4)} |\n")
    L += ["## Cash by day, full container\n", "| Day | Event | Amount |", "|---:|---|---:|"]
    L += [f"| {d:.0f} | {ev} | {usd(a)} |" for _, d, ev, a in res["cash"]]
    L.append(f"\nPeak cash out {usd(b['PEAK'])}.\n")
    return "\n".join(L)


def main(out=None):
    res = results()
    out = out or os.path.join(PROJ, "working", "04_full_container_plan.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report(res))
    return res


if __name__ == "__main__":
    res = main()
    if "--json" in sys.argv:
        keep = ("U", "SALE", "avg_cpb", "avg_price", "GM", "CM", "CONTRIB", "REV", "COGS", "GP", "SELL_VAR", "SELL_FIX", "FIN", "PEAK",
                "CASH_TOTAL", "f_be", "chg_gm_0", "chg_gm_t", "OCEAN", "DUTY", "INS", "ORIGIN", "SUP", "kg", "units", "cpb", "price",
                "out0", "out1", "out2", "out3", "vat_ref", "t1", "t2", "t3", "t4", "t_ref", "US_SHP", "US_CTR", "MPF", "HMF")
        slim = lambda r: {k: r[k] for k in keep if k in r}  # noqa: E731
        print(json.dumps(dict(c4={s: slim(r) for s, r in res["c4"].items()}, c1={s: slim(r) for s, r in res["c1"].items()},
                              c4_rep=slim(res["c4_rep"]), c1_rep=slim(res["c1_rep"]), avg=slim(res["avg"]), avg_rep=slim(res["avg_rep"]),
                              avg_c1=slim(res["avg_c1"]), steps=res["steps"], cash=res["cash"], swings=res["swings"], swing_units=res["swing_units"],
                              max_exw={str(g): v for g, v in res["max_exw"].items()}, one_size={c: slim(r) for c, r in res["one_size"].items()},
                              one_size_exw={str(g): v for g, v in res["one_size_exw"].items()}, gm25_price=res["gm25_price"], gm25_cm=res["gm25_cm"],
                              free_ocean_gm=res["free_ocean_gm"], no_duty_gm=res["no_duty_gm"], order=res["order"],
                              load={s: dict(len_util=m["len_util"], tot_kg=m["tot_kg"], payload_util=m["payload_util"],
                                            rows=[dict(sku=x["sku"], units=x["units"], bundles=x["bundles"], zone_len=x["zone_len"], layers=x["layers"]) for x in m["rows"]],
                                            Lu=m["Lu"]) for s, m in res["load"].items()},
                              mixes=[dict(label=m["label"], units=m["units"], first=m["r"]["CONTRIB"], rep=m["rep"]["CONTRIB"], cpb=m["r"]["avg_cpb"],
                                          avg_first=m["avg"]["CONTRIB"], avg_rep=m["avg_rep"]["CONTRIB"], avg_gm=m["avg"]["GM"], avg_rep_cm=m["avg_rep"]["CM"])
                                     for m in res["mixes"]]), indent=1, default=float))
