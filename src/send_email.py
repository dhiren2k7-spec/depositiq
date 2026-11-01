import os
import json
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
GMAIL_USER = "dhiren2k7@gmail.com"

RATE_LABELS = {
    "checking_apy": "Checking",
    "savings":      "Savings",
    "mma":          "MMA",
    "cd_3mo":       "3Mo CD",
    "cd_6mo":       "6Mo CD",
    "cd_12mo":      "12Mo CD",
    "cd_24mo":      "24Mo CD"
}

PRODUCTS = list(RATE_LABELS.keys())

# Extended label set for Direct/Online Banks — includes additional CD tenors
# not tracked for regional peers (NYM/SFL)
DO_RATE_LABELS = {
    "checking_apy": "Checking",
    "savings":      "Savings",
    "mma":          "MMA",
    "cd_3mo":       "3Mo CD",
    "cd_6mo":       "6Mo CD",
    "cd_9mo":       "9Mo CD",
    "cd_12mo":      "12Mo CD",
    "cd_18mo":      "18Mo CD",
    "cd_24mo":      "24Mo CD",
    "cd_36mo":      "3Yr CD",
    "cd_48mo":      "4Yr CD",
    "cd_60mo":      "5Yr CD",
}

DO_PRODUCTS = list(DO_RATE_LABELS.keys())

# Popular Bank Professional Light Theme
PB_BLUE  = "#003087"   # Popular Bank corporate blue — header/title backgrounds
PB_RED   = "#CC0000"   # Popular Bank red (from logo)
BG       = "#f4f6f9"   # light gray page background
SURFACE  = "#f8f9fa"   # off-white surface rows
CARD     = "#ffffff"   # white cards
BORDER   = "#d0d7de"   # light border
TEXT     = "#1a1a2e"   # near-black text
TEXT2    = "#4a5568"   # medium gray secondary text
ACCENT   = "#fb923c"   # orange accents (keep for rate highlights)
GREEN    = "#3fb950"   # green (keep for rate comparison)
RED      = "#f85149"   # red (keep for rate comparison)
FONT     = "IBM Plex Sans, Arial, sans-serif"
MONO     = "JetBrains Mono, Courier New, monospace"

# Popular Bank logo — base64 encoded PNG
_PB_LOGO_B64 = "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"

def _pct(v):
    if v is None:
        return "—"
    return f"{v:.2f}%"

def _rate_color(subj, peer):
    if subj is None or peer is None:
        return TEXT2
    diff = subj - peer
    if diff >= 0.10:
        return GREEN
    if diff <= -0.10:
        return RED
    return TEXT

def _rate_td(val, compare=None):
    color = _rate_color(val, compare) if compare is not None else TEXT
    return f'<td style="padding:7px 12px;text-align:right;font-family:{MONO};font-size:18px;color:{color};">{_pct(val)}</td>'

def _region_badge(label, color):
    return f'<span style="display:inline-block;background:{color};color:#fff;font-size:14px;font-weight:700;padding:2px 8px;border-radius:10px;letter-spacing:.04em;white-space:nowrap;">{label}</span>'

