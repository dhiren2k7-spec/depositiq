import os
import json
import struct
import zlib
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
            sv = subj_rates.get(p)
            row.append(_pct(pv))
        ws.write_row(r, row)
    subj_row = [f"★ {subj_name}"] + [_pct(subj_rates.get(p)) for p in PRODUCTS]
    ws.write_row(len(peers) + 1, subj_row, bold=True, bg="FB923C", fg="000000")


def _add_analysis_sheet(wb, report, fred_data, week_date):
    ws = wb.add_sheet("AI Analysis")
    r = 0
    ws.write_row(r, ["DepositIQ AI Analysis", week_date], bold=True); r += 2

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


class _Workbook:
    def __init__(self):
        self.sheets = []

    def add_sheet(self, name):
        ws = _Sheet(name)
        self.sheets.append(ws)
        return ws

    def save(self, path):
        parts = {}
        rels   = []
        sheet_entries = []

        shared_strings = []
        ss_index = {}

        def shared(s):
            s = str(s)
            if s not in ss_index:
                ss_index[s] = len(shared_strings)
                shared_strings.append(s)
            return ss_index[s]

        for idx, ws in enumerate(self.sheets):
            sid = idx + 1
            rows_xml = ""
            for r_idx in sorted(ws.rows.keys()):
                cells = ws.rows[r_idx]
                row_xml = f'<row r="{r_idx+1}">'
                for c_idx, cell in enumerate(cells):
                    col_letter = chr(ord("A") + c_idx)
                    cell_ref = f"{col_letter}{r_idx+1}"
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
            parts[f"xl/worksheets/sheet{sid}.xml"] = sheet_xml.encode()
            sheet_entries.append((sid, ws.name))
            rels.append(f'<Relationship Id="rId{sid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{sid}.xml"/>')

        ss_items = "".join(f"<si><t>{_esc(s)}</t></si>" for s in shared_strings)
        ss_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">'
            f"{ss_items}</sst>"
        )
        parts["xl/sharedStrings.xml"] = ss_xml.encode()
        rels.append('<Relationship Id="rIdSS" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>')

        sheet_tags = "".join(f'<sheet name="{_esc(n)}" sheetId="{sid}" r:id="rId{sid}"/>' for sid, n in sheet_entries)
        wb_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<sheets>{sheet_tags}</sheets></workbook>"
        )
        parts["xl/workbook.xml"] = wb_xml.encode()

        wb_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + "".join(rels) + "</Relationships>"
        parts["xl/_rels/workbook.xml.rels"] = wb_rels.encode()

        ct_overrides = (
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        )
        for sid, _ in sheet_entries:
            ct_overrides += f'<Override PartName="/xl/worksheets/sheet{sid}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'

        ct_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            f"{ct_overrides}</Types>"
        )
        parts["[Content_Types].xml"] = ct_xml.encode()

        top_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        )
        parts["_rels/.rels"] = top_rels.encode()

        with open(path, "wb") as f:
            f.write(_zip(parts))


def _esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")


def _zip(files):
    buf = b""
    central = b""
    offsets = {}
    for name, data in files.items():
        compressed = zlib.compress(data)[2:-4]
        crc = zlib.crc32(data) & 0xFFFFFFFF
        nm  = name.encode()
        offsets[name] = len(buf)
        local = (
            b"PK\x03\x04"
            + struct.pack("<HHHHIIIHHH", 20, 0, 8, 0, 0, crc, len(compressed), len(data), len(nm), 0)
            + nm + compressed
        )
        buf += local
        central += (
            b"PK\x01\x02"
            + struct.pack("<HHHHHIIIHHHHHHII", 20, 20, 0, 8, 0, 0, crc, len(compressed), len(data), len(nm), 0, 0, 0, 0, 0, offsets[name])
            + nm
        )
    cd_offset = len(buf)
    cd_size   = len(central)
    n = len(files)
    eocd = (
        b"PK\x05\x06"
        + struct.pack("<HHHHIIH", 0, 0, n, n, cd_size, cd_offset, 0)
    )
    return buf + central + eocd
