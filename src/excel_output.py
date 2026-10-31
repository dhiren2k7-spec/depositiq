import os
import zipfile
import io
from datetime import datetime

PRODUCTS = ["checking_apy", "savings", "mma", "cd_3mo", "cd_6mo", "cd_12mo", "cd_24mo"]
LABELS   = ["Checking APY", "Savings", "MMA", "3-Mo CD", "6-Mo CD", "12-Mo CD", "24-Mo CD"]

def _pct(v):
    return f"{v:.2f}%" if v is not None else "N/A"

def build_excel(config, report, fred_data, week_date):
    out_dir = os.path.join(os.path.dirname(__file__), "../output")
    os.makedirs(out_dir, exist_ok=True)
    safe_date = week_date.replace(" ", "_").replace(",", "")
    path = os.path.join(out_dir, f"DepositIQ_PopularBank_{safe_date}.xlsx")

    wb = _Workbook()

    _add_subject_sheet(wb, config["subject_banks"], week_date)

    group_order = [
        ("ny_metro",      "NY Metro"),
        ("south_florida", "South Florida"),
        ("direct_online", "Direct Online"),
    ]
    pb_rates  = config["subject_banks"][0]["rates"]
    pd_rates  = config["subject_banks"][1]["rates"]

    for gk, sheet_name in group_order:
        grp = config["peer_groups"].get(gk, {})
        peers = grp.get("peers_with_rates", grp.get("banks", []))
        subj_rates = pd_rates if gk == "direct_online" else pb_rates
        subj_name  = "Popular Direct" if gk == "direct_online" else "Popular Bank"
        _add_peer_sheet(wb, sheet_name, peers, subj_rates, subj_name)

    _add_analysis_sheet(wb, report, fred_data, week_date)

    pb_cd_tiers = config["subject_banks"][0].get("cd_tiers")
    if pb_cd_tiers:
        _add_cd_tier_sheet(wb, pb_cd_tiers)

    wb.save(path)
    return path


def _add_subject_sheet(wb, subject_banks, week_date):
    ws = wb.add_sheet("Subject Banks")
    ws.write_row(0, ["DepositIQ — Popular Bank", "Date:", week_date], bold=True)
    ws.write_row(2, ["Institution"] + LABELS, bold=True, bg="4472C4", fg="FFFFFF")
    for r, sb in enumerate(subject_banks, start=3):
        row = [sb["display_name"]] + [_pct(sb["rates"].get(p)) for p in PRODUCTS]
        ws.write_row(r, row)


def _add_peer_sheet(wb, sheet_name, peers, subj_rates, subj_name):
    ws = wb.add_sheet(sheet_name)
    ws.write_row(0, ["Institution"] + LABELS, bold=True, bg="4472C4", fg="FFFFFF")
    for r, peer in enumerate(peers, start=1):
        rates = peer.get("rates", {})
        row = [peer["name"]]
        for p in PRODUCTS:
            pv = rates.get(p)
            row.append(_pct(pv))
        ws.write_row(r, row)
    subj_row = [f"★ {subj_name}"] + [_pct(subj_rates.get(p)) for p in PRODUCTS]
    ws.write_row(len(peers) + 1, subj_row, bold=True, bg="FB923C", fg="000000")


def _add_analysis_sheet(wb, report, fred_data, week_date):
    ws = wb.add_sheet("Rate Analysis")
    r = 0
    ws.write_row(r, ["DepositIQ Rate Analysis", week_date], bold=True); r += 2

    ws.write_row(r, ["EXECUTIVE SUMMARY"], bold=True, bg="1C2128", fg="FB923C"); r += 1
    ws.write_row(r, [report.get("week_summary", "")]); r += 2

    ws.write_row(r, ["TOP PRIORITY"], bold=True, bg="1C2128", fg="FB923C"); r += 1
    ws.write_row(r, [report.get("top_priority", "")]); r += 2

    for key, label in [
        ("ny_metro_analysis",      "NY Metro Analysis"),
        ("south_florida_analysis", "South Florida Analysis"),
        ("direct_online_analysis", "Direct / Online Analysis"),
    ]:
        ana = report.get(key, {})
        ws.write_row(r, [label], bold=True, bg="1C2128", fg="FB923C"); r += 1
        ws.write_row(r, ["Position:", ana.get("position", "")]); r += 1
        ws.write_row(r, ["Recommendation:", ana.get("recommendation", "")]); r += 1
        for g in ana.get("gaps", []):
            ws.write_row(r, ["  Gap:", g]); r += 1
        r += 1

    ws.write_row(r, ["RISK LEVEL:", report.get("risk_level",""), report.get("risk_rationale","")], bold=True); r += 2
    ws.write_row(r, ["WATCH NEXT WEEK"], bold=True); r += 1
    ws.write_row(r, [report.get("next_watch","")]); r += 2

    ws.write_row(r, ["NATIONAL BENCHMARKS (FRED)"], bold=True); r += 1
    fred_map = {"FEDFUNDS":"Fed Funds","MMNRNNS":"Nat'l MMA","CD3NAX":"3-Mo CD","CD6NAX":"6-Mo CD","CD1NAX":"12-Mo CD"}
    for sid, lbl in fred_map.items():
        ws.write_row(r, [lbl, _pct(fred_data.get(sid))]); r += 1


