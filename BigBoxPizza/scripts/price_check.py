"""US pizza-box price check (October 2026): what US pizzerias pay per box, by size and buying channel.

    python3 BigBoxPizza/scripts/price_check.py     → BigBoxPizza/working/03_us_pizza_box_price_check.md

Reads data/us_pizza_box_prices_2026-10-16.csv [S102] (one row per listing seen online; prices from search-result extracts,
because the session's network policy blocked opening the pages). Rows marked in_average=Yes are regular single-case
prices of plain or stock-print boxes from mainstream sellers; premium, custom-print, clearance and outlier rows are
kept for the record but left out of the averages. The what-if re-runs the cost engine with the model's BASE listing
prices replaced by the market averages; it does not change inputs.py.
"""
import csv
import os
import statistics as st
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import engine as E  # noqa: E402
import inputs as I  # noqa: E402

DATA = os.path.join(PROJ, "data", "us_pizza_box_prices_2026-10-16.csv")
SIZE_SKU = {12: "3460", 14: "3464", 16: "3463"}


def load(path=DATA):
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["size_in"] = int(r["size_in"])
        r["per_box"] = float(r["pack_price_usd"]) / int(r["pack_qty"])
    return rows


def stats(rows):
    out = {}
    for size in sorted({r["size_in"] for r in rows}):
        reg = [r for r in rows if r["size_in"] == size and r["in_average"] == "Yes"]
        deals = [r for r in rows if r["size_in"] == size and r["price_kind"] == "Volume or sale"]
        if not reg:
            continue
        p = [r["per_box"] for r in reg]
        out[size] = dict(n=len(p), sellers=len({r["seller"] for r in reg}), mean=st.mean(p), median=st.median(p), lo=min(p), hi=max(p),
                         cheapest=min(reg, key=lambda r: r["per_box"]), best_deal=min(deals, key=lambda r: r["per_box"]) if deals else None,
                         by_channel={c: st.mean([r["per_box"] for r in reg if r["channel"] == c]) for c in sorted({r["channel"] for r in reg})})
    return out


def what_if(s):
    """Engine re-run with BASE listing prices set to the market averages (12" scaled to E-flute, as in the model)."""
    base = {k: E.compute(1, ci, 0) for k, ci in (("C1", 0), ("C4", 3), ("C5", 4), ("C6", 5), ("C7", 6))}
    edisc = I.MARKET["eflute_disc"]["v"][1]
    keep = {k: I.MARKET["listing"][k]["v"] for k in I.MARKET["listing"]}
    new = {"3464": s[14]["mean"], "3463": s[16]["mean"], "3460": s[12]["mean"] * (1 - edisc)}
    try:
        for k, v in new.items():
            lo, _, hi = keep[k]
            I.MARKET["listing"][k]["v"] = (lo, v, hi)
        alt = {k: E.compute(1, ci, 0) for k, ci in (("C1", 0), ("C4", 3), ("C5", 4), ("C6", 5), ("C7", 6))}
        rep = {k: E.compute(1, ci, 0, dict(testfac=0.0)) for k, ci in (("C1", 0), ("C4", 3), ("C5", 4), ("C6", 5), ("C7", 6))}
    finally:
        for k, v in keep.items():
            I.MARKET["listing"][k]["v"] = v
    return base, alt, rep, new


def usd(x, d=3):
    return ("−" if x < 0 else "") + f"${abs(x):,.{d}f}"


def pct(x):
    return ("−" if x < 0 else "+") + f"{abs(x) * 100:.1f}%"