def _peer_table(group_label, peers, subject_rates, rate_labels=None, show_subject=True):
    if rate_labels is None:
        rate_labels = RATE_LABELS
    products = list(rate_labels.keys())
    prod_headers = "".join(
        f'<th style="padding:6px 10px;text-align:right;color:{TEXT2};font-size:17px;white-space:nowrap;font-weight:600;">{lbl}</th>'
        for lbl in rate_labels.values()
    )
    rows = ""
    for peer in peers:
        r = peer.get("rates", {})
        cells = "".join(
            _rate_td(r.get(p), subject_rates.get(p)) for p in products
        )
        rows += f"""
        <tr style="border-bottom:1px solid {BORDER};">
          <td style="padding:6px 12px;font-size:18px;color:{TEXT};white-space:nowrap;">{peer['name']}</td>
          {cells}
        </tr>"""

    subj_cells = "".join(
        f'<td style="padding:6px 10px;text-align:right;font-family:{MONO};font-size:18px;color:{PB_BLUE};font-weight:700;">{_pct(subject_rates.get(p))}</td>'
        for p in products
    )

    return f"""
    <div style="margin-bottom:32px;">
      <div style="font-size:20px;font-weight:700;color:{PB_BLUE};text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">{group_label}</div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
          <thead>
            <tr style="background:{SURFACE};border-bottom:2px solid {PB_BLUE};">
              <th style="padding:8px 12px;text-align:left;color:{TEXT2};font-size:17px;white-space:nowrap;font-weight:600;">Institution</th>
              {prod_headers}
            </tr>
          </thead>
          <tbody>
            {rows}
            {f'''<tr style="background:#e8f0fb;border-top:2px solid {PB_BLUE};">
              <td style="padding:8px 12px;font-size:18px;color:{PB_BLUE};font-weight:700;">★ Popular Bank</td>
              {subj_cells}
            </tr>''' if show_subject else ''}
          </tbody>
        </table>
      </div>
    </div>"""

def _analysis_card(title, analysis):
    bullets = analysis.get("gaps", []) or analysis.get("takeaways", [])
    items = "".join(
        f'<li style="margin-bottom:6px;color:{TEXT2};font-size:18px;">{g}</li>'
        for g in bullets
    )
    bullet_section = f'<div style="font-size:16px;font-weight:700;color:{PB_BLUE};text-transform:uppercase;letter-spacing:.07em;margin:10px 0 6px;">Key Takeaways</div><ul style="margin:0;padding-left:20px;font-size:18px;">{items}</ul>' if items else ""
    return f"""
    <div style="background:{CARD};border-left:4px solid {PB_BLUE};border-radius:6px;padding:18px 20px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,0.06);">
      <div style="font-size:19px;font-weight:700;color:{PB_BLUE};text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px;">{title}</div>
      <p style="margin:0 0 6px;color:{TEXT};font-size:18px;">{analysis.get('position','')}</p>
      {bullet_section}
    </div>"""

def _risk_badge(risk_level):
    colors = {"LOW": GREEN, "MEDIUM": ACCENT, "HIGH": RED}
    c = colors.get(risk_level, TEXT2)
    return f'<span style="display:inline-block;background:{c};color:#fff;font-size:16px;font-weight:700;padding:3px 12px;border-radius:12px;letter-spacing:.05em;">{risk_level} RISK</span>'

# Maps each Popular Bank tenor label to the flat FDIC product key for peers
_TENOR_TO_PRODUCT = {
    "30-89 Days":    "cd_3mo",
    "90-179 Days":   "cd_3mo",
    "180-269 Days":  "cd_6mo",
    "270-364 Days":  "cd_6mo",
    "12-17 Months":  "cd_12mo",
    "18-23 Months":  "cd_12mo",
    "24-35 Months":  "cd_24mo",
    "36-47 Months":  None,
    "48-59 Months":  None,
    "60-119 Months": None,
    "120 Months":    None,
}

