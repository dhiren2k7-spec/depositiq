"""
Generates a standalone HTML "workbook" — a tabbed page that mirrors
the six Excel sheets: Subject Banks, NY Metro, South Florida,
Popular Direct, Rate Analysis, CD Rate Sheet.
"""

from datetime import datetime

PB_BLUE  = "#003087"
PB_RED   = "#CC0000"
ACCENT   = "#fb923c"
BG       = "#f4f6f9"
CARD     = "#ffffff"
BORDER   = "#d0d7de"
TEXT     = "#1a1a2e"
TEXT2    = "#4a5568"
GREEN    = "#16a34a"
RED_C    = "#dc2626"
FONT     = "IBM Plex Sans, Arial, sans-serif"
MONO     = "JetBrains Mono, Courier New, monospace"

PRODUCTS = ["checking_apy", "savings", "mma", "cd_3mo", "cd_6mo", "cd_12mo", "cd_24mo"]
LABELS   = ["Checking", "Savings", "MMA", "3-Mo CD", "6-Mo CD", "12-Mo CD", "24-Mo CD"]

DO_PRODUCTS = ["checking_apy", "savings", "mma",
               "cd_3mo", "cd_6mo", "cd_9mo",
               "cd_12mo", "cd_18mo", "cd_24mo",
               "cd_36mo", "cd_48mo", "cd_60mo"]
DO_LABELS   = ["Checking", "Savings", "MMA",
               "3Mo", "6Mo", "9Mo",
               "12Mo", "18Mo", "24Mo",
               "3Yr", "4Yr", "5Yr"]


def _pct(v):
    if v is None:
        return "—"
    return f"{v:.2f}%"


def _rate_color(val, compare):
    if val is None or compare is None:
        return TEXT2
    diff = val - compare
    if diff >= 0.10:
        return GREEN
    if diff <= -0.10:
        return RED_C
    return TEXT


def _th(label, align="right"):
    return (f'<th style="padding:8px 10px;text-align:{align};'
            f'background:{PB_BLUE};color:#fff;font-size:13px;'
            f'font-weight:600;white-space:nowrap;">{label}</th>')


def _td(val, mono=True, color=TEXT, bold=False):
    fw = "700" if bold else "400"
    ff = MONO if mono else FONT
    return (f'<td style="padding:7px 10px;text-align:right;'
            f'font-family:{ff};font-size:13px;color:{color};'
            f'font-weight:{fw};white-space:nowrap;">{val}</td>')


def _td_left(val, bold=False, color=TEXT, bg=None):
    bg_css = f"background:{bg};" if bg else ""
    fw = "700" if bold else "400"
    return (f'<td style="padding:7px 10px;text-align:left;'
            f'font-family:{FONT};font-size:13px;color:{color};'
            f'font-weight:{fw};{bg_css}">{val}</td>')


def _section_header(title):
    return (f'<tr><td colspan="20" style="padding:10px 10px 4px;'
            f'font-family:{FONT};font-size:11px;font-weight:700;'
            f'letter-spacing:.08em;text-transform:uppercase;'
            f'color:{ACCENT};background:{BG};">{title}</td></tr>')


def _table_wrap(inner_html):
    return (f'<div style="overflow-x:auto;margin-bottom:24px;">'
            f'<table style="border-collapse:collapse;width:100%;'
            f'min-width:600px;background:{CARD};border:1px solid {BORDER};">'
            f'{inner_html}</table></div>')


# ── Sheet 1: Subject Banks ─────────────────────────────────────────────────
def _subject_sheet(config, week_date):
    subject_banks = config.get("subject_banks", [])
    headers = "".join([_th("Institution", "left")] + [_th(l) for l in LABELS])
    rows = ""
    for sb in subject_banks:
        name = sb.get("display_name", sb.get("name", ""))
        cells = _td_left(name, bold=True)
        for p in PRODUCTS:
            cells += _td(_pct(sb.get("rates", {}).get(p)))
        rows += f'<tr style="border-bottom:1px solid {BORDER};">{cells}</tr>'

    inner = (f'<thead><tr>{headers}</tr></thead>'
             f'<tbody>{rows}</tbody>')
    return _table_wrap(inner)


# ── Sheet 2/3: Peer group (NY Metro / South Florida) ──────────────────────
def _peer_sheet(peers, subj_rates, subj_name):
    headers = "".join([_th("Institution", "left")] + [_th(l) for l in LABELS])
    rows = ""
    for peer in peers:
        r = peer.get("rates", {})
        cells = _td_left(peer.get("name", ""))
        for p in PRODUCTS:
            pv = r.get(p)
            color = _rate_color(subj_rates.get(p), pv) if pv is not None else TEXT2
            cells += _td(_pct(pv), color=color)
        rows += f'<tr style="border-bottom:1px solid {BORDER};">{cells}</tr>'

    # Subject bank highlighted row
    scells = _td_left(f"★ {subj_name}", bold=True, color="#000", bg=ACCENT)
    for p in PRODUCTS:
        scells += _td(_pct(subj_rates.get(p)), bold=True, color="#000")
    rows += f'<tr style="border-bottom:2px solid {PB_BLUE};">{scells}</tr>'

    inner = (f'<thead><tr>{headers}</tr></thead>'
             f'<tbody>{rows}</tbody>')
    return _table_wrap(inner)


