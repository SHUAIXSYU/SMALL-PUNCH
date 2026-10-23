"""Read an XLSX ZIP/XML package without Excel, recalculation, or source writes.

All recovered source content is written only to the caller-supplied private folder.
"""
import argparse
import datetime as dt
import hashlib
import json
import posixpath
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

NS = {
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def text_runs(node):
    return "".join(x.text or "" for x in node.findall(".//x:t", NS))

def rels(zipfile, member):
    root = ET.fromstring(zipfile.read(member))
    return {x.attrib["Id"]: x.attrib for x in root.findall("p:Relationship", NS)}

def destination(base, target):
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(posixpath.dirname(base), target))

def parse_chart(zipfile, path):
    chart = ET.fromstring(zipfile.read(path))
    series = []
    for node in chart.findall(".//c:ser", NS):
        item = {}
        for key, sub in (("title", "c:tx"), ("x", "c:xVal"), ("y", "c:yVal"),
                         ("category", "c:cat"), ("value", "c:val")):
            part = node.find(sub, NS)
            if part is not None:
                item[key] = {"formulae": [x.text for x in part.findall(".//c:f", NS)],
                             "cached_values": [x.text for x in part.findall(".//c:pt/c:v", NS)]}
        series.append(item)
    return {"path": path, "chart_types": [x.tag.split("}")[-1] for x in chart.findall(".//c:plotArea/*", NS)
                                          if x.tag.split("}")[-1].endswith("Chart")],
            "series": series,
            "title_text": [x.text for x in chart.findall(".//c:title//a:t", NS)],
            "axis_titles": [x.text for x in chart.findall(".//c:ax//c:title//a:t", NS)]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--private-output", required=True)
    args = parser.parse_args()
    source = Path(args.source).resolve()
    output = Path(args.private_output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    before = sha(source)
    with ZipFile(source) as z:
        members = z.namelist()
        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        workbook_rels = rels(z, "xl/_rels/workbook.xml.rels")
        shared = []
        if "xl/sharedStrings.xml" in members:
            strings = ET.fromstring(z.read("xl/sharedStrings.xml"))
            shared = [text_runs(si) for si in strings.findall("x:si", NS)]
        styles = ET.fromstring(z.read("xl/styles.xml"))
        custom_formats = {int(x.attrib["numFmtId"]): x.attrib.get("formatCode")
                          for x in styles.findall(".//x:numFmts/x:numFmt", NS)}
        xfs = [dict(x.attrib) for x in styles.findall(".//x:cellXfs/x:xf", NS)]
        sheet_info = []
        raw_sheets = {}
        all_charts = []
        for sheet in workbook.findall(".//x:sheets/x:sheet", NS):
            name = sheet.attrib["name"]
            rid = sheet.attrib["{%s}id" % NS["r"]]
            path = destination("xl/workbook.xml", workbook_rels[rid]["Target"])
            root = ET.fromstring(z.read(path))
            dimension = root.find("x:dimension", NS)
            rows = []
            cells = []
            for row in root.findall(".//x:sheetData/x:row", NS):
                rows.append({"row": int(row.attrib["r"]), "hidden": row.attrib.get("hidden") == "1",
                             "height": row.attrib.get("ht"), "outline_level": row.attrib.get("outlineLevel")})
                for c in row.findall("x:c", NS):
                    kind = c.attrib.get("t", "n")
                    value_node = c.find("x:v", NS)
                    formula_node = c.find("x:f", NS)
                    inline = c.find("x:is", NS)
                    raw = value_node.text if value_node is not None else None
                    decoded = shared[int(raw)] if kind == "s" and raw is not None else (text_runs(inline) if kind == "inlineStr" and inline is not None else raw)
                    style_id = int(c.attrib.get("s", "0"))
                    cells.append({"ref": c.attrib["r"], "type": kind, "style": style_id,
                                  "num_format_id": xfs[style_id].get("numFmtId") if style_id < len(xfs) else None,
                                  "raw_v": raw, "value": decoded,
                                  "formula": formula_node.text if formula_node is not None else None,
                                  "formula_attributes": dict(formula_node.attrib) if formula_node is not None else None})
            cols = [dict(x.attrib) for x in root.findall(".//x:cols/x:col", NS)]
            merged = [x.attrib["ref"] for x in root.findall(".//x:mergeCells/x:mergeCell", NS)]
            drawing_rids = [x.attrib["{%s}id" % NS["r"]] for x in root.findall("x:drawing", NS)]
            sheet_rels_path = posixpath.join(posixpath.dirname(path), "_rels", posixpath.basename(path) + ".rels")
            sheet_rels = rels(z, sheet_rels_path) if sheet_rels_path in members else {}
            for drid in drawing_rids:
                drawing_path = destination(path, sheet_rels[drid]["Target"])
                drawing_rels_path = posixpath.join(posixpath.dirname(drawing_path), "_rels", posixpath.basename(drawing_path) + ".rels")
                drawing_rels = rels(z, drawing_rels_path) if drawing_rels_path in members else {}
                drawing = ET.fromstring(z.read(drawing_path))
                for chart_ref in drawing.findall(".//c:chart", NS):
                    chart_rid = chart_ref.attrib["{%s}id" % NS["r"]]
                    chart_path = destination(drawing_path, drawing_rels[chart_rid]["Target"])
                    all_charts.append({"sheet": name, **parse_chart(z, chart_path)})
            raw_sheets[name] = {"path": path, "cells": cells, "rows": rows, "cols": cols,
                                "merged": merged, "dimension": dimension.attrib.get("ref") if dimension is not None else None}
            sheet_info.append({"name": name, "sheet_id": sheet.attrib["sheetId"],
                               "state": sheet.attrib.get("state", "visible"), "path": path,
                               "dimension": raw_sheets[name]["dimension"], "cell_count": len(cells),
                               "formula_count": sum(c["formula"] is not None for c in cells),
                               "hidden_rows": [r["row"] for r in rows if r["hidden"]],
                               "hidden_columns": [c for c in cols if c.get("hidden") == "1"],
                               "merged": merged})
        names = [{"name": x.attrib.get("name"), "localSheetId": x.attrib.get("localSheetId"), "text": x.text}
                 for x in workbook.findall(".//x:definedNames/x:definedName", NS)]
        connections = [x for x in members if "externalLink" in x or "connections" in x or "vbaProject" in x]
        audit = {"observed_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
                 "source_path": str(source), "source_sha256_before": before,
                 "zip_members": members, "sheets": sheet_info, "defined_names": names,
                 "charts": all_charts, "custom_number_formats": custom_formats,
                 "external_or_macro_members": connections,
                 "calculation_properties": [dict(x.attrib) for x in workbook.findall("x:calcPr", NS)],
                 "raw_cells_file": "xlsx_cells_full.json",
                 "status": "STRUCTURAL_AUDIT_COMPLETE_SEMANTICS_PENDING"}
        (output / "xlsx_cells_full.json").write_text(json.dumps(raw_sheets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    after = sha(source)
    audit["source_sha256_after"] = after
    audit["source_unchanged"] = before == after
    (output / "xlsx_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sheet_count": len(sheet_info), "sheet_cells": [(x["name"], x["cell_count"], x["formula_count"]) for x in sheet_info],
                      "chart_count": len(all_charts), "source_unchanged": before == after,
                      "status": audit["status"]}, ensure_ascii=False))

if __name__ == "__main__":
    main()
