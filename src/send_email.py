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

def _peer_table(group_label, peers, subject_rates):
    prod_headers = "".join(
        f'<th style="padding:6px 10px;text-align:right;color:{TEXT2};font-size:11px;white-space:nowrap;">{lbl}</th>'
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
          <td style="padding:6px 10px;font-size:12px;color:{TEXT};white-space:nowrap;">{peer['name']}</td>
          {cells}
        </tr>"""

    subj_cells = "".join(
        f'<td style="padding:6px 10px;text-align:right;font-family:{MONO};font-size:12px;color:{ACCENT};font-weight:600;">{_pct(subject_rates.get(p))}</td>'
        for p in PRODUCTS
    )

    return f"""
    <div style="margin-bottom:28px;">
      <div style="font-size:13px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">{group_label}</div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:6px;overflow:hidden;">
          <thead>
            <tr style="background:{SURFACE};">
              <th style="padding:6px 10px;text-align:left;color:{TEXT2};font-size:11px;white-space:nowrap;">Institution</th>
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
      <ul style="margin:0 0 8px;padding-left:18px;font-size:12px;">{gaps}</ul>
      <div style="background:{SURFACE};border-radius:4px;padding:10px;font-size:12px;color:{GREEN};">
        <strong>→ Recommendation:</strong> {analysis.get('recommendation','')}
      </div>
    </div>"""

def _risk_badge(risk_level):
    colors = {"LOW": GREEN, "MEDIUM": ACCENT, "HIGH": RED}
    c = colors.get(risk_level, TEXT2)
    return f'<span style="display:inline-block;background:{c};color:#000;font-size:11px;font-weight:700;padding:2px 10px;border-radius:12px;letter-spacing:.05em;">{risk_level} RISK</span>'

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

    pb_rates = subject_banks[0]["rates"]

    peer_tables = ""
    for gk in ["ny_metro", "south_florida", "direct_online"]:
        grp = peer_groups.get(gk, {})
        peers = grp.get("peers_with_rates", grp.get("banks", []))
        subj_r = subject_banks[1]["rates"] if gk == "direct_online" else pb_rates
        peer_tables += _peer_table(grp.get("label", gk), peers, subj_r)

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
</head>
<body style="margin:0;padding:0;background:{BG};font-family:{FONT};color:{TEXT};">
<div style="max-width:860px;margin:0 auto;padding:24px 16px;">

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

  <!-- Week Summary -->
  <div style="background:{CARD};border-left:4px solid {ACCENT};border-radius:6px;padding:16px;margin-bottom:24px;">
    <div style="font-size:11px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">Executive Summary</div>
    <p style="margin:0;font-size:14px;line-height:1.6;color:{TEXT};">{report.get('week_summary','')}</p>
  </div>

  <!-- Top Priority Banner -->
  <div style="background:{SURFACE};border:1px solid {ACCENT};border-radius:6px;padding:14px 16px;margin-bottom:24px;">
    <span style="font-size:11px;font-weight:700;color:{ACCENT};text-transform:uppercase;letter-spacing:.07em;">⚡ TOP PRIORITY THIS WEEK</span>
    <p style="margin:6px 0 0;font-size:13px;color:{TEXT};">{report.get('top_priority','')}</p>
  </div>

  <!-- National Benchmarks -->
  <div style="margin-bottom:24px;">
    <div style="font-size:13px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">National Benchmarks (FRED)</div>
    <table style="width:100%;border-collapse:collapse;background:{CARD};border-radius:6px;overflow:hidden;">
      <tr>{fred_cells}</tr>
    </table>
  </div>

  <!-- Subject Banks -->
  {subject_table}

  <!-- Peer Tables -->
  {peer_tables}

  <!-- AI Analysis Cards -->
  <div style="margin-bottom:24px;">
    <div style="font-size:13px;font-weight:600;color:{ACCENT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;">Regional Analysis & Recommendations</div>
    {analysis_cards}
  </div>

  <!-- Risk + Next Watch -->
  <div style="display:flex;gap:16px;margin-bottom:24px;">
    <div style="flex:1;background:{CARD};border-radius:6px;padding:16px;">
      <div style="font-size:11px;font-weight:600;color:{TEXT2};text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;">Risk Assessment</div>
      <div style="margin-bottom:6px;">{_risk_badge(risk_level)}</div>
      <p style="margin:0;font-size:12px;color:{TEXT2};">{report.get('risk_rationale','')}</p>
    </div>
    <div style="flex:1;background:{CARD};border-radius:6px;padding:16px;">
      <div style="font-size:11px;font-weight:600;color:{TEXT2};text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;">Watch Next Week</div>
      <p style="margin:0;font-size:12px;color:{TEXT};">{report.get('next_watch','')}</p>
    </div>
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


def send_email(html_body, to_email, from_email, week_date=None, excel_path=None, html_path=None, pdf_path=None):
    if week_date is None:
        week_date = datetime.now().strftime("%b %d, %Y")

    safe_date = week_date.replace(" ", "_").replace(",", "")
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"DepositIQ — Popular Bank Rate Intelligence — {week_date}"
    msg["From"] = f"DepositIQ <{GMAIL_USER}>"
    msg["To"] = to_email

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
        server.sendmail(GMAIL_USER, to_email, msg.as_string())

    print(f"Email sent to {to_email}")
    return 200