# ── Sheet 4: Popular Direct (extended tenors) ──────────────────────────────
def _direct_sheet(peers, pd_rates):
    headers = "".join([_th("Institution", "left")] + [_th(l) for l in DO_LABELS])
    rows = ""
    for peer in peers:
        r = peer.get("rates", {})
        cells = _td_left(peer.get("name", ""))
        for p in DO_PRODUCTS:
            pv = r.get(p)
            color = _rate_color(pd_rates.get(p), pv) if pv is not None else TEXT2
            cells += _td(_pct(pv), color=color)
        rows += f'<tr style="border-bottom:1px solid {BORDER};">{cells}</tr>'

    scells = _td_left("★ Popular Direct", bold=True, color="#000", bg=ACCENT)
    for p in DO_PRODUCTS:
        scells += _td(_pct(pd_rates.get(p)), bold=True, color="#000")
    rows += f'<tr style="border-bottom:2px solid {PB_BLUE};">{scells}</tr>'

    inner = (f'<thead><tr>{headers}</tr></thead>'
             f'<tbody>{rows}</tbody>')
    return _table_wrap(inner)


# ── Sheet 5: Rate Analysis ─────────────────────────────────────────────────
def _analysis_sheet(report, fred_data):
    def card(title, body, color=PB_BLUE):
        return (f'<div style="background:{CARD};border:1px solid {BORDER};'
                f'border-left:4px solid {color};border-radius:6px;'
                f'padding:16px 18px;margin-bottom:16px;">'
                f'<div style="font-family:{FONT};font-size:11px;font-weight:700;'
                f'letter-spacing:.08em;text-transform:uppercase;color:{color};">{title}</div>'
                f'<div style="font-family:{FONT};font-size:14px;color:{TEXT};'
                f'line-height:1.6;margin-top:8px;">{body}</div></div>')

    def analysis_card(label, ana, color=ACCENT):
        pos = ana.get("position", "—")
        rec = ana.get("recommendation", "—")
        items = ana.get("gaps", []) or ana.get("takeaways", [])
        bullets = "".join(
            f'<li style="margin-top:4px;">{g}</li>' for g in (items or [])
        )
        body = (f'<b>Position:</b> {pos}<br>'
                f'<b>Recommendation:</b> {rec}'
                + (f'<ul style="margin:8px 0 0 16px;padding:0;">{bullets}</ul>' if bullets else ""))
        return card(label, body, color)

    fred_map = {
        "FEDFUNDS": "Fed Funds Rate",
        "MMNRNNS":  "National MMA",
        "CD3NAX":   "3-Mo CD (Nat'l)",
        "CD6NAX":   "6-Mo CD (Nat'l)",
        "CD1NAX":   "12-Mo CD (Nat'l)",
    }
    fred_rows = "".join(
        f'<tr style="border-bottom:1px solid {BORDER};">'
        f'{_td_left(lbl)}'
        f'{_td(_pct(fred_data.get(sid)), color=PB_BLUE, bold=True)}'
        f'</tr>'
        for sid, lbl in fred_map.items()
    )
    fred_table = _table_wrap(
        f'<thead><tr>{_th("Benchmark", "left")}{_th("Rate")}</tr></thead>'
        f'<tbody>{fred_rows}</tbody>'
    )

    risk = report.get("risk_level", "—")
    risk_color = RED_C if risk == "HIGH" else (ACCENT if risk == "MEDIUM" else GREEN)

    html = ""
    html += card("Executive Summary", report.get("week_summary", "—"))
    html += card("Top Priority", report.get("top_priority", "—"), PB_RED)
    html += analysis_card("NY Metro Analysis", report.get("ny_metro_analysis", {}))
    html += analysis_card("South Florida Analysis", report.get("south_florida_analysis", {}))
    html += analysis_card("Popular Direct — Key Takeaways", report.get("direct_online_analysis", {}))
    html += card("Watch Next Week", report.get("next_watch", "—"))
    html += card(
        f'Risk Level: <span style="color:{risk_color};">{risk}</span>',
        report.get("risk_rationale", "—")
    )
    html += f'<h3 style="font-family:{FONT};font-size:13px;font-weight:700;color:{PB_BLUE};margin:24px 0 8px;">National Benchmarks (FRED)</h3>'
    html += fred_table
    return html


