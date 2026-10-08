#!/usr/bin/env python3
"""Step 1: PDF -> data/rows/{code}.csv  (+ data/depts.json, extraction diagnostics).

Comment text is kept exactly as extracted (layout line breaks kept as '\\n').
Run:  .venv/bin/python scripts/extract.py            (only new/changed PDFs)
"""
import csv, hashlib, json, re, sys, unicodedata
from pathlib import Path
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
INPUT, ROWS, DEPTS = ROOT / "input", ROOT / "data/rows", ROOT / "data/depts.json"

# Approved by user (code proposals accepted as recommended). Keyed by filename.
KNOWN = {
    "循環器内科2026正解と解説.pdf": ("循環器内科", "CV"),
    "脳神経内科2026正解と解説.pdf": ("脳神経内科", "NE"),
    "腎臓内科2026正解と解説.pdf": ("腎臓内科", "NP"),
    "血液内科2026正解と解説.pdf": ("血液内科", "HE"),
    "呼吸器内科2026正解と解説.pdf": ("呼吸器内科", "RE"),
    "小児科2026正解と解説.pdf": ("小児科", "PD"),
    "アレ膠2026正解と解説.pdf": ("アレルギー・膠原病内科", "AR"),
    "呼吸器外科2026正解と解説.pdf": ("呼吸器外科", "RS"),
    "消化器内科2026正解と解説.pdf": ("消化器内科", "GI"),
    "消化器外科2026正解と解説.pdf": ("消化器外科", "GS"),
    "糖尿病代謝内科2026解答と解説.pdf": ("糖尿病・代謝・内分泌内科", "DM"),
    "感染症科2026正解と解説.pdf": ("感染症科", "ID"),
    "乳腺外科2026正解と解説.pdf": ("乳腺外科", "BR"),
    "医療倫理・医療文書 正解と解説.pdf": ("医療倫理・医療文書", "EM"),
}
# byte-identical re-issues the user said to ignore (confirmed 確認1)
IGNORED_DUPLICATES = {
    "アレ膠2026正解と解説 2.pdf": "アレ膠2026正解と解説.pdf",
    "乳腺外科2026正解と解説 2.pdf": "乳腺外科2026正解と解説.pdf",
    "医療倫理・医療文書 正解と解説 2.pdf": "医療倫理・医療文書 正解と解説.pdf",
}
COLS = ["dept", "no", "answer", "kokushi", "origin", "comment", "comment_note",
        "kokushi_raw", "origin_raw", "src_flag", "accuracy", "prev_year", "category", "standard"]


def md5(p):
    return hashlib.md5(p.read_bytes()).hexdigest()


def norm_answer(s):
    s = unicodedata.normalize("NFKC", s or "").lower()
    parts = re.findall(r"[a-z]+", s) if not re.search(r"\d", s) else re.findall(r"\d+", s)
    return ",".join(parts)


def norm_kokushi(raw):
    """returns (kokushi, origin, flags) ; flags: list of modified/similar/important/qb:.../also:..."""
    raw0 = (raw or "").strip()
    s = re.sub(r"\s+", "", unicodedata.normalize("NFKC", raw0))
    flags = []
    if s in ("オリジナル", "オリジナル問題", "新規", "創作問題"):
        return "", "original", flags
    if s in ("不明", ""):
        return "", "unknown", flags
    if s == "過去問アレンジ":
        return "", "unknown", ["arranged"]
    if s == "重要問題":
        return "", "unknown", ["important"]
    m = re.match(r"^第?(\d{2,3})回?[-]?([A-Ia-i])[-]?(\d{1,3})(?:[-~](\d{1,3}))?(.*)$", s)
    if not m:
        return "", "unknown", [f"UNPARSED:{raw0}"]
    k = f"{m.group(1)}{m.group(2).upper()}{m.group(3)}" + (f"-{m.group(4)}" if m.group(4) else "")
    rest = m.group(5)
    if "改変" in rest or rest.startswith("改"): flags.append("modified"); rest = rest.replace("改変", "").lstrip("改")
    if "類題" in rest: flags.append("similar"); rest = rest.replace("類題", "")
    q = re.search(r"\(QB[^)]*\)", rest)
    if q: flags.append("qb:" + q.group(0)[1:-1]); rest = rest.replace(q.group(0), "")
    others = re.findall(r"(\d{2,3})[-]?([A-I])[-]?(\d{1,3})(?:[-~]\d{1,3})?", rest)
    if others:
        flags.append("also:" + "|".join(f"{a}{b}{c}" for a, b, c in others)); rest = ""
    rest = rest.strip(",、")
    if rest: flags.append(f"UNPARSED:{rest}")
    return k, "kokushi", flags


