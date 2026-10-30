import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

FDIC_BASE = "https://banks.data.fdic.gov/api"

FDIC_RATE_MAP = {
    "REPDTE":      None,
    "CERT":        None,
    "STALP":       None,
    "INTEXPY":     "checking_apy",
    "INTDEPRTD":   "savings",
    "INTDEPRTM":   "mma",
    "INTDEPRT3":   "cd_3mo",
    "INTDEPRT6":   "cd_6mo",
    "INTDEPRT1":   "cd_12mo",
    "INTDEPRT2":   "cd_24mo",
}

def _fdic_get(endpoint, params):
    url = f"{FDIC_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception:
        return None

def fetch_peer_rates(fdic_cert):
    params = {
        "filters": f"CERT:{fdic_cert}",
        "fields": "CERT,REPDTE,INTEXPY,INTDEPRTD,INTDEPRTM,INTDEPRT3,INTDEPRT6,INTDEPRT1,INTDEPRT2",
        "sort_by": "REPDTE",
        "sort_order": "DESC",
        "limit": 1,
        "output": "json"
    }
    data = _fdic_get("financials", params)
    if not data or not data.get("data"):
        return {}
    row = data["data"][0].get("data", {})
    rates = {}
    for fdic_key, prod_key in FDIC_RATE_MAP.items():
        if prod_key and fdic_key in row and row[fdic_key] is not None:
            val = row[fdic_key]
            try:
                rates[prod_key] = float(val)
            except (TypeError, ValueError):
                rates[prod_key] = None
    return rates

def fetch_fred_data(fred_api_key):
    series = {
        "FEDFUNDS": None,
        "MMNRNNS":  None,
        "CD3NAX":   None,
        "CD6NAX":   None,
        "CD1NAX":   None,
    }
    for sid in list(series.keys()):
        params = {
            "series_id": sid,
            "api_key": fred_api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
            "observation_start": "2020-01-01",
        }
        url = f"https://api.stlouisfed.org/fred/series/observations?{urllib.parse.urlencode(params)}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read())
            obs = body.get("observations", [])
            if obs:
                val = obs[0].get("value", ".")
                series[sid] = float(val) if val != "." else None
        except Exception:
            series[sid] = None
    return series

def fetch_all_peer_rates(config):
    peer_groups = config["peer_groups"]
    seen = {}

    for gk, grp in peer_groups.items():
        enriched = []
        for bank in grp["banks"]:
            cert = str(bank["fdic_cert"])
            if cert not in seen:
                seen[cert] = fetch_peer_rates(cert)
            bank_copy = dict(bank)
            bank_copy["rates"] = seen[cert]
            enriched.append(bank_copy)
        peer_groups[gk]["peers_with_rates"] = enriched

    return peer_groups
