"""Static report charts (PNG). Palette: validated default categorical order (dataviz skill
reference palette, light mode); diverging blue↔red for favourable/adverse. Legends always present
for ≥2 series; selective direct labels; hairline solid grid; text in text tokens."""
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import textwrap  # noqa: E402

import engine as E  # noqa: E402
import inputs as I  # noqa: E402

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT2 = "#52514e"
GRID = "#e6e5e1"
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
FAV, ADV = "#2a78d6", "#e34948"


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=TEXT2, labelsize=9, length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def cost_components(r):
    comps = {}
    for code in [k["code"] for k in I.SKUS]:
        if r["units"][code] == 0:
            continue
        sale = r["sale_units"][code]
        csh = r["units"][code] * 0  # placeholder
        vol_share = (r["units"][code] * E.unit_props(r["s"])[code]["vol"]) / r["V"]
        u_share = r["units"][code] / r["U"]
        v_share = (r["SUP"] and r["sup"][code] / r["SUP"])
        cv_k = r["sup"][code] * (1 + (I.SUPPLIER["vat_rate"]["v"][r["s"]] if r["drivers"]["vatmode"] == 3 else 0)) + r["tooling"] * u_share
        cv_share = cv_k / r["CV"]
        duty_rate = I.CUSTOMS["mfn"]["v"][r["s"]] + r["drivers"]["s301"]
        comps[code] = [
            (r["sup"][code] + (r["sup"][code] * I.SUPPLIER["vat_rate"]["v"][r["s"]] if r["drivers"]["vatmode"] == 3 else 0) + r["tooling"] * u_share) / sale,
            (r["orig_ctr"] * vol_share + r["orig_shp"] * u_share) / sale,
            (r["OCEAN"] * vol_share + r["INS"] * v_share) / sale,
            (cv_k * duty_rate + (r["MPF"] + r["HMF"]) * cv_share) / sale,
            (r["US_SHP"] * u_share + r["US_CTR"] * vol_share) / sale,
            ((r["DELIV"] + r["UNLOAD"]) * vol_share) / sale,
        ]
        assert abs(sum(comps[code]) - r["cpb"][code]) < 1e-9, (code, sum(comps[code]), r["cpb"][code])
    return comps


def chart_cost_stack(r, path, title):
    comps = cost_components(r)
    labels = ["Supplier (EXW)", "Egypt origin", "Ocean freight + insurance", "Duty + MPF/HMF", "US entry & port", "Delivery & unloading"]
    names = {"3464": '3464 (14")', "3463": '3463 (16")', "3460": '3460 (12")'}
    rows = [c for c in ["3464", "3463", "3460"] if c in comps]
    fig, ax = plt.subplots(figsize=(10, 3.9), facecolor=SURFACE)
    _style(ax)
    for yi, code in enumerate(rows):
        left = 0.0
        for j, v in enumerate(comps[code]):
            ax.barh(yi, v, left=left, height=0.52, color=CAT[j], edgecolor=SURFACE, linewidth=1.6, label=labels[j] if yi == 0 else None)
            left += v
        ax.text(left + 0.004, yi, f"${left:.3f}", va="center", ha="left", fontsize=9, color=TEXT)
        p = r["price"][code]
        ax.plot([p, p], [yi - 0.36, yi + 0.36], color=TEXT, linewidth=2)
        ax.text(p + 0.002, yi - 0.30, f"price ${p:.3f}", ha="left", va="bottom", fontsize=8, color=TEXT)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([names[c] for c in rows], fontsize=10, color=TEXT)
    ax.invert_yaxis()
    ax.set_xlabel("USD per saleable box (delivered to customer)", color=TEXT2, fontsize=9)
    ax.set_xlim(0, max(sum(v) for v in comps.values()) * 1.18)
    ax.set_title(title, loc="left", fontsize=11, color=TEXT)
    ax.plot([], [], color=TEXT, linewidth=2, label="Achievable wholesale price")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=4, frameon=False, fontsize=8, labelcolor=TEXT2)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor=SURFACE)
    plt.close(fig)


def chart_tornado(base, sens, path, title, top=10):
    pairs = []
    for i in range(0, 30, 2):
        lo_lab, lo = sens[i]
        hi_lab, hi = sens[i + 1]
        d1 = (lo["CM"] - base["CM"]) * 100
        d2 = (hi["CM"] - base["CM"]) * 100
        driver = lo_lab.split(":")[0].split(" ")[0] if lo_lab.startswith("FX") else lo_lab
        pairs.append((abs(d1 - d2), lo_lab, d1, hi_lab, d2))
    pairs.sort(reverse=True)
    pairs = pairs[:top]
    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor=SURFACE)
    _style(ax)
    for yi, (sw, l1, d1, l2, d2) in enumerate(pairs):
        for lab, d in ((l1, d1), (l2, d2)):
            ax.barh(yi, d, height=0.5, color=FAV if d > 0 else ADV, edgecolor=SURFACE, linewidth=1.2)
        ax.text(min(d1, d2) - 0.8, yi, f"{min(d1, d2):+.0f}".replace("-", "−"), va="center", ha="right", fontsize=8, color=TEXT2)
        ax.text(max(d1, d2) + 0.8, yi, f"{max(d1, d2):+.0f}".replace("-", "−"), va="center", ha="left", fontsize=8, color=TEXT2)
    ax.set_yticks(range(len(pairs)))
    # label order follows the bars: adverse case (left bar) first, favourable case (right bar) second
    ax.set_yticklabels([f"{p[1]}  /  {p[3]}" if p[2] <= p[4] else f"{p[3]}  /  {p[1]}" for p in pairs], fontsize=8, color=TEXT)
    ax.invert_yaxis()
    ax.axvline(0, color=TEXT2, linewidth=0.8)
    ax.set_xlabel(f"Change in contribution margin vs base case ({base['CM']:.1%}), percentage points\nRow labels read: adverse case  /  favourable case".replace("-", "−"),
                  color=TEXT2, fontsize=9)
    lo_all = min(min(p[2], p[4]) for p in pairs)
    hi_all = max(max(p[2], p[4]) for p in pairs)
    ax.set_xlim(lo_all - 6, hi_all + 6)
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=TEXT)
    ax.legend(handles=[Patch(color=FAV, label="Favourable change"), Patch(color=ADV, label="Adverse change")],
              loc="lower right", frameon=False, fontsize=8, labelcolor=TEXT2)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor=SURFACE)
    plt.close(fig)


