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

# Bloomberg dark theme palette
BG       = "#0d1117"
SURFACE  = "#161b22"
CARD     = "#1c2128"
BORDER   = "#30363d"
ACCENT   = "#fb923c"
GREEN    = "#3fb950"
RED      = "#f85149"
TEXT     = "#e6edf3"
TEXT2    = "#8b949e"
FONT     = "IBM Plex Sans, Arial, sans-serif"
MONO     = "JetBrains Mono, Courier New, monospace"

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
    return f'<td style="padding:6px 10px;text-align:right;font-family:{MONO};font-size:12px;color:{color};">{_pct(val)}</td>'

def _region_badge(label, color):
    return f'<span style="display:inline-block;background:{color};color:#000;font-size:9px;font-weight:700;padding:1px 6px;border-radius:10px;letter-spacing:.04em;white-space:nowrap;">{label}</span>'

def _combined_peer_table(ny_group, sfl_group, pb_rates):
    """Single merged table: NY Metro + South Florida peers + Popular Bank pinned at bottom."""
    prod_headers = "".join(
        f'<th style="padding:5px 8px;text-align:right;color:{TEXT2};font-size:10px;white-space:nowrap;">{lbl}</th>'
        for lbl in RATE_LABELS.values()
    )

    rows = ""
    ny_peers  = ny_group.get("peers_with_rates", ny_group.get("banks", []))
    sfl_peers = sfl_group.get("peers_with_rates", sfl_group.get("banks", []))

    # NY Metro rows
    rows += f"""
    <tr style="background:{SURFACE};">
      <td colspan="9" style="padding:5px 10px;font-size:10px;font-weight:700;color:#38bdf8;letter-spacing:.06em;text-transform:uppercase;">
        ▸ New York Metro
      </td>
    </tr>"""
    for peer in ny_peers:
        r = peer.get("rates", {})
        cells = "".join(_rate_td(r.get(p), pb_rates.get(p)) for p in PRODUCTS)
        rows += f"""
        <tr style="border-bottom:1px solid {BORDER};">
          <td style="padding:5px 10px;font-size:11px;color:{TEXT};white-space:nowrap;">
            {peer['name']}
            <span style="margin-left:5px;display:inline-block;background:#1e3a5f;color:#38bdf8;font-size:8px;font-weight:700;padding:1px 5px;border-radius:8px;">NYM</span>
          </td>
          {cells}
        </tr>"""

    # South Florida rows
    rows += f"""
    <tr style="background:{SURFACE};">
      <td colspan="9" style="padding:5px 10px;font-size:10px;font-weight:700;color:#4ade80;letter-spacing:.06em;text-transform:uppercase;">
        ▸ South Florida
      </td>
    </tr>"""
    for peer in sfl_peers:
        r = peer.get("rates", {})
        cells = "".join(_rate_td(r.get(p), pb_rates.get(p)) for p in PRODUCTS)
        rows += f"""
        <tr style="border-bottom:1px solid {BORDER};">
          <td style="padding:5px 10px;font-size:11px;color:{TEXT};white-space:nowrap;">
            {peer['name']}
            <span style="margin-left:5px;display:inline-block;background:#1a3a2a;color:#4ade80;font-size:8px;font-weight:700;padding:1px 5px;border-radius:8px;">SFL</span>
          </td>
          {cells}
        </tr>"""

    # Popular Bank pinned row
    subj_cells = "".join(
        f'<td style="padding:5px 8px;text-align:right;font-family:{MONO};font-size:11px;color:{ACCENT};font-weight:700;">{_pct(pb_rates.get(p))}</td>'
        for p in PRODUCTS
    )

    return f"""
    <div style="margin-bottom:28px;">
      <div style="font-size:13px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">
        Regional Peer Comparison — NY Metro &amp; South Florida
      </div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:6px;overflow:hidden;">
          <thead>
            <tr style="background:{SURFACE};border-bottom:2px solid {BORDER};">
              <th style="padding:6px 10px;text-align:left;color:{TEXT2};font-size:10px;white-space:nowrap;">Institution</th>
              {prod_headers}
            </tr>
          </thead>
          <tbody>
            {rows}
            <tr style="background:{SURFACE};border-top:2px solid {ACCENT};">
              <td style="padding:6px 10px;font-size:12px;color:{ACCENT};font-weight:700;">★ Popular Bank</td>
              {subj_cells}
            </tr>
          </tbody>
        </table>
      </div>
    </div>"""

