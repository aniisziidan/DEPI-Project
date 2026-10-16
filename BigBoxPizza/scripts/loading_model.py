"""Container loading geometry for flat-packed pizza-box blanks.

Two independent methods are used:
  1. `pattern_positions` – a closed-form "row-mix" floor pattern (n1 rows with the
     bundle's long side along the container + n2 rows rotated 90°, n2 = 0..2).
     This is exactly what the Excel workbook implements with formulas.
  2. `dp_positions` – an exhaustive two-dimensional guillotine dynamic program over
     raster points (validation).  If it finds more floor positions than (1), the
     difference is reported as upside that a load planner could capture.
Heights: bundles are stacked flat in full-height columns ("stacks").
Mixed loads: each SKU occupies its own block of container length ("zone").

All dimensions in mm, weights in kg.  PROVISIONAL: blank and bundle geometry is an
engineering estimate until NFC supplies die-lines, bundle counts and bundle sizes.
"""
from functools import lru_cache
import math

import inputs as I

S_IDX = {"LOW": 0, "BASE": 1, "STRESS": 2}


def v(inp, s):
    return inp["v"][s]


# ----------------------------------------------------------------------------- blanks & bundles
def blank(sku, s):
    k = v(I.BLANK["k_len"], s)
    allow = v(I.BLANK["w_allow"], s)
    Lb = 2 * sku["L"] + k * sku["H"]
    Wb = sku["W"] + 2 * sku["H"] + allow
    area = Lb * Wb / 1e6
    wt = area * v(I.BLANK["net_area"], s) * v(I.BLANK["grammage"], s) / 1000.0
    return dict(Lb=Lb, Wb=Wb, area=area, weight=wt)


def bundle(sku, s):
    b = blank(sku, s)
    wrap = v(I.BLANK["wrap_mm"], s)
    n = v(I.BLANK["per_bundle"], s)
    a = b["Lb"] + wrap
    bb = b["Wb"] + wrap
    h = n * v(I.BLANK["pitch"], s)
    w = n * b["weight"] + v(I.BLANK["wrap_kg"], s)
    return dict(a=a, b=bb, h=h, weight=w, n=n, vol=a * bb * h / 1e9, blank=b)


def usable(ct, s):
    Lu = ct["L"] - v(I.USABLE["len_ded"], s)
    Wu = ct["W"] - v(I.USABLE["wid_ded"], s)
    Hu = min(ct["H"] - v(I.USABLE["hgt_ded"], s), ct["door_H"])
    return Lu, Wu, Hu