def fix_header_garble(t):
    return t


def extract_table_pdf(path, dept):
    rows, anomalies, colmap = [], [], None
    with pdfplumber.open(path) as pdf:
        for pi, page in enumerate(pdf.pages, 1):
            for tbl in page.extract_tables():
                for r in tbl:
                    cells = [(c or "") for c in r]
                    first = cells[0].strip()
                    if first in ("No", "問題"):
                        colmap = {}
                        for i, c in enumerate(cells):
                            if c.startswith("正解"): colmap["answer"] = i
                            elif "国試" in c: colmap["kokushi"] = i
                            elif c.startswith("コメント"): colmap["comment"] = i
                        colmap["no"] = 0
                        continue
                    if not any(c.strip() for c in cells):
                        continue
                    if colmap is None:
                        anomalies.append(f"p{pi}: header前の行 {cells!r}")
                        continue
                    if first == "" and rows and cells[colmap["answer"]].strip():
                        # No cell lost by table detection: recover from text layer (same y as kokushi cell)
                        guess = rows[-1]["no"] + 1
                        rows.append(dict(no=guess, answer_raw=cells[colmap["answer"]], kokushi_raw=cells[colmap["kokushi"]],
                                         comment=cells[colmap["comment"]], page=pi,
                                         note=f"No欄が表抽出で欠落。直前+1={guess}と補完(テキスト層で確認要)"))
                        continue
                    if not re.fullmatch(r"\d+", first):
                        anomalies.append(f"p{pi}: No列が数字でない行 {cells!r}")
                        continue
                    ans, kok, note = cells[colmap["answer"]], cells[colmap["kokushi"]], ""
                    cm = cells[colmap["comment"]]
                    ov = re.fullmatch(r"([^\s\d]{1,2})\s+(\S{2,4})", cells[-1]) if len(cells) > colmap["comment"] + 1 else None
                    if ov:   # comment text overflowed into the next (担当者) column
                        cells = cells[:-1] + [ov.group(2)]
                        cells[colmap["comment"]] = cm + ov.group(1)
                        note = f"コメント末尾の{ov.group(1)!r}が隣の担当者列に溢れていたため復元"
                    m = re.fullmatch(r"\s*([a-eａ-ｅ][a-eａ-ｅ,\s、，]*?)\s+(\d{2,3}\s*[A-Ia-iＡ-Ｉ]\s*\d+.*)", ans, re.S) if not kok.strip() else None
                    if m:
                        ans, kok = m.group(1), m.group(2)
                        note = "正解と国試番号が同一セルに結合していたため分割(元セル: " + cells[colmap["answer"]] + ")"
                    rows.append(dict(
                        no=int(first), answer_raw=ans, kokushi_raw=kok, comment=cells[colmap["comment"]], page=pi, note=note))
    return rows, anomalies


def extract_em(path):
    """医療倫理: no table lines -> split words by x position."""
    out, anomalies = [], []
    with pdfplumber.open(path) as pdf:
        for pi, page in enumerate(pdf.pages, 1):
            words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
            starts = sorted([w for w in words if w["x0"] < 80 and re.fullmatch(r"問\d+", w["text"])],
                            key=lambda w: w["top"])
            for i, s in enumerate(starts):
                top = s["top"] - 2
                bot = starts[i + 1]["top"] - 2 if i + 1 < len(starts) else page.height
                blk = [c for c in page.chars if top <= c["top"] < bot]
                def col(x0, x1):
                    cs = sorted([c for c in blk if x0 <= c["x0"] < x1 and c["text"].strip()],
                                key=lambda c: (round(c["top"] / 3), c["x0"]))
                    lines, cur, y = [], "", None
                    for c in cs:
                        if y is None or abs(c["top"] - y) > 3:
                            if cur: lines.append(cur)
                            cur, y = "", c["top"]
                        cur += c["text"]
                    if cur: lines.append(cur)
                    return lines
                out.append(dict(
                    no=int(s["text"][1:]), kokushi_raw="".join(col(80, 112)), answer_raw="".join(col(112, 127)),
                    accuracy="".join(col(127, 150)), category="".join(col(150, 205)),
                    standard=" ".join(col(205, 372)), comment="\n".join(col(372, 575)),
                    prev_year="".join(col(575, 900)), page=pi))
    return out, anomalies


