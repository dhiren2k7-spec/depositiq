"""
scraper.py — Web scrapers for peer bank deposit rates.
stdlib only: urllib.request + html.parser. No pip deps.
Returns dict with keys: checking_apy, savings, mma, cd_3mo, cd_6mo, cd_12mo, cd_24mo
Missing products → key absent from dict.
"""

import re
import json
import urllib.request
import urllib.error
from html.parser import HTMLParser

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
TIMEOUT = 20


def _get(url, extra_headers=None):
    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
            enc = r.headers.get_content_charset("utf-8") or "utf-8"
            return raw.decode(enc, errors="replace")
    except Exception:
        return ""


def _get_json(url, extra_headers=None):
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read())
    except Exception:
        return None


def _pct(s):
    """Parse '4.50%' or '4.50' → float or None."""
    if s is None:
        return None
    s = str(s).strip().replace("%", "").replace(",", "")
    try:
        v = float(s)
        return v if 0 < v < 20 else None
    except (ValueError, TypeError):
        return None


def _find_apy(text, label_pattern, window=200):
    """Find APY value near a label pattern in raw HTML/text."""
    m = re.search(label_pattern, text, re.IGNORECASE)
    if not m:
        return None
    chunk = text[m.start():m.start() + window]
    hits = re.findall(r'(\d+\.\d+)\s*%', chunk)
    if hits:
        return _pct(hits[0])
    return None


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def get_text(self):
        return " ".join(self.parts)


def _html_text(html):
    p = _TextExtractor()
    p.feed(html)
    return p.get_text()


# ── DIRECT/ONLINE BANKS ────────────────────────────────────────────────────

def scrape_ally():
    """Ally Bank — savings, MMA, CDs via JSON API."""
    rates = {}
    # Ally publishes rates as JSON on their rates page
    html = _get("https://www.ally.com/bank/online-savings-account/")
    txt = _html_text(html)
    v = _find_apy(txt, r'(high\s+yield\s+savings|online\s+savings)', 300)
    if v:
        rates["savings"] = v

    html = _get("https://www.ally.com/bank/money-market-account/")
    txt = _html_text(html)
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.ally.com/bank/cd/")
    txt = _html_text(html)
    for pattern, key in [
        (r'3.month|3-month', "cd_3mo"),
        (r'6.month|6-month', "cd_6mo"),
        (r'12.month|1.year|12-month', "cd_12mo"),
        (r'18.month|18-month', "cd_18mo"),
    ]:
        v = _find_apy(txt, pattern, 300)
        if v and key not in rates:
            rates[key] = v

    # Try 24-month
    v = _find_apy(txt, r'24.month|2.year', 300)
    if v:
        rates["cd_24mo"] = v

    return rates


