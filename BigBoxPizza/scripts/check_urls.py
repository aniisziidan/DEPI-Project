"""One-shot reachability check of every source URL in sources_data.py (brief §21: "confirm that source URLs work
where accessible").

    python3 BigBoxPizza/scripts/check_urls.py      → outputs/url_check.json (read by qa_checklist.py)

Each distinct URL is requested once (GET, first bytes only) through the session's HTTPS proxy. Hosts the egress
policy already denied in this session are not retried; a 403 on the proxy CONNECT is recorded as a policy block,
not as a dead link. Local evidence paths are checked on disk. Network-dependent, so it is not part of build_all.py.
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
REPO = os.path.dirname(PROJ)
sys.path.insert(0, HERE)

import sources_data as SD  # noqa: E402

# Hosts denied by the egress policy earlier in this session (proxy status, 2026-10-15). Not retried.
DENIED = {"hts.usitc.gov", "www.ecfr.gov", "ecfr.gov", "www.federalregister.gov", "federalregister.gov", "api.census.gov",
          "www.cbp.gov", "cbp.gov", "rulings.cbp.gov", "www.cbe.org.eg", "cbe.org.eg", "nilecarton.com", "www.nilecarton.com"}
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def split_urls(field):
    return [p.strip() for p in field.split(";")] if ";" in field else [field.strip()]


def _ctx():
    ca = "/root/.ccr/ca-bundle.crt"
    return ssl.create_default_context(cafile=ca) if os.path.exists(ca) else ssl.create_default_context()


def probe(url, ctx):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
            r.read(512)
            return dict(result="reachable", code=r.status, final_url=r.geturl())
    except urllib.error.HTTPError as e:
        return dict(result="http_error", code=e.code, detail=str(e.reason)[:120])
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "Tunnel connection failed: 403" in reason or "Tunnel connection failed: 407" in reason:
            return dict(result="blocked_by_policy", code=None, detail=reason[:120])
        return dict(result="network_error", code=None, detail=reason[:160])
    except Exception as e:  # noqa: BLE001 – record any failure, never crash the check
        return dict(result="network_error", code=None, detail=f"{type(e).__name__}: {e}"[:160])


def main(out=None):
    out = out or os.path.join(PROJ, "outputs", "url_check.json")
    ctx = _ctx()
    jobs, rows = {}, []
    for s in SD.SOURCES:
        for u in split_urls(s["url"]):
            if u.startswith("http"):
                host = (urlparse(u).hostname or "").lower()
                if host in DENIED:
                    rows.append(dict(id=s["id"], url=u, host=host, result="blocked_by_policy", code=None,
                                     detail="Host denied by egress policy earlier in this session; not retried"))
                else:
                    jobs.setdefault(u, []).append(s["id"])
            else:
                path = u.split(" (")[0]
                ok = os.path.exists(os.path.join(REPO, path))
                rows.append(dict(id=s["id"], url=u, host="(local file)", result="local_file_ok" if ok else "local_file_missing", code=None))
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(probe, u, ctx): u for u in jobs}
        for f in cf.as_completed(futs):
            u = futs[f]
            r = f.result()
            for sid in jobs[u]:
                rows.append(dict(id=sid, url=u, host=(urlparse(u).hostname or "").lower(), **r))
    rows.sort(key=lambda x: (x["id"], x["url"]))
    res = dict(checked_at=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), rows=rows)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    summary = {}
    for r in rows:
        summary[r["result"]] = summary.get(r["result"], 0) + 1
    print(out, summary)
    return res


if __name__ == "__main__":
    main()
