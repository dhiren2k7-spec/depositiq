import json
import os
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime

PEER_RATES_PATH = os.path.join(os.path.dirname(__file__), "../config/peer_rates.json")

# ── Curinos live feed (Option B) ─────────────────────────────────────────────
# If all four OneDrive secrets are present, use the live Curinos Excel.
# Otherwise fall back to the static config/peer_rates.json.
_CURINOS_SECRETS = (
    "ONEDRIVE_CLIENT_ID",
    "ONEDRIVE_CLIENT_SECRET",
    "ONEDRIVE_TENANT_ID",
    "ONEDRIVE_FILE_PATH",
)

def _curinos_enabled():
    return all(os.environ.get(s) for s in _CURINOS_SECRETS)

def _load_curinos_rates():
    """Attempt to download and parse Curinos Excel from OneDrive."""
    from fetch_curinos import fetch_curinos_rates
    return fetch_curinos_rates()

def _load_static_peer_rates():
    try:
        with open(PEER_RATES_PATH) as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if not k.startswith("_")}
    except Exception:
        return {}

def _load_peer_rates():
    """
    Returns peer_rates dict keyed by group name.
    Curinos Excel takes priority when secrets are available.
    Falls back to static config/peer_rates.json.
    """
    if _curinos_enabled():
        try:
            result = _load_curinos_rates()
            if result:
                print("  [DATA] Peer rates sourced from Curinos (live)")
                return result
        except Exception as e:
            print(f"  [WARN] Curinos feed failed ({e}), using static peer_rates.json")
    else:
        print("  [DATA] Peer rates sourced from static config/peer_rates.json")
    return _load_static_peer_rates()

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

    # Try Curinos live; fall back to static
    curinos_data = _load_peer_rates()

    for gk, grp in peer_groups.items():
        enriched = []
        for bank in grp["banks"]:
            name = bank["name"]
            bank_copy = dict(bank)

            # Curinos returns {group: {label, banks: [{name, rates}]}}
            # Static returns {group: {label, description, banks: [{name, rates}]}}
            # Both have .get(gk, {}).get("banks", [])
            grp_data = curinos_data.get(gk, {})
            banks_list = grp_data.get("banks", []) if isinstance(grp_data, dict) else []

            # Match by name (exact or fuzzy)
            matched_rates = {}
            for b in banks_list:
                bname = b.get("name", "")
                if bname == name or bname.lower() in name.lower() or name.lower() in bname.lower():
                    matched_rates = b.get("rates", {})
                    break

            # Static fallback key is just bank name
            if not matched_rates and name in curinos_data:
                matched_rates = curinos_data[name]

            bank_copy["rates"] = matched_rates
            enriched.append(bank_copy)
        peer_groups[gk]["peers_with_rates"] = enriched

    return peer_groups