def scrape_marcus():
    """Marcus by Goldman Sachs."""
    rates = {}
    html = _get("https://www.marcus.com/us/en/savings/high-yield-online-savings-account")
    txt = _html_text(html)
    v = _find_apy(txt, r'(annual\s+percentage\s+yield|apy|high.yield)', 400)
    if v:
        rates["savings"] = v

    html = _get("https://www.marcus.com/us/en/savings/certificates-of-deposit")
    txt = _html_text(html)
    for pat, key in [
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'18.month', "cd_18mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_discover():
    """Discover Bank."""
    rates = {}
    html = _get("https://www.discover.com/online-banking/savings-account/")
    txt = _html_text(html)
    v = _find_apy(txt, r'(online\s+savings|high.yield|annual\s+percentage)', 400)
    if v:
        rates["savings"] = v

    html = _get("https://www.discover.com/online-banking/money-market/")
    txt = _html_text(html)
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.discover.com/online-banking/cd/rates/")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_amex():
    """American Express National Bank."""
    rates = {}
    html = _get("https://www.americanexpress.com/en-us/banking/savings/")
    txt = _html_text(html)
    v = _find_apy(txt, r'(high.yield|savings\s+account|apy)', 400)
    if v:
        rates["savings"] = v

    html = _get("https://www.americanexpress.com/en-us/banking/high-yield-savings/")
    txt2 = _html_text(html)
    v2 = _find_apy(txt2, r'(high.yield|apy)', 400)
    if v2 and not rates.get("savings"):
        rates["savings"] = v2

    html = _get("https://www.americanexpress.com/en-us/banking/cd/")
    txt = _html_text(html)
    for pat, key in [
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_synchrony():
    """Synchrony Bank."""
    rates = {}
    html = _get("https://www.synchronybank.com/banking/high-yield-savings/")
    txt = _html_text(html)
    v = _find_apy(txt, r'(savings|apy|annual)', 400)
    if v:
        rates["savings"] = v

    html = _get("https://www.synchronybank.com/banking/money-market-account/")
    txt = _html_text(html)
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.synchronybank.com/banking/cd/")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_barclays():
    """Barclays Bank Delaware."""
    rates = {}
    html = _get("https://www.banking.barclaysus.com/high-yield-savings.html")
    txt = _html_text(html)
    v = _find_apy(txt, r'(savings|apy)', 400)
    if v:
        rates["savings"] = v

    html = _get("https://www.banking.barclaysus.com/online-savings.html")
    txt2 = _html_text(html)
    v2 = _find_apy(txt2, r'(savings|apy)', 300)
    if v2 and not rates.get("savings"):
        rates["savings"] = v2

    html = _get("https://www.banking.barclaysus.com/tiered-savings.html")
    txt = _html_text(html)
    v = _find_apy(txt, r'(tiered|money\s+market)', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.banking.barclaysus.com/online-cd.html")
    txt = _html_text(html)
    for pat, key in [
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_capital_one():
    """Capital One 360."""
    rates = {}
    html = _get("https://www.capitalone.com/bank/savings-accounts/online-savings-account/")
    txt = _html_text(html)
    v = _find_apy(txt, r'(360\s+performance\s+savings|savings|apy)', 400)
    if v:
        rates["savings"] = v

    html = _get("https://www.capitalone.com/bank/savings-accounts/money-market/")
    txt = _html_text(html)
    v = _find_apy(txt, r'(money\s+market|360\s+money)', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.capitalone.com/bank/cds/online-cd-accounts/")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_bread():
    """Bread Financial (formerly Comenity)."""
    rates = {}
    html = _get("https://www.breadfinancial.com/en/we-offer/banking.html")
    txt = _html_text(html)
    v = _find_apy(txt, r'(high.yield\s+savings|savings|apy)', 400)
    if v:
        rates["savings"] = v

    html = _get("https://www.breadfinancial.com/en/we-offer/banking/high-yield-savings-account.html")
    txt2 = _html_text(html)
    v2 = _find_apy(txt2, r'(savings|apy)', 300)
    if v2 and not rates.get("savings"):
        rates["savings"] = v2

    html = _get("https://www.breadfinancial.com/en/we-offer/banking/cds.html")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


# ── LARGE NATIONAL BANKS ────────────────────────────────────────────────────

def scrape_jpmorgan():
    """JP Morgan Chase."""
    rates = {}
    html = _get("https://www.chase.com/personal/savings/compare-savings-accounts")
    txt = _html_text(html)
    v = _find_apy(txt, r'(savings|apy|annual)', 400)
    if v:
        rates["savings"] = v

    html = _get("https://www.chase.com/personal/savings/cd-account-rates")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month|90.day', "cd_3mo"),
        (r'6.month|180.day', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v

    html = _get("https://www.chase.com/personal/banking/chase-total-checking")
    txt = _html_text(html)
    v = _find_apy(txt, r'(checking|apy)', 200)
    if v:
        rates["checking_apy"] = v

    return rates


def scrape_wells_fargo():
    """Wells Fargo."""
    rates = {}
    html = _get("https://www.wellsfargo.com/savings-cds/rates/")
    txt = _html_text(html)

    v = _find_apy(txt, r'(way2save|savings\s+account)', 400)
    if v:
        rates["savings"] = v

    v = _find_apy(txt, r'(platinum\s+savings|money\s+market)', 300)
    if v:
        rates["mma"] = v

    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_truist():
    """Truist Bank."""
    rates = {}
    html = _get("https://www.truist.com/personal-banking/savings-accounts")
    txt = _html_text(html)
    v = _find_apy(txt, r'(one\s+savings|savings|apy)', 400)
    if v:
        rates["savings"] = v

    html = _get("https://www.truist.com/personal-banking/cds-iras/cd-rates")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_pnc():
    """PNC Bank."""
    rates = {}
    html = _get("https://www.pnc.com/en/personal-banking/banking/savings-and-money-market.html")
    txt = _html_text(html)
    v = _find_apy(txt, r'(savings|apy)', 400)
    if v:
        rates["savings"] = v

    v = _find_apy(txt, r'(money\s+market|premium\s+money)', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.pnc.com/en/personal-banking/banking/savings-and-money-market/cd-rates.html")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_flagstar():
    """Flagstar Bank."""
    rates = {}
    html = _get("https://www.flagstar.com/personal/savings.html")
    txt = _html_text(html)
    v = _find_apy(txt, r'(savings|apy)', 400)
    if v:
        rates["savings"] = v

    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.flagstar.com/personal/savings/certificate-of-deposit.html")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month|91.day', "cd_3mo"),
        (r'6.month|182.day', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


# ── NY METRO REGIONAL BANKS ─────────────────────────────────────────────────

def scrape_berkshire():
    """Berkshire Bank."""
    rates = {}
    html = _get("https://www.berkshirebank.com/personal/deposit-accounts/savings")
    txt = _html_text(html)
    v = _find_apy(txt, r'(savings|apy)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.berkshirebank.com/personal/deposit-accounts/cds")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_cathay():
    """Cathay Bank."""
    rates = {}
    html = _get("https://www.cathaybank.com/personal-banking/deposit-accounts/savings-accounts")
    txt = _html_text(html)
    v = _find_apy(txt, r'(savings|apy)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.cathaybank.com/personal-banking/deposit-accounts/certificates-of-deposit")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month|90.day', "cd_3mo"),
        (r'6.month|180.day', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_connectone():
    """ConnectOne Bank."""
    rates = {}
    html = _get("https://www.connectonebank.com/personal/deposit-accounts/savings")
    txt = _html_text(html)
    v = _find_apy(txt, r'(savings|apy)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.connectonebank.com/personal/deposit-accounts/certificates-of-deposit")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_dime():
    """Dime Community Bank."""
    rates = {}
    html = _get("https://www.dime.com/personal/savings")
    txt = _html_text(html)
    v = _find_apy(txt, r'(savings|apy)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v

    html = _get("https://www.dime.com/personal/cds")
    txt = _html_text(html)
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_flushing():
    """Flushing Bank."""
    rates = {}
    html = _get("https://www.flushingbank.com/rates")
    txt = _html_text(html)

    v = _find_apy(txt, r'(savings|statement\s+savings)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v
    for pat, key in [
        (r'3.month|91.day', "cd_3mo"),
        (r'6.month|182.day', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_oceanfirst():
    """OceanFirst Bank."""
    rates = {}
    html = _get("https://www.oceanfirstbank.com/rates/")
    txt = _html_text(html)

    v = _find_apy(txt, r'(savings|statement\s+savings)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_provident():
    """Provident Bank (NJ)."""
    rates = {}
    html = _get("https://www.provident.bank/rates")
    txt = _html_text(html)

    v = _find_apy(txt, r'(savings|statement\s+savings|regular\s+savings)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v
    for pat, key in [
        (r'3.month|91.day', "cd_3mo"),
        (r'6.month|182.day', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


# ── SOUTH FLORIDA REGIONAL BANKS ────────────────────────────────────────────

def scrape_amerant():
    """Amerant Bank."""
    rates = {}
    html = _get("https://www.amerantbank.com/personal/rates")
    if not html:
        html = _get("https://www.amerantbank.com/personal/savings")
    txt = _html_text(html)

    v = _find_apy(txt, r'(savings|statement\s+savings)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_bankunited():
    """BankUnited."""
    rates = {}
    html = _get("https://www.bankunited.com/personal-banking/rates")
    txt = _html_text(html)

    v = _find_apy(txt, r'(savings|statement\s+savings)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_ocean_bank():
    """Ocean Bank (FL) — private bank, rates page."""
    rates = {}
    html = _get("https://www.oceanbank.com/rates/")
    txt = _html_text(html)

    v = _find_apy(txt, r'(savings|statement\s+savings)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_seacoast():
    """Seacoast National Bank."""
    rates = {}
    html = _get("https://www.seacoastbank.com/rates")
    txt = _html_text(html)

    v = _find_apy(txt, r'(savings|statement\s+savings)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


def scrape_servisfirst():
    """ServisFirst Bank."""
    rates = {}
    html = _get("https://www.servisfirstbank.com/personal/rates/")
    if not html:
        html = _get("https://www.servisfirstbank.com/rates/")
    txt = _html_text(html)

    v = _find_apy(txt, r'(savings|statement\s+savings)', 400)
    if v:
        rates["savings"] = v
    v = _find_apy(txt, r'money\s+market', 300)
    if v:
        rates["mma"] = v
    for pat, key in [
        (r'3.month', "cd_3mo"),
        (r'6.month', "cd_6mo"),
        (r'12.month|1.year', "cd_12mo"),
        (r'24.month|2.year', "cd_24mo"),
    ]:
        v = _find_apy(txt, pat, 300)
        if v:
            rates[key] = v
    return rates


# ── DISPATCH TABLE ──────────────────────────────────────────────────────────

SCRAPERS = {
    # Direct/Online
    "Ally Bank":               scrape_ally,
    "Marcus by Goldman Sachs": scrape_marcus,
    "Discover Bank":           scrape_discover,
    "American Express NB":     scrape_amex,
    "Synchrony Bank":          scrape_synchrony,
    "Barclays Bank DE":        scrape_barclays,
    "Capital One":             scrape_capital_one,
    "Bread Financial":         scrape_bread,
    # Large nationals
    "JP Morgan Chase":         scrape_jpmorgan,
    "Wells Fargo":             scrape_wells_fargo,
    "Truist":                  scrape_truist,
    "PNC Bank":                scrape_pnc,
    "Flagstar Bank NA":        scrape_flagstar,
    # NY Metro regionals
    "Berkshire Bank":          scrape_berkshire,
    "Cathay Bank":             scrape_cathay,
    "ConnectOne Bank":         scrape_connectone,
    "Dime Community Bank":     scrape_dime,
    "Flushing Bank":           scrape_flushing,
    "OceanFirst Bank NA":      scrape_oceanfirst,
    "Provident Bank":          scrape_provident,
    # South Florida regionals
    "Amerant Bank NA":         scrape_amerant,
    "BankUnited Inc":          scrape_bankunited,
    "Ocean Bank":              scrape_ocean_bank,
    "Seacoast National Bank":  scrape_seacoast,
    "ServisFirst Bank":        scrape_servisfirst,
}


def scrape_bank(bank_name):
    """Main entry point: returns rates dict for bank_name, empty dict if not found/failed."""
    fn = SCRAPERS.get(bank_name)
    if not fn:
        return {}
    try:
        return fn() or {}
    except Exception:
        return {}
