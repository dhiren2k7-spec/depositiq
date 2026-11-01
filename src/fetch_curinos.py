"""
fetch_curinos.py
Downloads the CurinosConnect Excel from OneDrive via Microsoft Graph API
and parses it into the peer_rates structure used by fetch_data.py.

Required GitHub Secrets:
  ONEDRIVE_CLIENT_ID      — Azure AD app client ID
  ONEDRIVE_CLIENT_SECRET  — Azure AD app client secret
  ONEDRIVE_TENANT_ID      — Azure AD tenant ID
  ONEDRIVE_FILE_PATH      — OneDrive path to the Curinos Excel file
                            e.g. /DepositIQ/curinos_peer_rates.xlsx
"""

import os
import json
import urllib.request
import urllib.parse
import tempfile
from datetime import datetime

# ── Column name mappings from CurinosConnect Excel → our internal keys
# EDIT THESE to match the actual column headers in your CurinosConnect export.
# Run `python src/fetch_curinos.py --inspect` after first download to see headers.
COLUMN_MAP = {
    "Institution Name":   "name",
    "Bank Name":          "name",          # alternate header
    "Checking APY":       "checking_apy",
    "Checking":           "checking_apy",
    "Savings APY":        "savings",
    "Savings Rate":       "savings",
    "MMA APY":            "mma",
    "Money Market APY":   "mma",
    "Money Market":       "mma",
    "3 Month CD":         "cd_3mo",
    "3-Month CD APY":     "cd_3mo",
    "CD 3 Month":         "cd_3mo",
    "6 Month CD":         "cd_6mo",
    "6-Month CD APY":     "cd_6mo",
    "CD 6 Month":         "cd_6mo",
    "12 Month CD":        "cd_12mo",
    "12-Month CD APY":    "cd_12mo",
    "CD 12 Month":        "cd_12mo",
    "1 Year CD":          "cd_12mo",
    "24 Month CD":        "cd_24mo",
    "24-Month CD APY":    "cd_24mo",
    "CD 24 Month":        "cd_24mo",
    "2 Year CD":          "cd_24mo",
    "9 Month CD":         "cd_9mo",
    "9-Month CD APY":     "cd_9mo",
    "CD 9 Month":         "cd_9mo",
    "18 Month CD":        "cd_18mo",
    "18-Month CD APY":    "cd_18mo",
    "CD 18 Month":        "cd_18mo",
    "36 Month CD":        "cd_36mo",
    "36-Month CD APY":    "cd_36mo",
    "CD 36 Month":        "cd_36mo",
    "3 Year CD":          "cd_36mo",
    "48 Month CD":        "cd_48mo",
    "48-Month CD APY":    "cd_48mo",
    "CD 48 Month":        "cd_48mo",
    "4 Year CD":          "cd_48mo",
    "60 Month CD":        "cd_60mo",
    "60-Month CD APY":    "cd_60mo",
    "CD 60 Month":        "cd_60mo",
    "5 Year CD":          "cd_60mo",
}

# Peer group assignment — map institution names to peer group keys
# Add/edit as needed based on what Curinos returns
PEER_GROUP_MAP = {
    # NY Metro
    "Berkshire Bank":        "ny_metro",
    "Cathay Bank":           "ny_metro",
    "ConnectOne Bank":       "ny_metro",
    "Dime Community Bank":   "ny_metro",
    "Flushing Bank":         "ny_metro",
    "OceanFirst Bank":       "ny_metro",
    "Provident Bank":        "ny_metro",
    "JPMorgan Chase":        "ny_metro",
    "JP Morgan Chase":       "ny_metro",
    "Flagstar Bank":         "ny_metro",
    "PNC Bank":              "ny_metro",
    # South Florida
    "Amerant Bank":          "south_florida",
    "BankUnited":            "south_florida",
    "Ocean Bank":            "south_florida",
    "Seacoast Bank":         "south_florida",
    "Seacoast National Bank":"south_florida",
    "ServisFirst Bank":      "south_florida",
    "Wells Fargo":           "south_florida",
    "Truist":                "south_florida",
    # Direct / Online
    "Ally Bank":             "direct_online",
    "Marcus":                "direct_online",
    "Marcus by Goldman Sachs":"direct_online",
    "Discover Bank":         "direct_online",
    "American Express":      "direct_online",
    "Synchrony Bank":        "direct_online",
    "Barclays":              "direct_online",
    "Capital One":           "direct_online",
    "Bread Financial":       "direct_online",
}

PEER_GROUP_LABELS = {
    "ny_metro":      "New York Metro Peers",
    "south_florida": "South Florida Peers",
    "direct_online": "Direct / Online Banks",
}


def _get_onedrive_token():
    tenant_id = os.environ["ONEDRIVE_TENANT_ID"]
    client_id = os.environ["ONEDRIVE_CLIENT_ID"]
    client_secret = os.environ["ONEDRIVE_CLIENT_SECRET"]

    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    body = urllib.parse.urlencode({
        "grant_type":    "client_credentials",
        "client_id":     client_id,
        "client_secret": client_secret,
        "scope":         "https://graph.microsoft.com/.default"
    }).encode()

    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def _download_from_onedrive(token, file_path, dest_path):
    """Download file from OneDrive using Microsoft Graph API."""
    # file_path is like /DepositIQ/curinos_peer_rates.xlsx
    encoded = urllib.parse.quote(file_path)
    url = f"https://graph.microsoft.com/v1.0/me/drive/root:{encoded}:/content"

    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        with open(dest_path, "wb") as f:
            f.write(resp.read())
    print(f"  Downloaded Curinos Excel → {dest_path}")