def report(rows, s, wi):
    base, alt, rep, new = wi
    L = ["# US pizza-box price check, October 2026\n",
         f"{len(rows)} listings from {len({r['seller'] for r in rows})} sellers, read from search-result extracts on 16 Oct 2026 "
         "(the network policy blocked opening the pages). Averages use regular single-case prices of plain or stock-print boxes "
         "from mainstream sellers; premium, custom-print, clearance and outlier listings are recorded but excluded. Data: "
         "`data/us_pizza_box_prices_2026-10-16.csv`.\n",
         "## What pizzerias pay per box (regular case-of-50 prices)\n",
         "| Size | Listings | Sellers | Average | Median | Range | Cheapest regular price | Best bulk or sale price | Model BASE listing |",
         "|---|---:|---:|---:|---:|---|---|---|---:|"]
    for size, x in s.items():
        sku = SIZE_SKU.get(size)
        model = I.MARKET["listing"][sku]["v"][1] if sku else None
        bd = x["best_deal"]
        L.append(f"| {size}\" | {x['n']} | {x['sellers']} | {usd(x['mean'])} | {usd(x['median'])} | {usd(x['lo'])}–{usd(x['hi'])} | "
                 f"{usd(x['cheapest']['per_box'])} ({x['cheapest']['seller']}) | "
                 f"{(usd(bd['per_box']) + ' (' + bd['seller'] + ', ' + bd['note'] + ')') if bd else '—'} | {usd(model) if model else '—'} |")
    L.append("\n## Average by buying channel\n")
    chans = sorted({c for x in s.values() for c in x["by_channel"]})
    L.append("| Size | " + " | ".join(chans) + " |")
    L.append("|---|" + "---:|" * len(chans))
    for size, x in s.items():
        L.append(f"| {size}\" | " + " | ".join(usd(x["by_channel"][c]) if c in x["by_channel"] else "—" for c in chans) + " |")
    L.append("\n## Operator and trade reports (not averaged)\n")
    for r in rows:
        if r["price_kind"] == "Operator report":
            L.append(f"- {r['size_in']}\" — {usd(r['per_box'], 2)} per box: {r['seller']}, {r['product']} ({r['note']}). {r['url']}")
    L.append("\n## What-if: BigBoxPizza sells at prices based on the market average\n")
    L.append("The model's BASE listing prices are the cheapest online prices (WebstaurantStore). Replacing them with the market averages "
             f"(12\" scaled to E-flute: {usd(new['3460'])}; 14\" {usd(new['3464'])}; 16\" {usd(new['3463'])}) and keeping every cost and "
             "the 20% E-flute discount and 25% buyer margin:\n")
    L.append("| Configuration | Buyer price (avg) | Gross margin, model | Gross margin, market average | Margin after all costs, market average | Result, first shipment | Result, repeat shipment | Margin after all costs, repeat |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    names = {"C1": "Quoted 60,000 mix, one 40' HC", "C4": "Full 40' HC, equal mix", "C5": "Full 40' HC, 14\" only", "C6": "Full 40' HC, 16\" only",
             "C7": "Full 40' HC, 12\" only"}
    for k in ("C1", "C4", "C5", "C6", "C7"):
        b, a = base[k], alt[k]
        r = rep.get(k)
        L.append(f"| {names[k]} | {usd(a['avg_price'])} | {pct(b['GM'])} | {pct(a['GM'])} | {pct(a['CM'])} | {usd(a['CONTRIB'], 0)} | "
                 f"{usd(r['CONTRIB'], 0) if r else '—'} | {pct(r['CM']) if r else '—'} |")
    L.append("")
    return "\n".join(L)


def main(out=None):
    rows = load()
    s = stats(rows)
    wi = what_if(s)
    out = out or os.path.join(PROJ, "working", "03_us_pizza_box_price_check.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report(rows, s, wi))
    return rows, s, wi


if __name__ == "__main__":
    rows, s, wi = main()
    for size, x in s.items():
        print(size, x["n"], round(x["mean"], 3), round(x["median"], 3), round(x["lo"], 3), round(x["hi"], 3), {c: round(v, 3) for c, v in x["by_channel"].items()})
    base, alt, rep, new = wi
    print("new listings", {k: round(v, 3) for k, v in new.items()})
    for k in alt:
        print(k, "GM", round(base[k]["GM"], 3), "->", round(alt[k]["GM"], 3), "CM", round(alt[k]["CM"], 3), "CONTRIB", round(alt[k]["CONTRIB"]),
              "repeat", round(rep[k]["CONTRIB"]) if k in rep else None, "price", round(alt[k]["avg_price"], 4))