def _unified_cd_table(ny_group, sfl_group, pb_cd_tiers):
    """
    One table per Popular Bank CD tier (5 total).
    Each table: NYM section on top, SFL section below.
    Columns: [Tenor] | [peer APYs...] | [★ Popular Bank APY for that tier]
    """
    if not pb_cd_tiers:
        return ""

    tiers  = pb_cd_tiers["tiers"]   # list of 5 tier label strings
    tenors = pb_cd_tiers["tenors"]  # OrderedDict: tenor_label -> list of 5 tier dicts

    ny_peers  = ny_group.get("peers_with_rates",  ny_group.get("banks",  []))
    sfl_peers = sfl_group.get("peers_with_rates", sfl_group.get("banks", []))

    def _bank_hdr(name, badge_color):
        short = (name.replace(" Bank", "").replace(" NA", "")
                     .replace(", N.A.", "").replace(" Inc", "")[:14])
        return (
            f'<th style="padding:5px 8px;text-align:right;color:{TEXT2};font-size:15px;'
            f'white-space:nowrap;border-left:1px solid {BORDER};background:{SURFACE};">'
            f'<div style="color:{badge_color};font-weight:700;font-size:15px;">{short}</div>'
            f'<div style="font-size:14px;color:{TEXT2};">APY</div></th>'
        )

    def _pb_hdr():
        return (
            f'<th style="padding:5px 8px;text-align:right;font-size:15px;'
            f'white-space:nowrap;border-left:2px solid {PB_BLUE};background:#e8f0fb;">'
            f'<div style="color:{PB_BLUE};font-weight:700;font-size:15px;">★ Popular</div>'
            f'<div style="font-size:14px;color:{PB_BLUE};">APY</div></th>'
        )

    def _peer_td(val, first=False):
        bl = f"border-left:1px solid {BORDER};" if first else ""
        if val is None:
            return f'<td style="padding:5px 8px;text-align:right;font-family:{MONO};font-size:16px;color:{TEXT2};{bl}">—</td>'
        return f'<td style="padding:5px 8px;text-align:right;font-family:{MONO};font-size:16px;color:{TEXT};{bl}">{val:.2f}%</td>'

    def _pb_td(apy_val):
        bl = f"border-left:2px solid {PB_BLUE};"
        if apy_val is None:
            return f'<td style="padding:5px 8px;text-align:right;font-family:{MONO};font-size:16px;color:{TEXT2};{bl}">—</td>'
        return f'<td style="padding:5px 8px;text-align:right;font-family:{MONO};font-size:16px;color:{PB_BLUE};font-weight:700;{bl}">{apy_val:.2f}%</td>'

    def _section_header(label, color, col_count):
        return (
            f'<tr style="background:{color}15;">'
            f'<td colspan="{col_count}" style="padding:7px 10px;font-size:16px;font-weight:700;'
            f'color:{color};letter-spacing:.05em;border-top:2px solid {color};'
            f'border-bottom:1px solid {BORDER};">{label}</td>'
            f'</tr>'
        )

    def _bank_header_row(peers, badge_color):
        return (
            f'<tr style="border-bottom:2px solid {BORDER};">'
            f'<th style="padding:5px 10px;text-align:left;color:{TEXT2};font-size:15px;background:{SURFACE};">Tenor</th>'
            + "".join(_bank_hdr(b["name"], badge_color) for b in peers)
            + _pb_hdr()
            + '</tr>'
        )

    def _data_rows(peers, tier_idx):
        rows = ""
        for i, (tenor, tier_vals) in enumerate(tenors.items()):
            bg = CARD if i % 2 == 0 else SURFACE
            product_key = _TENOR_TO_PRODUCT.get(tenor)
            pb_apy = tier_vals[tier_idx]["apy"] if tier_vals and tier_idx < len(tier_vals) else None

            peer_cells = "".join(
                _peer_td(peer.get("rates", {}).get(product_key) if product_key else None, first=(j == 0))
                for j, peer in enumerate(peers)
            )
            rows += (
                f'<tr style="background:{bg};border-bottom:1px solid {BORDER};">'
                f'<td style="padding:6px 10px;font-size:17px;color:{TEXT};white-space:nowrap;font-weight:600;">{tenor}</td>'
                f'{peer_cells}{_pb_td(pb_apy)}'
                f'</tr>'
            )
        return rows

    # Build one table per tier
    tables_html = ""
    for tier_idx, tier_label in enumerate(tiers):
        ny_cols  = len(ny_peers)  + 2   # tenor + peers + PB
        sfl_cols = len(sfl_peers) + 2

        ny_section  = _section_header("▸ NY METRO REGION",       "#38bdf8", ny_cols)
        ny_hdrs     = _bank_header_row(ny_peers,  "#38bdf8")
        ny_rows     = _data_rows(ny_peers,  tier_idx)

        sfl_section = _section_header("▸ SOUTH FLORIDA REGION",  "#16a34a", sfl_cols)
        sfl_hdrs    = _bank_header_row(sfl_peers, "#16a34a")
        sfl_rows    = _data_rows(sfl_peers, tier_idx)

        tables_html += f"""
        <div style="margin-bottom:36px;">
          <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:8px;">
            <span style="font-size:18px;font-weight:700;color:{PB_BLUE};text-transform:uppercase;letter-spacing:.08em;">
              CD Tier {tier_idx + 1} — {tier_label}
            </span>
            <span style="font-size:16px;color:{TEXT2};">
              Peer APY = nearest tenor bucket &nbsp;·&nbsp;
              <span style="color:{PB_BLUE};font-weight:600;">★ Popular Bank</span> = Tier {tier_idx + 1} APY
            </span>
          </div>
          <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.07);font-size:16px;">
              <thead>{ny_section}{ny_hdrs}</thead>
              <tbody>
                {ny_rows}
                {sfl_section}{sfl_hdrs}
                {sfl_rows}
              </tbody>
            </table>
          </div>
        </div>"""

    return f"""
    <div style="margin-bottom:10px;">
      <div style="font-size:20px;font-weight:700;color:{PB_BLUE};text-transform:uppercase;letter-spacing:.08em;margin-bottom:18px;">
        CD Tenor Comparison — Brick &amp; Mortar Peers vs. Popular Bank (All 5 Tiers)
      </div>
      {tables_html}
    </div>"""


