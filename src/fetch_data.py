import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

from scraper import scrape_bank

def fetch_peer_rates(bank_name):
    """Fetch deposit product rates by scraping the bank's public rates page."""
    return scrape_bank(bank_name)

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
            name = bank["name"]
            if name not in seen:
                seen[name] = fetch_peer_rates(name)
            bank_copy = dict(bank)
            bank_copy["rates"] = seen[name]
            enriched.append(bank_copy)
        peer_groups[gk]["peers_with_rates"] = enriched

    return peer_groups