# ── Sheet 6: CD Rate Sheet ─────────────────────────────────────────────────
def _cd_tier_sheet(cd_tiers):
    if not cd_tiers:
        return '<p style="color:{TEXT2};font-family:{FONT};">No CD tier data available.</p>'

    tiers  = cd_tiers.get("tiers", [])
    tenors = cd_tiers.get("tenors", {})

    tier_headers = "".join(
        f'<th colspan="2" style="padding:8px 10px;text-align:center;'
        f'background:{PB_BLUE};color:#fff;font-size:13px;font-weight:600;'
        f'border-left:2px solid rgba(255,255,255,.2);">{t}</th>'
        for t in tiers
    )
    sub_headers = "".join(
        '<th style="padding:6px 8px;text-align:right;background:#1C2128;'
        f'color:{ACCENT};font-size:12px;">Rate</th>'
        '<th style="padding:6px 8px;text-align:right;background:#1C2128;'
        f'color:{ACCENT};font-size:12px;">APY</th>'
        for _ in tiers
    )

    rows = ""
    for tenor, tier_vals in tenors.items():
        cells = _td_left(tenor, bold=True)
        for v in tier_vals:
            cells += _td(f"{v['rate']:.2f}%", color=TEXT2)
            cells += _td(f"{v['apy']:.2f}%", color=PB_BLUE, bold=True)
        rows += f'<tr style="border-bottom:1px solid {BORDER};">{cells}</tr>'

    inner = (f'<thead>'
             f'<tr>{_th("Tenor", "left")}{tier_headers}</tr>'
             f'<tr><td style="background:#1C2128;"></td>{sub_headers}</tr>'
             f'</thead>'
             f'<tbody>{rows}</tbody>')
    return _table_wrap(inner)


# ── Main builder ───────────────────────────────────────────────────────────
def build_html_workbook(config, report, fred_data, week_date):
    subject_banks = config.get("subject_banks", [])
    pb_rates = subject_banks[0].get("rates", {}) if len(subject_banks) > 0 else {}
    pd_rates = subject_banks[1].get("rates", {}) if len(subject_banks) > 1 else {}

    peer_groups = config.get("peer_groups", {})

    def get_peers(gk):
        grp = peer_groups.get(gk, {})
        return grp.get("peers_with_rates", grp.get("banks", []))

    ny_peers  = get_peers("ny_metro")
    sfl_peers = get_peers("south_florida")
    do_peers  = get_peers("direct_online")

    cd_tiers = subject_banks[0].get("cd_tiers") if subject_banks else None

    tabs = [
        ("subject",   "Subject Banks"),
        ("ny",        "NY Metro"),
        ("sfl",       "South Florida"),
        ("direct",    "Popular Direct"),
        ("analysis",  "Rate Analysis"),
        ("cdtier",    "CD Rate Sheet"),
    ]

    tab_buttons = ""
    for tid, tlabel in tabs:
        tab_buttons += (
            f'<button onclick="showTab(\'{tid}\')" id="btn-{tid}" '
            f'style="padding:8px 18px;border:none;cursor:pointer;'
            f'font-family:{FONT};font-size:13px;font-weight:600;'
            f'border-bottom:3px solid transparent;background:transparent;'
            f'color:{TEXT2};" '
            f'data-active="false">{tlabel}</button>'
        )

    tab_contents = {
        "subject":  _subject_sheet(config, week_date),
        "ny":       _peer_sheet(ny_peers, pb_rates, "Popular Bank"),
        "sfl":      _peer_sheet(sfl_peers, pb_rates, "Popular Bank"),
        "direct":   _direct_sheet(do_peers, pd_rates),
        "analysis": _analysis_sheet(report, fred_data),
        "cdtier":   _cd_tier_sheet(cd_tiers),
    }

    panes = ""
    for tid, _ in tabs:
        panes += (
            f'<div id="tab-{tid}" class="tab-pane" '
            f'style="display:none;padding:20px 0;">'
            f'{tab_contents[tid]}</div>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DepositIQ — {week_date}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:{BG};color:{TEXT};font-family:{FONT};min-height:100vh;}}
@media print{{
  @page{{size:A4 landscape;margin:10mm;}}
  .no-print{{display:none!important;}}
  .tab-pane{{display:block!important;page-break-before:always;}}
  .tab-pane:first-of-type{{page-break-before:avoid;}}
}}
</style>
</head>
<body>
<div style="background:{PB_BLUE};color:#fff;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;">
  <div>
    <div style="font-size:20px;font-weight:700;letter-spacing:-.01em;">DepositIQ — Rate Intelligence</div>
    <div style="font-size:12px;opacity:.75;margin-top:2px;">Popular Bank · {week_date}</div>
  </div>
  <div style="font-size:11px;opacity:.6;text-align:right;">Weekly Competitive Rate Report</div>
</div>

<div class="no-print" style="background:{CARD};border-bottom:1px solid {BORDER};padding:0 28px;display:flex;gap:4px;overflow-x:auto;">
  {tab_buttons}
</div>

<div style="padding:0 28px 40px;">
  {panes}
</div>

<script>
function showTab(id) {{
  document.querySelectorAll('.tab-pane').forEach(p => p.style.display='none');
  document.querySelectorAll('button[data-active]').forEach(b => {{
    b.style.color='{TEXT2}';
    b.style.borderBottomColor='transparent';
    b.dataset.active='false';
  }});
  document.getElementById('tab-'+id).style.display='block';
  var btn=document.getElementById('btn-'+id);
  btn.style.color='{PB_BLUE}';
  btn.style.borderBottomColor='{ACCENT}';
  btn.dataset.active='true';
}}
showTab('subject');
</script>
</body>
</html>"""

    return html
