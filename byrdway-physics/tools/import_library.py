"""Convert the owner's Video Link Library workbook into src/data/resources.json.

Run: python3 tools/import_library.py
Source of truth: sources/ByrdWay_Physics_Video_Link_Library.xlsx (Drive, 19 Oct 2026).
Every link is preserved exactly as written in the workbook; nothing is invented.
"""
import json, pathlib, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
wb = openpyxl.load_workbook(ROOT / "sources/ByrdWay_Physics_Video_Link_Library.xlsx")

def rows(name):
    ws = wb[name]
    it = ws.iter_rows()
    hdr = [c.value for c in next(it)]
    for r in it:
        if not any(c.value for c in r):
            continue
        yield {h: (c.hyperlink.target if c.hyperlink else c.value) for h, c in zip(hdr, r) if h}

def links(r):
    return {"khan": r["Khan Academy"], "oct": r["Organic Chem Tutor"], "yt": r["YouTube"]}

out = {"source": "ByrdWay_Physics_Video_Link_Library.xlsx", "built": "2026-10-19",
       "linkKind": "search", "units": [], "sections": [], "labs": [], "orientation": [],
       "engines": [], "assessment": [], "reference": [], "anchors": []}
seen = set()
for r in rows("Master Table"):
    u = int(r["Unit"])
    if u not in seen:
        seen.add(u)
        out["units"].append({"num": u, "title": r["Unit Title"], "part": r["Part"]})
    out["sections"].append({"id": str(r["Section"]), "unit": u, "topic": r["Topic"],
                            "pathway": r["Pathway"], "keywords": r["Search keywords"],
                            "note": r["Note"], "links": links(r)})
for r in rows("Signature Labs"):
    out["labs"].append({"num": int(r["#"]), "title": r["Laboratory"], "focus": r["Student investigation"],
                        "keywords": r["Search keywords"], "links": links(r)})
for sheet, key, col in [("Orientation (Sec I)", "orientation", "Power Tool Experience item"),
                        ("Learning Engines (Sec III)", "engines", "Learning engine"),
                        ("Assessment (Sec V)", "assessment", "Assessment layer"),
                        ("Reference (Sec VI)", "reference", "Student resource")]:
    for r in rows(sheet):
        out[key].append({"num": int(r["#"]), "title": r[col], "keywords": r["Search keywords"], "links": links(r)})
for r in rows("Course Anchors"):
    out["anchors"].append({"title": r["Resource"], "url": r["Link"], "use": r["Use it for"]})

rowcount = sum(len(out[k]) for k in ["sections", "labs", "orientation", "engines", "assessment", "reference"])
linkcount = rowcount * 3
assert len(out["sections"]) == 170 and len(out["units"]) == 20 and len(out["labs"]) == 20
assert rowcount == 242 and linkcount == 726, (rowcount, linkcount)
out["counts"] = {"units": 20, "sections": 170, "rows": rowcount, "links": linkcount, "anchors": len(out["anchors"])}
(ROOT / "src/data/resources.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print("ok", out["counts"])