def extract_breast(path):
    """乳腺外科: answer list table on p1, comments (some questions only) as text on p2."""
    rows, anomalies, comments = [], [], {}
    with pdfplumber.open(path) as pdf:
        for t in pdf.pages[0].extract_tables():
            for r in t:
                c = [(x or "").strip() for x in r]
                if re.fullmatch(r"\d+", c[0]):
                    rows.append(dict(no=int(c[0]), kokushi_raw=c[1], answer_raw=c[2], comment="", page=1))
        txt = "\n".join((p.extract_text() or "") for p in pdf.pages[1:])
    zen = str.maketrans("０１２３４５６７８９", "0123456789")
    parts = re.split(r"(?m)^問題\s*([０-９0-9]+)\s*[：:]\s*", txt)
    head = parts[0].strip()
    if head != "【解説】":
        anomalies.append(f"解説の先頭テキストが想定外: {head!r}")
    for i in range(1, len(parts), 2):
        comments[int(parts[i].translate(zen))] = parts[i + 1].strip()
    for r in rows:
        r["comment"] = comments.pop(r["no"], "")
    for k in comments:
        anomalies.append(f"解説にあるが正解一覧にない問題番号: {k}")
    return rows, anomalies


def build_rows(path, dept):
    if dept == "医療倫理・医療文書":
        raw, an = extract_em(path)
    elif dept == "乳腺外科":
        raw, an = extract_breast(path)
    else:
        raw, an = extract_table_pdf(path, dept)
    out = []
    for r in raw:
        k, origin, flags = norm_kokushi(r["kokushi_raw"])
        out.append({
            "dept": dept, "no": r["no"], "answer": norm_answer(r["answer_raw"]), "kokushi": k,
            "origin": origin, "comment": r["comment"], "comment_note": r.get("note", ""), "src_flag": ";".join(flags),
            "kokushi_raw": r["kokushi_raw"].replace("\n", ""),
            "origin_raw": r["kokushi_raw"].replace("\n", "") if origin != "kokushi" else "",
            "accuracy": r.get("accuracy", ""), "prev_year": r.get("prev_year", ""),
            "category": r.get("category", ""), "standard": r.get("standard", ""),
        })
    return out, an


def main():
    ROWS.mkdir(parents=True, exist_ok=True)
    depts = json.loads(DEPTS.read_text()) if DEPTS.exists() else {}
    for pdf in sorted(INPUT.glob("*.pdf")):
        name = pdf.name
        if name in IGNORED_DUPLICATES:
            assert md5(pdf) == md5(INPUT / IGNORED_DUPLICATES[name]), f"{name} is not identical"
            continue
        if name not in KNOWN:
            print(f"!! 未承認のPDF（停止して確認）: {name}"); continue
        dept, code = KNOWN[name]
        h = md5(pdf)
        if depts.get(code, {}).get("md5") == h:
            continue
        rows, anomalies = build_rows(pdf, dept)
        with open(ROWS / f"{code}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
        depts[code] = {"dept": dept, "code": code, "pdf": name, "md5": h,
                       "ignored_duplicates": [k for k, v in IGNORED_DUPLICATES.items() if v == name]}
        print(f"{code} {dept}: {len(rows)} rows" + (f"  anomalies={len(anomalies)}" if anomalies else ""))
        for a in anomalies: print("   ", a)
    DEPTS.write_text(json.dumps(depts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
