#!/usr/bin/env python3
"""Step 3: data/cards_src/{code}.txt + topics + rows -> data/cards/{code}.jsonl
src line: no|src(c/s/i)|key|front|back|rv(''|R)|note   -- one line per *make* topic, in topic order.
Refuses to overwrite an existing cards file unless --force."""
import csv, json, re, sys, unicodedata, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cardlib import *
R = Path(__file__).resolve().parent.parent
force = "--force" in sys.argv
for code in [a for a in sys.argv[1:] if not a.startswith("--")]:
    rows = {int(r["no"]): r for r in csv.DictReader(open(R/f"data/rows/{code}.csv", encoding="utf-8"))}
    topics = [json.loads(l) for l in open(R/f"data/topics/{code}.jsonl", encoding="utf-8")]
    makes = collections.defaultdict(list)
    for t in topics:
        if t["card_policy"] == "make": makes[t["src_no"]].append(t)
    src = collections.defaultdict(list)
    for ln, line in enumerate(open(R/f"data/cards_src/{code}.txt", encoding="utf-8"), 1):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"): continue
        p = line.split("|")
        assert len(p) == 7, f"{code}:{ln} fields={len(p)}: {line[:80]}"
        src[int(p[0])].append((ln, p))
    for n in set(makes) | set(src):
        assert len(makes.get(n, [])) == len(src.get(n, [])), f"{code} No{n}: topics(make)={len(makes.get(n,[]))} cards={len(src.get(n,[]))}"
    out, seen, errs = [], set(), []
    for n in sorted(src):
        r = rows[n]
        comment = r["comment"].replace("\n", "")
        sents = [s for s in re.split(r"(?<=[。．])", comment) if s.strip()] or [comment]
        for (ln, p), t in zip(src[n], makes[n]):
            _, s, key, front, back, rv, note = p
            assert s in "csi" and len(s) == 1, f"{code}:{ln} src"
            basis = ""
            if key.strip():
                hit = None
                for w in range(1, len(sents) + 1):          # shortest run of consecutive sentences containing the key
                    for i in range(len(sents) - w + 1):
                        if nfkc_ns(key) in nfkc_ns("".join(sents[i:i + w])):
                            hit = "".join(sents[i:i + w]); break
                    if hit: break
                if not hit:
                    print(f"{code}:{ln} key not found in No{n}: {key!r}\n    COMMENT: {comment}"); errs.append(ln); continue
                basis = hit.strip()
            else:
                assert s != "c", f"{code}:{ln} comment card needs key"
            fl = {TOPIC_FLAG_MAP[x] for x in t["flags"] if x in TOPIC_FLAG_MAP} | auto_flags(front, back)
            y = kokushi_year(r["kokushi"])
            if y is not None and y <= 104: fl.add("old_exam")
            if "modified" in r["src_flag"].split(";"): fl.add("modified")
            note_full = note
            card = {"id": t["topic_id"], "front": front, "back": back, "dept": r["dept"], "dept_code": code, "src_no": n,
                    "kokushi": r["kokushi"], "origin": r["origin"], "specificity": t["specificity"],
                    "content_source": {"c": "comment", "s": "supplement", "i": "inferred"}[s],
                    "risk_flags": [x for x in FLAG_ORDER if x in fl], "basis": basis, "note": note_full}
            if rv == "R": card["force_review"] = True
            if code == "EM":
                card["accuracy"] = r["accuracy"]; card["prev_year"] = "昨年度出題" if r["prev_year"].strip() else ""
            assert card["id"] not in seen; seen.add(card["id"]); out.append(card)
    if errs: sys.exit(f"{code}: {len(errs)} key errors")
    path = R/f"data/cards/{code}.jsonl"
    body = "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in out)
    if path.exists() and path.read_text(encoding="utf-8") != body and not force:
        sys.exit(f"{code}: cards already exist and differ; refusing to overwrite (use --force only if instructed)")
    path.write_text(body, encoding="utf-8")
    fc = collections.Counter(c["content_source"] for c in out)
    nm = sum(1 for c in out if deck_of(c) != "要確認")
    print(f"{code}: {len(out)} cards  main={nm} review={len(out)-nm}  src={dict(fc)}")