def _peer_table(group_label, peers, subject_rates):
    prod_headers = "".join(
        f'<th style="padding:5px 8px;text-align:right;color:{TEXT2};font-size:10px;white-space:nowrap;">{lbl}</th>'
        for lbl in RATE_LABELS.values()
    )
    rows = ""
    for peer in peers:
        r = peer.get("rates", {})
        cells = "".join(
            _rate_td(r.get(p), subject_rates.get(p)) for p in PRODUCTS
        )
        rows += f"""
        <tr style="border-bottom:1px solid {BORDER};">
          <td style="padding:5px 10px;font-size:11px;color:{TEXT};white-space:nowrap;">{peer['name']}</td>
          {cells}
        </tr>"""

    subj_cells = "".join(
        f'<td style="padding:5px 8px;text-align:right;font-family:{MONO};font-size:11px;color:{ACCENT};font-weight:700;">{_pct(subject_rates.get(p))}</td>'
        for p in PRODUCTS
    )

    return f"""
    <div style="margin-bottom:28px;">
      <div style="font-size:13px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">{group_label}</div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:6px;overflow:hidden;">
          <thead>
            <tr style="background:{SURFACE};">
              <th style="padding:6px 10px;text-align:left;color:{TEXT2};font-size:10px;white-space:nowrap;">Institution</th>
              {prod_headers}
            </tr>
          </thead>
          <tbody>
            {rows}
            <tr style="background:{SURFACE};border-top:2px solid {ACCENT};">
              <td style="padding:6px 10px;font-size:12px;color:{ACCENT};font-weight:700;">★ Popular Bank</td>
              {subj_cells}
            </tr>
          </tbody>
        </table>
      </div>
    </div>"""

def _analysis_card(title, analysis):
    gaps = "".join(
        f'<li style="margin-bottom:4px;color:{TEXT2};">{g}</li>'
        for g in analysis.get("gaps", [])
    )
    return f"""
    <div style="background:{CARD};border-left:3px solid {ACCENT};border-radius:4px;padding:16px;margin-bottom:16px;">
      <div style="font-size:12px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px;">{title}</div>
      <p style="margin:0 0 8px;color:{TEXT};font-size:13px;">{analysis.get('position','')}</p>
      <ul style="margin:0;padding-left:18px;font-size:12px;">{gaps}</ul>
    </div>"""