def _parse_curinos_excel(xlsx_path, inspect=False):
    """
    Parse CurinosConnect Excel into peer_rates dict.
    Returns dict keyed by peer group with list of bank rate dicts.
    """
    try:
        import openpyxl
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "-q"])
        import openpyxl

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)

    # Try to find the right sheet — Curinos often names it "Data" or "Rates"
    sheet = None
    for candidate in ["Data", "Rates", "Peer Rates", "Rate Data", wb.sheetnames[0]]:
        if candidate in wb.sheetnames:
            sheet = wb[candidate]
            break

    if inspect:
        print(f"\nSheets: {wb.sheetnames}")
        print(f"Using sheet: {sheet.title}")
        headers = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
        print(f"Headers: {headers}")
        print("\nFirst 3 rows:")
        for i, row in enumerate(sheet.iter_rows(min_row=2, max_row=4, values_only=True)):
            print(f"  Row {i+2}: {row}")
        return None

    # Read headers
    headers = [str(cell.value).strip() if cell.value else ""
               for cell in next(sheet.iter_rows(min_row=1, max_row=1))]

    # Map column indices
    col_idx = {}
    name_col = None
    for i, h in enumerate(headers):
        mapped = COLUMN_MAP.get(h)
        if mapped == "name":
            name_col = i
        elif mapped:
            col_idx[mapped] = i

    if name_col is None:
        raise ValueError(f"Could not find institution name column. Headers: {headers}")

    # Build peer_rates structure
    peer_rates = {
        "ny_metro":      {"label": PEER_GROUP_LABELS["ny_metro"],      "banks": []},
        "south_florida": {"label": PEER_GROUP_LABELS["south_florida"],  "banks": []},
        "direct_online": {"label": PEER_GROUP_LABELS["direct_online"],  "banks": []},
    }

    products = ["checking_apy", "savings", "mma", "cd_3mo", "cd_6mo", "cd_9mo", "cd_12mo", "cd_18mo", "cd_24mo", "cd_36mo", "cd_48mo", "cd_60mo"]

    for row in sheet.iter_rows(min_row=2, values_only=True):
        bank_name = str(row[name_col]).strip() if row[name_col] else ""
        if not bank_name or bank_name == "None":
            continue

        group = PEER_GROUP_MAP.get(bank_name)
        if not group:
            # fuzzy match — check if any key is a substring
            for key, grp in PEER_GROUP_MAP.items():
                if key.lower() in bank_name.lower() or bank_name.lower() in key.lower():
                    group = grp
                    break

        if not group:
            print(f"  [WARN] Unrecognized bank '{bank_name}' — skipping")
            continue

        rates = {}
        for prod in products:
            idx = col_idx.get(prod)
            if idx is not None and idx < len(row):
                val = row[idx]
                if val is not None:
                    try:
                        # Curinos may deliver as percent (4.05) or decimal (0.0405)
                        v = float(val)
                        if v > 1:  # already in percent form
                            rates[prod] = round(v, 4)
                        else:      # decimal — convert to percent
                            rates[prod] = round(v * 100, 4)
                    except (TypeError, ValueError):
                        rates[prod] = None
                else:
                    rates[prod] = None
            else:
                rates[prod] = None

        peer_rates[group]["banks"].append({
            "name": bank_name,
            "rates": rates
        })

    total = sum(len(v["banks"]) for v in peer_rates.values())
    print(f"  Parsed {total} peer banks from Curinos Excel")
    return peer_rates


def fetch_curinos_rates(inspect=False):
    """
    Main entry point. Downloads Curinos Excel from OneDrive,
    parses it, returns peer_rates dict.
    Falls back to static config/peer_rates.json if any step fails.
    """
    file_path = os.environ.get("ONEDRIVE_FILE_PATH", "/DepositIQ/curinos_peer_rates.xlsx")

    try:
        print("  Fetching Curinos rates from OneDrive...")
        token = _get_onedrive_token()
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
        _download_from_onedrive(token, file_path, tmp_path)
        peer_rates = _parse_curinos_excel(tmp_path, inspect=inspect)
        print("  ✓ Curinos rates loaded from OneDrive")
        return peer_rates

    except Exception as e:
        print(f"  [WARN] Curinos OneDrive fetch failed ({e}), falling back to static peer_rates.json")
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base, "config", "peer_rates.json")) as f:
            data = json.load(f)
        # Strip _meta block
        return {k: v for k, v in data.items() if not k.startswith("_")}


if __name__ == "__main__":
    import sys
    inspect = "--inspect" in sys.argv
    if inspect:
        print("INSPECT MODE — showing Excel structure only\n")
    result = fetch_curinos_rates(inspect=inspect)
    if result and not inspect:
        for grp, data in result.items():
            print(f"\n{data['label']}: {len(data['banks'])} banks")