def _cd_tier_table(cd_tiers):
    tiers = cd_tiers["tiers"]
    tenors = cd_tiers["tenors"]

    tier_hdrs = "".join(
        f'<th colspan="2" style="padding:7px 10px;text-align:center;color:{PB_BLUE};font-size:17px;border-left:1px solid {BORDER};white-space:nowrap;font-weight:700;">{t}</th>'
        for t in tiers
    )
    sub_hdrs = "".join(
        f'<th style="padding:5px 8px;text-align:right;color:{TEXT2};font-size:17px;border-left:1px solid {BORDER};font-weight:600;">Rate</th>'
        f'<th style="padding:5px 8px;text-align:right;color:{TEXT2};font-size:17px;font-weight:600;">APY</th>'
        for _ in tiers
    )

    rows = ""
    for i, (tenor, tier_vals) in enumerate(tenors.items()):
        bg = CARD if i % 2 == 0 else SURFACE
        cells = "".join(
            f'<td style="padding:6px 8px;text-align:right;font-family:{MONO};font-size:16px;color:{TEXT2};border-left:1px solid {BORDER};">{v["rate"]:.2f}%</td>'
            f'<td style="padding:6px 8px;text-align:right;font-family:{MONO};font-size:16px;color:{TEXT};">{v["apy"]:.2f}%</td>'
            for v in tier_vals
        )
        rows += f'<tr style="background:{bg};border-bottom:1px solid {BORDER};">' \
                f'<td style="padding:6px 10px;font-size:17px;color:{TEXT};white-space:nowrap;">{tenor}</td>{cells}</tr>'

    return f"""
    <div style="margin-bottom:32px;">
      <div style="font-size:20px;font-weight:700;color:{PB_BLUE};text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">Popular Bank — CD Rate Sheet (Consumer &amp; Business)</div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.07);font-size:16px;">
          <thead>
            <tr style="background:{SURFACE};border-bottom:2px solid {PB_BLUE};">
              <th style="padding:8px 10px;text-align:left;color:{TEXT2};font-size:17px;font-weight:600;">Tenor</th>
              {tier_hdrs}
            </tr>
            <tr style="background:{SURFACE};border-bottom:2px solid {BORDER};">
              <th></th>{sub_hdrs}
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>"""


NYM_COLOR = "#38bdf8"
SFL_COLOR = "#4ade80"

