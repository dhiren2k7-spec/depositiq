"""
Fetches Popular Direct CD rates from cdvalet.com structured JSON embedded in HTML.
Falls back to config/banks.json values if fetch or parse fails.
"""

import re
import json
import urllib.request

CDVALET_URL = "https://www.cdvalet.com/bankDetails/Popular-Direct/0000000007f35c8635b9c077"

MONTH_TO_KEY = {
    3: "cd_3mo", 6: "cd_6mo", 9: "cd_9mo",
    12: "cd_12mo", 18: "cd_18mo", 24: "cd_24mo",
    36: "cd_36mo", 48: "cd_48mo", 60: "cd_60mo",
}


def fetch_popular_direct_rates(fallback_rates: dict) -> dict:
    rates = dict(fallback_rates)
    try:
        req = urllib.request.Request(
            CDVALET_URL,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DepositIQ/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        fetched = _parse(html)
        if fetched:
            rates.update(fetched)
            print(f"  [Popular Direct] Live rates fetched from cdvalet.com: {fetched}")
        else:
            print("  [Popular Direct] Parse returned no rates — using config fallback")

    except Exception as e:
        print(f"  [Popular Direct] Fetch failed ({e}) — using config fallback")

    return rates


def _parse(html: str) -> dict:
    result = {}

    # Primary: JSON structured data — apyPercent + termMonths pairs
    apy_hits = re.findall(r'"apyPercent","value":"([\d.]+)%"', html)
    term_hits = re.findall(r'"termMonths","value":"(\d+)"', html)

    if apy_hits and term_hits and len(apy_hits) == len(term_hits):
        for apy_str, term_str in zip(apy_hits, term_hits):
            months = int(term_str)
            apy = round(float(apy_str), 2)
            key = MONTH_TO_KEY.get(months)
            if key and 0.5 <= apy <= 10.0:
                result[key] = apy
        return result

    # Fallback: scan for term+APY pairs in plain text
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).lower()
    for months, key in MONTH_TO_KEY.items():
        pattern = rf"{months}\s*(?:month|mo)\b.{{0,80}}?(\d+\.\d+)\s*%"
        m = re.search(pattern, text)
        if m:
            apy = round(float(m.group(1)), 2)
            if 0.5 <= apy <= 10.0:
                result[key] = apy

    return result