def _risk_badge(risk_level):
    colors = {"LOW": GREEN, "MEDIUM": ACCENT, "HIGH": RED}
    c = colors.get(risk_level, TEXT2)
    return f'<span style="display:inline-block;background:{c};color:#000;font-size:11px;font-weight:700;padding:2px 10px;border-radius:12px;letter-spacing:.05em;">{risk_level} RISK</span>'

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
            f'<th style="padding:4px 6px;text-align:right;color:{TEXT2};font-size:9px;'
            f'white-space:nowrap;border-left:1px solid {BORDER};background:{SURFACE};">'
            f'<div style="color:{badge_color};font-weight:700;font-size:9px;">{short}</div>'
            f'<div style="font-size:8px;color:{TEXT2};">APY</div></th>'
        )

    def _pb_hdr():
        return (
            f'<th style="padding:4px 6px;text-align:right;font-size:9px;'
            f'white-space:nowrap;border-left:2px solid {ACCENT};background:{SURFACE};">'
            f'<div style="color:{ACCENT};font-weight:700;font-size:9px;">★ Popular</div>'
            f'<div style="font-size:8px;color:{ACCENT};">APY</div></th>'
        )

    def _peer_td(val, first=False):
        bl = f"border-left:1px solid {BORDER};" if first else ""
        if val is None:
            return f'<td style="padding:4px 6px;text-align:right;font-family:{MONO};font-size:10px;color:{TEXT2};{bl}">—</td>'
        return f'<td style="padding:4px 6px;text-align:right;font-family:{MONO};font-size:10px;color:{TEXT};{bl}">{val:.2f}%</td>'

    def _pb_td(apy_val):
        bl = f"border-left:2px solid {ACCENT};"
        if apy_val is None:
            return f'<td style="padding:4px 6px;text-align:right;font-family:{MONO};font-size:10px;color:{TEXT2};{bl}">—</td>'
        return f'<td style="padding:4px 6px;text-align:right;font-family:{MONO};font-size:10px;color:{ACCENT};font-weight:700;{bl}">{apy_val:.2f}%</td>'

    def _section_header(label, color, col_count):
        return (
            f'<tr style="background:{SURFACE};">'
            f'<td colspan="{col_count}" style="padding:6px 8px;font-size:10px;font-weight:700;'
            f'color:{color};letter-spacing:.05em;border-top:2px solid {BORDER};'
            f'border-bottom:1px solid {BORDER};">{label}</td>'
            f'</tr>'
        )

    def _bank_header_row(peers, badge_color):
        return (
            f'<tr style="border-bottom:2px solid {BORDER};">'
            f'<th style="padding:4px 8px;text-align:left;color:{TEXT2};font-size:9px;background:{SURFACE};">Tenor</th>'
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
                f'<td style="padding:5px 8px;font-size:11px;color:{TEXT};white-space:nowrap;font-weight:600;">{tenor}</td>'
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

        sfl_section = _section_header("▸ SOUTH FLORIDA REGION",  "#4ade80", sfl_cols)
        sfl_hdrs    = _bank_header_row(sfl_peers, "#4ade80")
        sfl_rows    = _data_rows(sfl_peers, tier_idx)

        tables_html += f"""
        <div style="margin-bottom:32px;">
          <div style="display:flex;align-items:baseline;gap:12px;margin-bottom:6px;">
            <span style="font-size:12px;font-weight:700;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;">
              CD Tier {tier_idx + 1} — {tier_label}
            </span>
            <span style="font-size:10px;color:{TEXT2};">
              Peer APY = nearest tenor bucket &nbsp;·&nbsp;
              <span style="color:{ACCENT};font-weight:600;">★ Popular Bank</span> = Tier {tier_idx + 1} APY
            </span>
          </div>
          <div style="overflow-x:auto;">
            <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:6px;overflow:hidden;font-size:11px;">
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
    <div style="margin-bottom:8px;">
      <div style="font-size:13px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:16px;">
        CD Tenor Comparison — Brick &amp; Mortar Peers vs. Popular Bank (All 5 Tiers)
      </div>
      {tables_html}
    </div>"""


def _cd_tier_table(cd_tiers):
    tiers = cd_tiers["tiers"]
    tenors = cd_tiers["tenors"]

    tier_hdrs = "".join(
        f'<th colspan="2" style="padding:6px 8px;text-align:center;color:{ACCENT};font-size:10px;border-left:1px solid {BORDER};white-space:nowrap;">{t}</th>'
        for t in tiers
    )
    sub_hdrs = "".join(
        f'<th style="padding:4px 6px;text-align:right;color:{TEXT2};font-size:10px;border-left:1px solid {BORDER};">Rate</th>'
        f'<th style="padding:4px 6px;text-align:right;color:{TEXT2};font-size:10px;">APY</th>'
        for _ in tiers
    )

    rows = ""
    for i, (tenor, tier_vals) in enumerate(tenors.items()):
        bg = CARD if i % 2 == 0 else SURFACE
        cells = "".join(
            f'<td style="padding:5px 6px;text-align:right;font-family:{MONO};font-size:11px;color:{TEXT2};border-left:1px solid {BORDER};">{v["rate"]:.2f}%</td>'
            f'<td style="padding:5px 6px;text-align:right;font-family:{MONO};font-size:11px;color:{TEXT};">{v["apy"]:.2f}%</td>'
            for v in tier_vals
        )
        rows += f'<tr style="background:{bg};border-bottom:1px solid {BORDER};">' \
                f'<td style="padding:5px 8px;font-size:11px;color:{TEXT};white-space:nowrap;">{tenor}</td>{cells}</tr>'

    return f"""
    <div style="margin-bottom:28px;">
      <div style="font-size:13px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Popular Bank — CD Rate Sheet (Consumer &amp; Business)</div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:6px;overflow:hidden;font-size:11px;">
          <thead>
            <tr style="background:{SURFACE};">
              <th style="padding:6px 8px;text-align:left;color:{TEXT2};font-size:10px;">Tenor</th>
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


def build_html_email(config, report, fred_data):
    now = datetime.now().strftime("%B %d, %Y")
    subject_banks = config["subject_banks"]
    peer_groups   = config["peer_groups"]

    prod_hdrs = "".join(
        f'<th style="padding:6px 10px;text-align:right;color:{TEXT2};font-size:11px;">{lbl}</th>'
        for lbl in RATE_LABELS.values()
    )
    subj_rows = ""
    for sb in subject_banks:
        r = sb["rates"]
        cells = "".join(
            f'<td style="padding:6px 10px;text-align:right;font-family:{MONO};font-size:12px;color:{ACCENT};">{_pct(r.get(p))}</td>'
            for p in PRODUCTS
        )
        subj_rows += f"""
        <tr style="border-bottom:1px solid {BORDER};">
          <td style="padding:6px 10px;font-size:12px;font-weight:600;color:{TEXT};">{sb['display_name']}</td>
          {cells}
        </tr>"""

    subject_table = f"""
    <div style="margin-bottom:28px;">
      <div style="font-size:13px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Subject Banks — Current Rates</div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:6px;overflow:hidden;">
          <thead>
            <tr style="background:{SURFACE};">
              <th style="padding:6px 10px;text-align:left;color:{TEXT2};font-size:11px;">Institution</th>
              {prod_hdrs}
            </tr>
          </thead>
          <tbody>{subj_rows}</tbody>
        </table>
      </div>
    </div>"""

    pb_cd_tiers = subject_banks[0].get("cd_tiers")
    pb_rates = subject_banks[0]["rates"]

    ny_grp  = peer_groups.get("ny_metro", {})
    sfl_grp = peer_groups.get("south_florida", {})
    do_grp  = peer_groups.get("direct_online", {})
    do_peers = do_grp.get("peers_with_rates", do_grp.get("banks", []))

    peer_tables = (
        _combined_peer_table(ny_grp, sfl_grp, pb_rates) +
        _peer_table(do_grp.get("label", "Direct / Online Banks"), do_peers, subject_banks[1]["rates"])
    )

    analysis_cards = (
        _analysis_card("New York Metro Analysis", report.get("ny_metro_analysis", {})) +
        _analysis_card("South Florida Analysis",  report.get("south_florida_analysis", {})) +
        _analysis_card("Direct / Online Analysis (Popular Direct)", report.get("direct_online_analysis", {}))
    )

    fred_mapping = {
        "FEDFUNDS": "Fed Funds", "MMNRNNS": "Nat'l MMA",
        "CD3NAX": "Nat'l 3Mo", "CD6NAX": "Nat'l 6Mo", "CD1NAX": "Nat'l 12Mo"
    }
    fred_cells = "".join(
        f'<td style="padding:6px 14px;text-align:center;font-family:{MONO};font-size:12px;color:{TEXT};">'
        f'<div style="color:{TEXT2};font-size:10px;margin-bottom:2px;">{lbl}</div>'
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

  <!-- Header -->
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
    <tr>
      <td>
        <div style="font-size:22px;font-weight:700;color:{ACCENT};letter-spacing:-.02em;">DepositIQ</div>
        <div style="font-size:12px;color:{TEXT2};margin-top:2px;">Deposit Rate Intelligence • Popular Bank</div>
      </td>
      <td align="right" style="vertical-align:top;">
        <div style="font-size:11px;color:{TEXT2};">{now}</div>
        <div style="margin-top:4px;">{_risk_badge(risk_level)}</div>
      </td>
    </tr>
  </table>

  <!-- National Benchmarks -->
  <div style="margin-bottom:24px;">
    <div style="font-size:13px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">National Benchmarks (FRED)</div>
    <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:6px;overflow:hidden;">
      <tr>{fred_cells}</tr>
    </table>
  </div>

  <!-- Subject Banks -->
  {subject_table}

  <!-- Unified CD Tenor & Tier Table (NYM + SFL + Popular Bank) -->
  {_unified_cd_table(ny_grp, sfl_grp, pb_cd_tiers) if pb_cd_tiers else ''}

  <!-- Peer Tables -->
  {peer_tables}

  <!-- Rate Analysis Cards -->
  <div style="margin-bottom:24px;">
    <div style="font-size:13px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;">Regional Rate Analysis — Key Takeaways</div>
    {analysis_cards}
  </div>

  <!-- Footer -->
  <div style="border-top:1px solid {BORDER};padding-top:14px;font-size:10px;color:{TEXT2};text-align:center;">
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
