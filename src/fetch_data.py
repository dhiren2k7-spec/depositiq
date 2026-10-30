import json
import os
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

PEER_RATES_PATH = os.path.join(os.path.dirname(__file__), "../config/peer_rates.json")

def _load_peer_rates():
    try:
        with open(PEER_RATES_PATH) as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}

def fetch_peer_rates(bank_name):
    rates = _load_peer_rates()
    return rates.get(bank_name, {})

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
    peer_rates = _load_peer_rates()

    for gk, grp in peer_groups.items():
        enriched = []
        for bank in grp["banks"]:
            name = bank["name"]
            bank_copy = dict(bank)
            bank_copy["rates"] = peer_rates.get(name, {})
            enriched.append(bank_copy)
        peer_groups[gk]["peers_with_rates"] = enriched

    return peer_groups
