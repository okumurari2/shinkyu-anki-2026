#!/usr/bin/env python3
"""Step 4 machine checks. Report only; never edits cards."""
import csv, glob, json, re, sys, collections, difflib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cardlib import *
R = Path(__file__).resolve().parent.parent
REQ = ["id","front","back","dept","dept_code","src_no","kokushi","origin","specificity","content_source","risk_flags","basis","note"]
errors, warns = collections.defaultdict(list), collections.defaultdict(list)
rows, topics, cards = {}, {}, {}
for f in sorted(glob.glob(str(R/"data/rows/*.csv"))):
    c = Path(f).stem; rows[c] = {int(r["no"]): r for r in csv.DictReader(open(f, encoding="utf-8"))}
    topics[c] = [json.loads(l) for l in open(R/f"data/topics/{c}.jsonl", encoding="utf-8")]
    cards[c] = [json.loads(l) for l in open(R/f"data/cards/{c}.jsonl", encoding="utf-8")]
allc = [(c, x) for c in cards for x in cards[c]]
# 1 schema / ids
ids = collections.Counter(x["id"] for _, x in allc)
for c, x in allc:
    miss = [k for k in REQ if k not in x]
    if miss: errors["schema"].append(f'{x.get("id")} missing {miss}')
    if not re.fullmatch(rf"{c}-\d{{2}}-[abc]", x["id"]): errors["id_format"].append(x["id"])
    if ids[x["id"]] > 1: errors["id_dup"].append(x["id"])
    if x["content_source"] not in ("comment","supplement","inferred"): errors["content_source"].append(x["id"])
    if x["specificity"] not in ("high","mid","low"): errors["specificity"].append(x["id"])
    if not x["front"].strip() or not x["back"].strip(): errors["empty"].append(x["id"])
    if len(x["front"]) > 120: warns["front_len>120"].append(f'{x["id"]}({len(x["front"])})')
    if len(x["back"]) > 140: warns["back_len>140"].append(f'{x["id"]}({len(x["back"])})')
# 2 duplicates
fr = collections.defaultdict(list)
for c, x in allc: fr[x["front"]].append(x["id"])
for k, v in fr.items():
    if len(v) > 1: errors["front_dup"].append(f'{v}: {k}')
fl = [(x["id"], re.sub(r"\s", "", x["front"]), re.sub(r"\s", "", x["back"])) for _, x in allc]
for i in range(len(fl)):
    for j in range(i + 1, len(fl)):
        a, b = fl[i], fl[j]
        if a[1] != b[1] and difflib.SequenceMatcher(None, a[1], b[1]).quick_ratio() > .9 and difflib.SequenceMatcher(None, a[1], b[1]).ratio() > .9:
            warns["front_similar"].append(f"{a[0]} ~ {b[0]}: {a[1][:40]}")
# same front text different dept but same back -> informational
# 3-6 rows linkage, basis, skip, old_exam
for c, cs in cards.items():
    mk = collections.Counter(t["src_no"] for t in topics[c] if t["card_policy"] == "make")
    got = collections.Counter(x["src_no"] for x in cs)
    for n in set(mk) | set(got):
        if mk[n] != got[n]: errors["topic_card_mismatch"].append(f"{c}-{n}: make topics {mk[n]} cards {got[n]}")
    tmap = {t["topic_id"]: t for t in topics[c]}
    for x in cs:
        r = rows[c].get(x["src_no"])
        if r is None: errors["row_missing"].append(x["id"]); continue
        t = tmap.get(x["id"])
        if t is None or t["card_policy"] != "make": errors["card_from_skip_topic"].append(x["id"])
        if x["content_source"] == "comment":
            if not x["basis"] or nfkc_ns(x["basis"]) not in nfkc_ns(r["comment"]): errors["basis_not_in_comment"].append(x["id"])
        elif x["basis"] and nfkc_ns(x["basis"]) not in nfkc_ns(r["comment"]): errors["basis_not_in_comment"].append(x["id"])
        if x["content_source"] != "comment" and "R" and not x["note"].strip(): warns["supplement_without_note"].append(x["id"])
        if (x["kokushi"], x["origin"]) != (r["kokushi"], r["origin"]): errors["kokushi_mismatch"].append(x["id"])
        y = kokushi_year(r["kokushi"])
        if y is not None and y <= 104 and "old_exam" not in x["risk_flags"]: errors["old_exam_missing"].append(x["id"])
        if "modified" in r["src_flag"].split(";") and "modified" not in x["risk_flags"]: errors["modified_missing"].append(x["id"])
        need = auto_flags(x["front"], x["back"])
        lack = need - set(x["risk_flags"])
        if lack: errors["risk_flag_missing"].append(f'{x["id"]}: {sorted(lack)}')
        t_flags = {TOPIC_FLAG_MAP[f] for f in (t or {}).get("flags", []) if f in TOPIC_FLAG_MAP}
        if t_flags - set(x["risk_flags"]): errors["topic_flag_lost"].append(x["id"])
        # answer leakage: back (>=5 chars) contained verbatim in front
        b = re.sub(r"[\s()（）、。]", "", x["back"]); f_ = re.sub(r"[\s()（）、。]", "", x["front"])
        if len(b) >= 5 and b in f_: warns["answer_in_front"].append(x["id"])
        if x["content_source"] == "comment" and x["specificity"] == "low": warns["comment_but_low"].append(x["id"])
        if c == "EM" and "accuracy" not in x: errors["em_accuracy_missing"].append(x["id"])
# skip rows must have no card
for c in cards:
    skiponly = {n for n in rows[c] if all(t["card_policy"] == "skip" for t in topics[c] if t["src_no"] == n)}
    for x in cards[c]:
        if x["src_no"] in skiponly: errors["card_on_skip_row"].append(x["id"])
# 8 incremental snapshot
snap = R/"data/build_snapshot.json"
if snap.exists():
    old = json.load(open(snap))
    for c, x in allc:
        o = old.get(x["id"])
        if o and (o["front"], o["back"]) != (x["front"], x["back"]): errors["existing_card_changed"].append(x["id"])
    for i in old:
        if i not in ids: errors["existing_card_deleted"].append(i)
else:
    warns["snapshot"].append("前回ビルドなし(初回)。Step 5で基準スナップショットを作成")
# report
tot = sum(len(v) for v in cards.values())
print(f"cards={tot} depts={len(cards)}")
print("== ERRORS ==" if errors else "== ERRORS: none ==")
for k, v in errors.items(): print(f"[{k}] {len(v)}:", *v[:12], sep="\n   ")
print("== WARNINGS ==" if warns else "== WARNINGS: none ==")
for k, v in warns.items(): print(f"[{k}] {len(v)}:", *v[:15], sep="\n   ")
dk = collections.Counter(); fc = collections.Counter(); cs_ = collections.Counter()
for c, x in allc:
    dk[(c, deck_of(x) != "要確認")] += 1
    for f in x["risk_flags"]: fc[f] += 1
    cs_[x["content_source"]] += 1
print("content_source:", dict(cs_)); print("risk_flags:", dict(fc))
print("main/review per dept:", {c: (dk[(c, True)], dk[(c, False)]) for c in cards})
json.dump({"errors": {k: v for k, v in errors.items()}, "warns": {k: v for k, v in warns.items()}}, open(R/"review/_validate.json", "w"), ensure_ascii=False, indent=1)
sys.exit(1 if errors else 0)