# ----------------------------------------------------------------------------- floor patterns
def pattern_positions(Lu, Wu, a, b, n2max=2):
    """Best row-mix pattern; returns (positions, n2, n1)."""
    best = (0, 0, 0)
    for n2 in range(0, n2max + 1):
        rem = Wu - n2 * a
        if rem < 0:
            continue
        n1 = int(rem // b)
        pos = n1 * int(Lu // a) + n2 * int(Lu // b)
        if pos > best[0]:
            best = (pos, n2, n1)
    return best


def dp_positions(Lu, Wu, a, b):
    """Exact max number of a×b rectangles (rotation allowed) in Lu×Wu under guillotine cuts."""
    a, b = int(round(a)), int(round(b))
    Lu, Wu = int(Lu), int(Wu)

    def raster(X):
        pts = set()
        for i in range(0, X // a + 1):
            for j in range(0, (X - i * a) // b + 1):
                pts.add(i * a + j * b)
        return sorted(pts)

    RL, RW = raster(Lu), raster(Wu)

    def down(R, x):
        lo, hi = 0, len(R) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if R[mid] <= x:
                lo = mid
            else:
                hi = mid - 1
        return R[lo]

    @lru_cache(maxsize=None)
    def f(x, y):
        best = 0
        if x >= a and y >= b:
            best = max(best, (x // a) * (y // b))
        if x >= b and y >= a:
            best = max(best, (x // b) * (y // a))
        for x1 in RL:
            if x1 <= 0:
                continue
            if x1 > x // 2:
                break
            best = max(best, f(x1, y) + f(down(RL, x - x1), y))
        for y1 in RW:
            if y1 <= 0:
                continue
            if y1 > y // 2:
                break
            best = max(best, f(x, y1) + f(x, down(RW, y - y1)))
        return best

    return f(down(RL, Lu), down(RW, Wu))


def zone_length(S, Wu, a, b, Lmax, n2max=2):
    """Minimum block length holding S stacks (exact search over candidate lengths)."""
    if S <= 0:
        return 0.0, 0, 0
    best = (math.inf, None, None)
    for n2 in range(0, n2max + 1):
        rem = Wu - n2 * a
        if rem < 0:
            continue
        n1 = int(rem // b)
        if n1 == 0 and n2 == 0:
            continue
        cands = sorted({i * a for i in range(1, int(Lmax // a) + 2)} | {j * b for j in range(1, int(Lmax // b) + 2)})
        for L in cands:
            if n1 * int(L // a) + n2 * int(L // b) >= S:
                if L < best[0]:
                    best = (L, n2, n1)
                break
    return best


def zone_length_excel(S, Wu, a, b, n2max=2):
    """Replicates the Excel closed-form candidate method (used to cross-check the workbook)."""
    if S <= 0:
        return 0.0
    best = math.inf
    for n2 in range(0, n2max + 1):
        rem = Wu - n2 * a
        if rem < 0:
            continue
        n1 = int(rem // b)
        if n1 == 0 and n2 == 0:
            continue
        rate_a = n1 + n2 * a / b          # stacks per 'a' of length
        rate_b = n1 * b / a + n2          # stacks per 'b' of length
        i0 = math.ceil(S / rate_a)
        j0 = math.ceil(S / rate_b)
        for L in [max(i0 + d, 0) * a for d in (-1, 0, 1, 2)] + [max(j0 + d, 0) * b for d in (-1, 0, 1, 2)]:
            if L > 0 and n1 * int(L // a) + n2 * int(L // b) >= S:
                best = min(best, L)
    return best


# ----------------------------------------------------------------------------- capacity per SKU × container
def capacity(sku, ct, s):
    bd = bundle(sku, s)
    Lu, Wu, Hu = usable(ct, s)
    layers = int(Hu // bd["h"])
    pos, n2, n1 = pattern_positions(Lu, Wu, bd["a"], bd["b"])
    dp = dp_positions(Lu, Wu, bd["a"], bd["b"])
    theo_bundles = pos * layers
    theo_units = theo_bundles * bd["n"]
    eff = v(I.USABLE["efficiency"], s)
    op_bundles = int(math.floor(theo_bundles * eff))
    op_units = op_bundles * bd["n"]
    wt_bundles = int(math.floor(ct["road_kg"] / bd["weight"]))
    wt_units = wt_bundles * bd["n"]
    real_units = min(op_units, wt_units)
    binding = "Volume / geometry" if op_units <= wt_units else "Weight (US road limit)"
    real_bundles = real_units // bd["n"]
    cargo_kg = real_bundles * bd["weight"]
    cube_used = real_bundles * bd["vol"]
    return dict(sku=sku["code"], ctype=ct["key"], Lu=Lu, Wu=Wu, Hu=Hu, layers=layers, positions=pos, n2=n2, n1=n1,
                dp_positions=dp, theo_units=theo_units, op_units=op_units, wt_units=wt_units, real_units=real_units,
                binding=binding, cargo_kg=cargo_kg, cube_util=cube_used / ct["cube"], payload_util=cargo_kg / ct["road_kg"],
                bundle=bd)


# ----------------------------------------------------------------------------- mixed loads
def mixed_load(units_by_sku, ct, s):
    """Zone layout for given units per SKU in ONE container. Returns feasibility details."""
    eff = v(I.USABLE["efficiency"], s)
    rows, tot_len, tot_len_x, tot_kg, tot_vol = [], 0.0, 0.0, 0.0, 0.0
    for sku in I.SKUS:
        u = units_by_sku.get(sku["code"], 0)
        bd = bundle(sku, s)
        Lu, Wu, Hu = usable(ct, s)
        layers = int(Hu // bd["h"])
        nb = math.ceil(u / bd["n"])
        # operational reserve: required bundles are inflated by 1/efficiency before the geometric fit
        stacks = math.ceil(nb / (eff * layers) - 1e-9) if nb else 0
        L, n2, n1 = zone_length(stacks, Wu, bd["a"], bd["b"], Lu)
        Lx = zone_length_excel(stacks, Wu, bd["a"], bd["b"])
        kg = nb * bd["weight"]
        rows.append(dict(sku=sku["code"], units=u, bundles=nb, layers=layers, stacks=stacks, zone_len=L, zone_len_excel=Lx,
                         n2=n2, n1=n1, kg=kg, vol=nb * bd["vol"], a=bd["a"], b=bd["b"]))
        tot_len += L
        tot_len_x += Lx
        tot_kg += kg
        tot_vol += nb * bd["vol"]
    Lu, Wu, Hu = usable(ct, s)
    fits_len = tot_len <= Lu + 1e-9
    fits_kg = tot_kg <= ct["road_kg"]
    return dict(rows=rows, tot_len=tot_len, tot_len_excel=tot_len_x, Lu=Lu, len_limit=Lu, tot_kg=tot_kg,
                road_kg=ct["road_kg"], fits=fits_len and fits_kg, fits_len=fits_len, fits_kg=fits_kg,
                len_util=tot_len / Lu, cube_util=tot_vol / ct["cube"], payload_util=tot_kg / ct["road_kg"])


def best_equal_mix(ct, s):
    """Maximum equal units per SKU (whole bundles) that fit one container."""
    n = v(I.BLANK["per_bundle"], s)
    lo, hi = 0, 4000  # bundles per SKU
    while lo < hi:
        mid = (lo + hi + 1) // 2
        m = mixed_load({k["code"]: mid * n for k in I.SKUS}, ct, s)
        if m["fits"]:
            lo = mid
        else:
            hi = mid - 1
    return lo * n


def container_by_key(key):
    for c in I.CONTAINERS:
        if c["key"] == key:
            return c
    raise KeyError(key)


def config_units(cfg, s):
    """Units per SKU for a configuration under scenario s (index)."""
    if cfg["kind"] == "fixed":
        return dict(cfg["units"])
    ct = container_by_key(cfg["ctype"])
    if cfg["kind"] == "fullmix":
        t = best_equal_mix(ct, s)
        return {k["code"]: t for k in I.SKUS}
    if cfg["kind"] == "fullsku":
        sku = [k for k in I.SKUS if k["code"] == cfg["sku"]][0]
        cap = capacity(sku, ct, s)
        return {k["code"]: (cap["real_units"] if k["code"] == cfg["sku"] else 0) for k in I.SKUS}
    raise ValueError(cfg)


def config_feasibility(cfg, s):
    units = config_units(cfg, s)
    if cfg["ctype"] == "LCL":
        vol = sum(math.ceil(units[k["code"]] / bundle(k, s)["n"]) * bundle(k, s)["vol"] for k in I.SKUS)
        kg = sum(math.ceil(units[k["code"]] / bundle(k, s)["n"]) * bundle(k, s)["weight"] for k in I.SKUS)
        return dict(units=units, fits=True, per_container=None, vol=vol, kg=kg)
    ct = container_by_key(cfg["ctype"])
    per = {k: math.ceil(u / cfg["n"]) for k, u in units.items()}
    m = mixed_load(per, ct, s)
    return dict(units=units, fits=m["fits"], per_container=m, vol=sum(r["vol"] for r in m["rows"]) * cfg["n"],
                kg=m["tot_kg"] * cfg["n"])


# ----------------------------------------------------------------------------- diagrams
COLORS = {"3464": "#2a6f97", "3463": "#c8553d", "3460": "#4f9d69"}


def draw_mixed(units_by_sku, ct, s, title, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    m = mixed_load(units_by_sku, ct, s)
    Lu, Wu, Hu = usable(ct, s)
    fig, ax = plt.subplots(figsize=(12.5, 4.4))
    ax.add_patch(Rectangle((0, 0), ct["L"], ct["W"], fill=False, lw=2, ec="#222"))
    ax.add_patch(Rectangle((0, 0), Lu, Wu, fill=False, lw=1, ls="--", ec="#888"))
    x0 = 0.0
    for r in m["rows"]:
        if r["stacks"] == 0:
            continue
        a, b, n2, n1 = r["a"], r["b"], r["n2"], r["n1"]
        placed = 0
        # rotated rows (long side across the width) first, then normal rows
        y = 0.0
        for _ in range(n2):
            x = x0
            while x + b <= x0 + r["zone_len"] + 1e-6 and placed < r["stacks"]:
                ax.add_patch(Rectangle((x, y), b, a, fc=COLORS[r["sku"]], ec="white", lw=0.8, alpha=0.9))
                placed += 1
                x += b
            y += a
        for _ in range(n1):
            x = x0
            while x + a <= x0 + r["zone_len"] + 1e-6 and placed < r["stacks"]:
                ax.add_patch(Rectangle((x, y), a, b, fc=COLORS[r["sku"]], ec="white", lw=0.8, alpha=0.9))
                placed += 1
                x += a
            y += b
        ax.text(x0 + r["zone_len"] / 2, ct["W"] + 120,
                f"SKU {r['sku']}: {r['units']:,} pcs = {r['bundles']} bundles\n{r['stacks']} stacks × ≤{r['layers']} layers; zone {r['zone_len']/1000:.2f} m",
                ha="center", va="bottom", fontsize=8)
        x0 += r["zone_len"]
    ax.axvline(m["len_limit"], color="#c00", ls=":", lw=1.2)
    ax.text(m["len_limit"], -260, f"usable length (stacks sized with {v(I.USABLE['efficiency'], s):.0%} loading-efficiency reserve)", color="#c00", fontsize=7, ha="right")
    ax.set_xlim(-100, ct["L"] + 100)
    ax.set_ylim(-400, ct["W"] + 900)
    ax.set_aspect("equal")
    ax.set_xlabel("Container length (mm) – door at right")
    ax.set_yticks([0, ct["W"]])
    status = "FITS" if m["fits"] else "DOES NOT FIT"
    ax.set_title(f"{title}\n{ct['name']} | blocks used {m['tot_len']/1000:.2f} m of {Lu/1000:.2f} m usable | "
                 f"{m['tot_kg']:,.0f} kg vs {ct['road_kg']:,} kg road limit | {status} (PROVISIONAL geometry)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return m


if __name__ == "__main__":
    for si, sn in enumerate(I.SCENARIOS):
        print("==", sn)
        for sku in I.SKUS:
            bd = bundle(sku, si)
            print(f" SKU {sku['code']}: blank {bd['blank']['Lb']:.0f}x{bd['blank']['Wb']:.0f} mm, {bd['blank']['weight']*1000:.0f} g; "
                  f"bundle {bd['a']:.0f}x{bd['b']:.0f}x{bd['h']:.0f} mm {bd['weight']:.2f} kg")
            for ct in I.CONTAINERS:
                c = capacity(sku, ct, si)
                print(f"   {ct['key']}: layers {c['layers']} pos {c['positions']} (dp {c['dp_positions']}) theo {c['theo_units']:,} "
                      f"op {c['op_units']:,} wt {c['wt_units']:,} real {c['real_units']:,} [{c['binding']}] cube {c['cube_util']:.0%} payload {c['payload_util']:.0%}")
        for cfg in I.CONFIGS:
            f = config_feasibility(cfg, si)
            pc = f["per_container"]
            extra = f" len {pc['tot_len']:.0f}/{pc['len_limit']:.0f} (xl {pc['tot_len_excel']:.0f}) kg {pc['tot_kg']:.0f}" if pc else f" vol {f['vol']:.1f} m3"
            print(f"  {cfg['key']} {cfg['name'][:45]:45s} units {sum(f['units'].values()):>7,} fits={f['fits']}{extra}")