_PROMO_REGION_MAP = {
    # NYM
    "Beacon Bank - Berkshire & Capital Region": "NYM",
    "ConnectOne Bank":                          "NYM",
    "Dime Community Bank":                      "NYM",
    "Flagstar Bank":                            "NYM",
    "OceanFirst Bank":                          "NYM",
    "Provident Bank":                           "NYM",
    "Chase - Downstate":                        "NYM",
    "PNC Bank - Manhattan":                     "NYM",
    # SFL
    "Amerant Bank":                             "SFL",
    "BankUnited":                               "SFL",
    "Ocean Bank":                               "SFL",
    "Seacoast National Bank":                   "SFL",
    "ServisFirst Bank":                         "SFL",
    "Chase - Florida":                          "SFL",
    "Wells Fargo Bank - South Florida":         "SFL",
    "Truist":                                   "SFL",
}


def _promo_cd_table(excel_path):
    """Build Promo CD rate comparison table from Excel survey data.
    Rows = banks (NYM section on top, SFL below, Popular Bank pinned last in each section).
    Columns = all unique promo tenors across peer banks + Popular Bank.
    Cells = APY. Popular Bank row in PB_BLUE.
    """
    if not excel_path or not os.path.exists(excel_path):
        print(f"  [promo] Excel not found at: {excel_path!r} — skipping promo table")
        return ""
    try:
        import openpyxl
        from collections import defaultdict
    except ImportError:
        return ""

    try:
        wb = openpyxl.load_workbook(excel_path)
        ws = wb.active
        rows = [r for r in ws.iter_rows(values_only=True) if any(c is not None for c in r)]
    except Exception:
        return ""

    # Filter to CD Special rows only
    cd_rows = [r for r in rows[2:] if r[2] == "CD" and r[3] == "Special"]

    # Peer banks: best APY per (bank, tenor)
    bank_tenor_apy = defaultdict(lambda: defaultdict(list))
    pb_tenor_tiers = defaultdict(list)  # tenor -> list of (min_bal, apy)

    for r in cd_rows:
        bank  = r[0]
        tenor = r[4]   # min_term months
        apy   = r[9]
        if apy is None:
            continue
        if bank == "Popular Bank":
            pb_tenor_tiers[tenor].append((r[6], apy))  # (min_bal, apy)
        else:
            bank_tenor_apy[bank][tenor].append(apy)

    # Best peer APY per bank/tenor
    bank_best = {b: {t: max(v) for t, v in td.items()} for b, td in bank_tenor_apy.items()}

    # Popular Bank Tier 1 (min_bal=1000) APY per tenor
    pb_tier1 = {}
    for tenor, vals in pb_tenor_tiers.items():
        t1 = [a for (mb, a) in vals if mb == 1000]
        if t1:
            pb_tier1[tenor] = t1[0]

    # All unique tenors: peer tenors UNION PB tenors, sorted
    all_tenors = sorted(
        set(t for b in bank_best.values() for t in b.keys()) | set(pb_tier1.keys())
    )

    if not all_tenors:
        return ""

    # Bucket banks by region
    nym_banks = [b for b in sorted(bank_best) if _PROMO_REGION_MAP.get(b) == "NYM"]
    sfl_banks = [b for b in sorted(bank_best) if _PROMO_REGION_MAP.get(b) == "SFL"]

    # Short name helper (strip long suffixes)
    def _short(name):
        return (name.replace("Bank - Berkshire & Capital Region", "Bank - Berkshire")
                    .replace("Wells Fargo Bank - South Florida", "Wells Fargo SFL")
                    .replace("PNC Bank - Manhattan", "PNC - Manhattan")
                    .replace("Chase - Downstate", "Chase Downstate")
                    .replace("Chase - Florida", "Chase Florida"))

    # --- Build header row (tenor columns) ---
    tenor_hdrs = "".join(
        f'<th style="padding:6px 9px;text-align:right;color:{TEXT2};font-size:17px;'
        f'white-space:nowrap;border-left:1px solid {BORDER};font-weight:600;">{t}mo</th>'
        for t in all_tenors
    )

    # --- Build a data row ---
    def _row(bank_name, apy_dict, bg, is_pb=False):
        name_color = PB_BLUE if is_pb else TEXT
        name_weight = "700" if is_pb else "400"
        star = "★ " if is_pb else ""
        cells = ""
        for t in all_tenors:
            val = apy_dict.get(t)
            if val is None:
                cell_txt = "—"
                cell_color = TEXT2
            else:
                cell_txt = f"{val:.2f}%"
                cell_color = PB_BLUE if is_pb else TEXT
            cells += (
                f'<td style="padding:6px 9px;text-align:right;font-family:{MONO};'
                f'font-size:17px;color:{cell_color};border-left:1px solid {BORDER};">'
                f'{cell_txt}</td>'
            )
        return (
            f'<tr style="background:{bg};border-bottom:1px solid {BORDER};">'
            f'<td style="padding:6px 10px;font-size:18px;color:{name_color};'
            f'font-weight:{name_weight};white-space:nowrap;">{star}{_short(bank_name)}</td>'
            f'{cells}</tr>'
        )

    # --- Build section header spanning all cols ---
    def _section_hdr(label, color):
        col_count = len(all_tenors) + 1
        return (
            f'<tr><td colspan="{col_count}" style="background:{color}18;'
            f'padding:6px 12px;font-size:17px;font-weight:700;color:{color};'
            f'letter-spacing:.06em;border-top:2px solid {color};">{label}</td></tr>'
        )

    # Build rows
    tbody = ""

    # NYM section
    if nym_banks:
        tbody += _section_hdr("NY METRO", NYM_COLOR)
        for i, b in enumerate(nym_banks):
            bg = CARD if i % 2 == 0 else SURFACE
            tbody += _row(b, bank_best[b], bg)
        # PB as last row of NYM section
        tbody += _row("Popular Bank", pb_tier1, "#e8f0fb", is_pb=True)

    # SFL section
    if sfl_banks:
        tbody += _section_hdr("SOUTH FLORIDA", SFL_COLOR)
        for i, b in enumerate(sfl_banks):
            bg = CARD if i % 2 == 0 else SURFACE
            tbody += _row(b, bank_best[b], bg)
        # PB as last row of SFL section too
        tbody += _row("Popular Bank", pb_tier1, "#e8f0fb", is_pb=True)

    col_count = len(all_tenors) + 1

    return f"""
    <div style="margin-bottom:36px;">
      <div style="font-size:20px;font-weight:700;color:{PB_BLUE};text-transform:uppercase;
           letter-spacing:.08em;margin-bottom:6px;">Promotional CD Rate Comparison — NY Metro &amp; South Florida</div>
      <div style="font-size:16px;color:{TEXT2};margin-bottom:10px;">
        Best available APY per tenor · Peer banks show highest APY across all balance tiers ·
        ★ Popular Bank shows Tier 1 ($1K–$25K) APY · Survey as of 10/26/2026
      </div>
      <div style="overflow-x:auto;">
        <table style="border-collapse:collapse;background:{CARD};border-radius:8px;
               overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.07);font-size:16px;min-width:100%;">
          <thead>
            <tr style="background:{SURFACE};border-bottom:2px solid {PB_BLUE};">
              <th style="padding:8px 12px;text-align:left;color:{TEXT2};font-size:17px;
                  white-space:nowrap;font-weight:600;">Institution</th>
              {tenor_hdrs}
            </tr>
          </thead>
          <tbody>{tbody}</tbody>
        </table>
      </div>
    </div>"""


