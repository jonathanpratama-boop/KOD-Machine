"""HERMES_NOV3_REPRO_v1 data fetch (public Binance archive data.binance.vision, the same source Hermes used).

Spot 1h monthly klines 2020-01..2026-10 and spot 1d monthly klines 2017-08..2026-10 for the union of Hermes's two
universes (hermes_universe_2020_22.json usdt_universe, hermes_universe_2023_26.json universe), plus USD-M futures monthly
funding-rate files for every listed futures symbol. Lists the S3 bucket per symbol first so only existing files are
requested. Resumable: raw/<kind>/<file>.zip are kept (gitignored); fetch_manifest.json records sha256 per file."""
import concurrent.futures as cf, hashlib, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DL = "https://data.binance.vision/"
LIST_FAIL = []


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 * (k + 1))
        except Exception:
            time.sleep(2 * (k + 1))
    raise RuntimeError("failed " + url)


def list_keys(prefix, delimiter=False):
    keys, prefixes, marker = [], [], ""
    while True:
        u = f"{S3}?prefix={urllib.parse.quote(prefix, safe='/')}" + ("&delimiter=/" if delimiter else "") + (f"&marker={urllib.parse.quote(marker, safe='/')}" if marker else "")
        try:
            x = get(u).decode()
        except RuntimeError:
            print("LIST FAILED", prefix, flush=True); LIST_FAIL.append(prefix); break
        keys += re.findall(r"<Key>([^<]+\.zip)</Key>", x)
        prefixes += re.findall(r"<Prefix>([^<]+/)</Prefix>", x)[1:] if delimiter else []
        if "<IsTruncated>true" not in x:
            break
        m = re.search(r"<NextMarker>(.*?)</NextMarker>", x)
        marker = m.group(1) if m else (keys[-1] if keys else prefixes[-1])
    return keys, prefixes


u1 = json.load(open(HERE / "hermes_universe_2020_22.json"))["usdt_universe"]
u2 = json.load(open(HERE / "hermes_universe_2023_26.json"))["universe"]
syms = sorted(set(u1) | set(u2))


def want(key, kind):
    ym = re.search(r"-(\d{4})-(\d{2})\.zip$", key)
    if not ym:
        return False
    ym = ym.group(1) + "-" + ym.group(2)
    return {"k1h": "2020-01" <= ym <= "2026-10", "k1d": "2017-08" <= ym <= "2026-10", "fund": ym <= "2026-10"}[kind]


jobs = []
with cf.ThreadPoolExecutor(16) as ex:
    for kind, iv in (("k1h", "1h"), ("k1d", "1d")):
        for keys, _ in ex.map(lambda s: list_keys(f"data/spot/monthly/klines/{s}/{iv}/"), syms):
            jobs += [(kind, k) for k in keys if want(k, kind)]
    _, fsyms = list_keys("data/futures/um/monthly/fundingRate/", delimiter=True)
    fsyms = [p.rstrip("/").split("/")[-1] for p in fsyms]
    for keys, _ in ex.map(lambda s: list_keys(f"data/futures/um/monthly/fundingRate/{s}/"), fsyms):
        jobs += [("fund", k) for k in keys if want(k, "fund")]
print("symbols", len(syms), "futures symbols", len(fsyms), "files", len(jobs), flush=True)


def one(job):
    kind, key = job
    d = RAW / kind; d.mkdir(parents=True, exist_ok=True)
    f = d / key.split("/")[-1]
    if not f.exists():
        b = get(DL + urllib.parse.quote(key, safe="/"))
        if b is None:
            return kind, key, None, "404"
        tmp = f.with_suffix(".part"); tmp.write_bytes(b); tmp.rename(f)
    return kind, key, hashlib.sha256(f.read_bytes()).hexdigest(), "ok"


man, stat = {"symbols": syms, "futures_symbols": fsyms, "files": {}}, {}
with cf.ThreadPoolExecutor(24) as ex:
    for n, (kind, key, h, s) in enumerate(ex.map(one, jobs), 1):
        stat[s] = stat.get(s, 0) + 1
        if h:
            man["files"][key] = h
        if n % 5000 == 0:
            print(n, len(jobs), stat, flush=True)
man["status"] = stat; man["list_failures"] = LIST_FAIL
(HERE / "fetch_manifest.json").write_text(json.dumps(man) + "\n")
print("done", stat, flush=True)