def chart_configs(rows_by, s, di, path, title):
    fig, ax = plt.subplots(figsize=(10, 4.8), facecolor=SURFACE)
    _style(ax)
    for ci, c in enumerate(I.CONFIGS):
        r = rows_by[(s, ci, di)]
        ax.barh(ci, r["avg_cpb"], height=0.5, color=CAT[0], edgecolor=SURFACE, linewidth=1.2, label="Delivered cost per box" if ci == 0 else None)
        ax.plot([r["avg_price"]] * 2, [ci - 0.36, ci + 0.36], color=TEXT, linewidth=2, label="Achievable price (avg)" if ci == 0 else None)
        ax.text(max(r["avg_cpb"], r["avg_price"]) + 0.006, ci, f"GM {r['GM']:+.0%}".replace("-", "−"), va="center", fontsize=8, color=TEXT2)
    ax.set_yticks(range(len(I.CONFIGS)))
    ax.set_yticklabels([f"{c['key']} {re.sub(r'\s*\(.*\)$', '', c['name'])}" for c in I.CONFIGS], fontsize=8, color=TEXT)
    ax.invert_yaxis()
    ax.set_xlabel("USD per saleable box", color=TEXT2, fontsize=9)
    ax.set_xlim(0, max(rows_by[(s, ci, di)]["avg_cpb"] for ci in range(len(I.CONFIGS))) * 1.16)
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=TEXT)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2, frameon=False, fontsize=8, labelcolor=TEXT2)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor=SURFACE)
    plt.close(fig)


def chart_path(combos, path, title, cm_min):
    fig, ax = plt.subplots(figsize=(10, 4.8), facecolor=SURFACE)
    _style(ax)
    ax.xaxis.grid(False)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    xs = range(len(combos))
    vals = [r["CM"] * 100 for _, r in combos]
    ax.bar(xs, vals, width=0.55, color=CAT[0], edgecolor=SURFACE, linewidth=1.2)
    for x, v in zip(xs, vals):
        ax.text(x, v + (1.2 if v >= 0 else -1.2), f"{v:+.1f}%".replace("-", "−"), ha="center", va="bottom" if v >= 0 else "top", fontsize=8, color=TEXT)
    ax.axhline(0, color=TEXT2, linewidth=0.8)
    ax.axhline(cm_min * 100, color=TEXT, linewidth=1.0)
    ax.text(-0.45, cm_min * 100 + 0.8, f"go threshold: contribution margin {cm_min:.0%}", ha="left", va="bottom", fontsize=8, color=TEXT2)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([lab.split(" ", 1)[0] + "\n" + "\n".join(textwrap.wrap(lab.split(" ", 1)[1], 22)) for lab, _ in combos], fontsize=7, color=TEXT)
    ax.set_ylim(min(vals) - 7, max(max(vals), cm_min * 100) + 6)
    ax.set_ylabel("Contribution margin (%)", color=TEXT2, fontsize=9)
    fig.suptitle(title, x=0.01, ha="left", fontsize=11, color=TEXT)
    fig.tight_layout()
    fig.savefig(path, dpi=140, facecolor=SURFACE)
    plt.close(fig)


def main(outdir):
    rows, base, sens, combos = E.run_all()
    rows_by = {(r["s"], r["ci"], r["di"]): r for r in rows}
    os.makedirs(outdir, exist_ok=True)
    chart_cost_stack(base, os.path.join(outdir, "chart_cost_stack_vs_price.png"),
                     "Quoted order (60,000 in one 40' HC → Edison NJ, BASE): delivered cost exceeds achievable price for every SKU")
    chart_tornado(base, sens, os.path.join(outdir, "chart_tornado_cm.png"),
                  "What moves contribution margin most (quoted order, BASE) – no single change makes it positive")
    chart_configs(rows_by, 1, 0, os.path.join(outdir, "chart_configs_cost_vs_price.png"),
                  "All shipment configurations, BASE, NY/NJ → Edison: cost per box vs achievable price")
    chart_path(combos, os.path.join(outdir, "chart_path_to_viability.png"),
               "Path to viability (full 40' HC, BASE): only the full combination of favourable changes clears the threshold", I.THRESHOLDS["cm_min"])
    return ["chart_cost_stack_vs_price.png", "chart_tornado_cm.png", "chart_configs_cost_vs_price.png", "chart_path_to_viability.png"]


if __name__ == "__main__":
    import sys
    print(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "outputs")))