def build_html_email(config, report, fred_data):
    now = datetime.now().strftime("%B %d, %Y")
    subject_banks = config["subject_banks"]
    peer_groups   = config["peer_groups"]

    prod_hdrs = "".join(
        f'<th style="padding:8px 12px;text-align:right;color:{TEXT2};font-size:18px;font-weight:600;">{lbl}</th>'
        for lbl in RATE_LABELS.values()
    )
    subj_rows = ""
    for sb in subject_banks:
        r = sb["rates"]
        cells = "".join(
            f'<td style="padding:8px 12px;text-align:right;font-family:{MONO};font-size:18px;color:{PB_BLUE};font-weight:600;">{_pct(r.get(p))}</td>'
            for p in PRODUCTS
        )
        subj_rows += f"""
        <tr style="border-bottom:1px solid {BORDER};">
          <td style="padding:8px 12px;font-size:18px;font-weight:600;color:{TEXT};">{sb['display_name']}</td>
          {cells}
        </tr>"""

    subject_table = f"""
    <div style="margin-bottom:32px;">
      <div style="font-size:20px;font-weight:700;color:{PB_BLUE};text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">Subject Banks — Current Rates</div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
          <thead>
            <tr style="background:{SURFACE};border-bottom:2px solid {PB_BLUE};">
              <th style="padding:8px 12px;text-align:left;color:{TEXT2};font-size:18px;font-weight:600;">Institution</th>
              {prod_hdrs}
            </tr>
          </thead>
          <tbody>{subj_rows}</tbody>
        </table>
      </div>
    </div>"""

    pb_cd_tiers = subject_banks[0].get("cd_tiers")
    pb_rates = subject_banks[0]["rates"]
    promo_excel = config.get("promo_cd_excel_path", "")


    ny_grp  = peer_groups.get("ny_metro", {})
    sfl_grp = peer_groups.get("south_florida", {})
    do_grp  = peer_groups.get("direct_online", {})
    do_peers = do_grp.get("peers_with_rates", do_grp.get("banks", []))

    peer_tables = (
        _peer_table(do_grp.get("label", "Popular Direct"), do_peers, subject_banks[1]["rates"], DO_RATE_LABELS, show_subject=False)
    )

    analysis_cards = (
        _analysis_card("New York Metro Analysis", report.get("ny_metro_analysis", {})) +
        _analysis_card("South Florida Analysis",  report.get("south_florida_analysis", {})) +
        _analysis_card("Popular Direct — Key Takeaways", report.get("direct_online_analysis", {}))
    )

    fred_mapping = {
        "FEDFUNDS": "Fed Funds", "MMNRNNS": "Nat'l MMA",
        "CD3NAX": "Nat'l 3Mo", "CD6NAX": "Nat'l 6Mo", "CD1NAX": "Nat'l 12Mo"
    }
    fred_cells = "".join(
        f'<td style="padding:8px 16px;text-align:center;font-family:{MONO};font-size:18px;color:{TEXT};">'
        f'<div style="color:{TEXT2};font-size:17px;margin-bottom:3px;font-weight:600;">{lbl}</div>'
        f'{_pct(fred_data.get(k))}</td>'
        for k, lbl in fred_mapping.items()
    )

    risk_level = report.get("risk_level", "MEDIUM")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DepositIQ — Popular Bank — {now}</title>