def _add_cd_tier_sheet(wb, cd_tiers):
    ws = wb.add_sheet("CD Rate Sheet")
    tiers = cd_tiers["tiers"]
    tenors = cd_tiers["tenors"]

    # Header row 0: tier labels spanning Rate/APY pairs
    hdr = ["Tenor"]
    for t in tiers:
        hdr.extend([t, ""])
    ws.write_row(0, hdr, bold=True, bg="4472C4", fg="FFFFFF")

    # Sub-header row 1: Rate / APY under each tier
    sub = [""]
    for _ in tiers:
        sub.extend(["Rate", "APY"])
    ws.write_row(1, sub, bold=True, bg="1C2128", fg="FB923C")

    # Data rows
    for r, (tenor, tier_vals) in enumerate(tenors.items(), start=2):
        row = [tenor]
        for v in tier_vals:
            row.extend([f"{v['rate']:.2f}%", f"{v['apy']:.2f}%"])
        ws.write_row(r, row)


class _Cell:
    def __init__(self, value, bold=False, bg=None, fg=None):
        self.value = value
        self.bold  = bold
        self.bg    = bg
        self.fg    = fg


class _Sheet:
    def __init__(self, name):
        self.name = name
        self.rows = {}

    def write_row(self, row_idx, values, bold=False, bg=None, fg=None):
        self.rows[row_idx] = [_Cell(v, bold=bold, bg=bg, fg=fg) for v in values]


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


class _Workbook:
    def __init__(self):
        self.sheets = []

    def add_sheet(self, name):
        ws = _Sheet(name)
        self.sheets.append(ws)
        return ws

    def save(self, path):
        # Build shared strings table
        shared_strings = []
        ss_index = {}

        def shared(s):
            s = str(s)
            if s not in ss_index:
                ss_index[s] = len(shared_strings)
                shared_strings.append(s)
            return ss_index[s]

        # Pre-pass to populate shared strings
        for ws in self.sheets:
            for r_idx in sorted(ws.rows.keys()):
                for cell in ws.rows[r_idx]:
                    shared(cell.value)

        # Build worksheet XML parts
        sheet_xmls = []
        for idx, ws in enumerate(self.sheets):
            sid = idx + 1
            rows_xml = ""
            for r_idx in sorted(ws.rows.keys()):
                cells = ws.rows[r_idx]
                row_xml = f'<row r="{r_idx + 1}">'
                for c_idx, cell in enumerate(cells):
                    col_letter = chr(ord("A") + c_idx)
                    cell_ref = f"{col_letter}{r_idx + 1}"
                    si = shared(cell.value)
                    row_xml += f'<c r="{cell_ref}" t="s"><v>{si}</v></c>'
                row_xml += "</row>"
                rows_xml += row_xml

            sheet_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                f'<sheetData>{rows_xml}</sheetData>'
                "</worksheet>"
            )
            sheet_xmls.append((sid, ws.name, sheet_xml))

        # Shared strings XML
        ss_items = "".join(f"<si><t>{_esc(s)}</t></si>" for s in shared_strings)
        ss_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            f' count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">'
            f"{ss_items}</sst>"
        )

        # Workbook XML
        sheet_tags = "".join(
            f'<sheet name="{_esc(n)}" sheetId="{sid}" r:id="rId{sid}"/>'
            for sid, n, _ in sheet_xmls
        )
        wb_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{sheet_tags}</sheets></workbook>"
        )

        # Workbook relationships
        rels = [
            f'<Relationship Id="rId{sid}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{sid}.xml"/>'
            for sid, _, _ in sheet_xmls
        ]
        rels.append(
            '<Relationship Id="rIdSS" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
            'Target="sharedStrings.xml"/>'
        )
        wb_rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(rels)
            + "</Relationships>"
        )

        # Content types
        ct_overrides = (
            '<Override PartName="/xl/workbook.xml"'
            ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml"'
            ' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        )
        for sid, _, _ in sheet_xmls:
            ct_overrides += (
                f'<Override PartName="/xl/worksheets/sheet{sid}.xml"'
                f' ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            )
        ct_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f"{ct_overrides}</Types>"
        )

        # Top-level relationships
        top_rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1"'
            ' Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"'
            ' Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

        # Write using Python's zipfile (produces valid ZIP/OOXML)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", ct_xml)
            zf.writestr("_rels/.rels", top_rels_xml)
            zf.writestr("xl/workbook.xml", wb_xml)
            zf.writestr("xl/_rels/workbook.xml.rels", wb_rels_xml)
            zf.writestr("xl/sharedStrings.xml", ss_xml)
            for sid, _, sheet_xml in sheet_xmls:
                zf.writestr(f"xl/worksheets/sheet{sid}.xml", sheet_xml)