<style>
@page {{ size: A4 landscape; margin: 10mm; }}
body {{ -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; text-rendering: optimizeLegibility; }}
</style>
</head>
<body style="margin:0;padding:0;background:{BG};font-family:{FONT};color:{TEXT};-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;">
<div style="max-width:1400px;margin:0 auto;padding:24px 16px;">

  <!-- Header — Full-width Popular Bank blue band: title LEFT, logo RIGHT -->
  <div style="background:{PB_BLUE};border-radius:10px;padding:0;margin-bottom:28px;overflow:hidden;box-shadow:0 2px 8px rgba(0,48,135,0.25);">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <td style="padding:22px 28px;vertical-align:middle;">
          <div style="font-size:36px;font-weight:700;color:#ffffff;letter-spacing:-.02em;line-height:1.1;">DepositIQ</div>
          <div style="font-size:18px;color:rgba(255,255,255,0.85);margin-top:6px;letter-spacing:.02em;">Deposit Rate Intelligence • Popular Bank</div>
        </td>
        <td align="right" style="padding:22px 28px;vertical-align:middle;">
          <img src="data:image/png;base64,{_PB_LOGO_B64}" style="height:120px;display:block;margin-left:auto;margin-bottom:10px;" alt="Popular Bank">
          <div style="font-size:17px;color:rgba(255,255,255,0.8);margin-bottom:6px;text-align:right;">{now}</div>
          <div style="text-align:right;">{_risk_badge(risk_level)}</div>
        </td>
      </tr>
    </table>
  </div>

  <!-- National Benchmarks -->
  <div style="margin-bottom:28px;">
    <div style="font-size:20px;font-weight:700;color:{PB_BLUE};text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">National Benchmarks (FRED)</div>
    <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08);">
      <tr>{fred_cells}</tr>
    </table>
  </div>

  <!-- Subject Banks -->
  {subject_table}

  <!-- Unified CD Tenor & Tier Table (NYM + SFL + Popular Bank) -->
  {_unified_cd_table(ny_grp, sfl_grp, pb_cd_tiers) if pb_cd_tiers else ''}

  <!-- Promotional CD Rate Comparison -->
  {_promo_cd_table(promo_excel) if promo_excel else ''}

  <!-- Peer Tables -->
  {peer_tables}

  <!-- Rate Analysis Cards -->
  <div style="margin-bottom:28px;">
    <div style="font-size:20px;font-weight:700;color:{PB_BLUE};text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px;">Regional Rate Analysis — Key Takeaways</div>
    {analysis_cards}
  </div>

  <!-- Footer -->
  <div style="border-top:2px solid {PB_BLUE};padding-top:16px;font-size:16px;color:{TEXT2};text-align:center;">
    DepositIQ • Automated deposit intelligence powered by FDIC BankFind + FRED
    • Delivered every Monday 6:45 AM ET • Data may have 1-week lag
  </div>

</div>
</body>
</html>"""

    return html

def generate_pdf(html_body, output_path):
    """Convert HTML report to PDF using weasyprint."""
    try:
        from weasyprint import HTML
        HTML(string=html_body).write_pdf(output_path)
        return True
    except Exception as e:
        print(f"  PDF generation failed: {e}")
        return False


def _attach_file(msg, path, filename, mime_type="application/octet-stream"):
    with open(path, "rb") as f:
        part = MIMEBase(*mime_type.split("/", 1))
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)


def send_email(html_body, to_email, from_email, week_date=None, excel_path=None, html_path=None, pdf_path=None, bcc_email=None):
    if week_date is None:
        week_date = datetime.now().strftime("%b %d, %Y")

    safe_date = week_date.replace(" ", "_").replace(",", "")
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"DepositIQ — Popular Bank Rate Intelligence — {week_date}"
    msg["From"] = f"DepositIQ <{GMAIL_USER}>"
    recipients = [r.strip() for r in to_email.split(",") if r.strip()]
    msg["To"] = ", ".join(recipients)
    bcc_list = [b.strip() for b in bcc_email.split(",") if b.strip()] if bcc_email else []
    if bcc_list:
        msg["Bcc"] = ", ".join(bcc_list)

    # Inline HTML body
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    # Excel attachment
    if excel_path and os.path.exists(excel_path):
        _attach_file(msg, excel_path,
                     f"DepositIQ_{safe_date}.xlsx",
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # HTML attachment
    if html_path and os.path.exists(html_path):
        _attach_file(msg, html_path,
                     f"DepositIQ_{safe_date}.html",
                     "text/html")

    # PDF attachment
    if pdf_path and os.path.exists(pdf_path):
        _attach_file(msg, pdf_path,
                     f"DepositIQ_{safe_date}.pdf",
                     "application/pdf")

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, recipients + bcc_list, msg.as_string())

    print(f"Email sent to {to_email}")
    return 200
