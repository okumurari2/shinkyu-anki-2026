"""Step 5: build out/shinkyu.apkg from data/cards/*.jsonl (all depts). Deterministic model/deck IDs and note guids."""
import json, hashlib, html, sys, collections, zipfile, sqlite3, tempfile, os
from pathlib import Path
import genanki
sys.path.insert(0, str(Path(__file__).parent))
from cardlib import deck_of

R = Path(__file__).resolve().parent.parent
def stable(s, mod=1 << 30): return int(hashlib.md5(s.encode()).hexdigest()[:8], 16) % mod + (1 << 30)

MODEL_ID = 1607392319  # fixed forever
CSS = ".card{font-family:sans-serif;font-size:20px;text-align:center}.aux{font-size:11px;color:#888;margin-top:14px}.aux summary{cursor:pointer}"
model = genanki.Model(MODEL_ID, "進級 Basic",
    fields=[{"name": n} for n in ["Front", "Back", "ID", "Src", "ContentSource", "Basis", "Flags"]],
    templates=[{"name": "Card 1", "qfmt": "{{Front}}",
        "afmt": "{{FrontSide}}<hr id=answer>{{Back}}<div class=aux><details><summary>info</summary>"
                "{{ID}} / {{Src}}<br>{{ContentSource}}<br>{{Basis}}<br>{{Flags}}</details></div>"}], css=CSS)

cards = []
for p in sorted((R/"data/cards").glob("*.jsonl")):
    cards += [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
depts = sorted({c["dept"] for c in cards})
decks = {n: genanki.Deck(stable("deck:" + n), "進級::" + n) for n in depts + ["要確認"]}
e = lambda s: html.escape(s or "")
exp = collections.Counter(); exp_tag = collections.Counter()
for c in cards:
    d = deck_of(c)
    unver = d == "要確認" or c["content_source"] in ("supplement", "inferred")
    tags = [f"dept::{c['dept']}", f"origin::{c['origin']}", f"specificity::{c['specificity']}", f"content::{c['content_source']}"]
    if unver: tags.append("unverified")
    src = f"{c['dept']} No.{c['src_no']}" + (f" {c['kokushi']}" if c["kokushi"] else "")
    note = genanki.Note(model=model, guid=hashlib.sha1(("shinkyu:" + c["id"]).encode()).hexdigest()[:10],
        fields=[e(c["front"]), e(c["back"]), c["id"], e(src), c["content_source"], e(c["basis"]), ",".join(c["risk_flags"])], tags=tags)
    decks[d].add_note(note); exp[d] += 1
    for t in tags: exp_tag[t] += 1
out = R/"out/shinkyu.apkg"; out.parent.mkdir(exist_ok=True)
genanki.Package(list(decks.values())).write_to_file(str(out))

# readback verification
with tempfile.TemporaryDirectory() as td:
    zipfile.ZipFile(out).extractall(td)
    db = next(Path(td).glob("collection.anki2*"))
    con = sqlite3.connect(db)
    ndeck = {json.loads(v)["name"]: k for k, v in [(r[0], r[1]) for r in [(k, json.dumps(x)) for k, x in json.loads(con.execute("select decks from col").fetchone()[0]).items()]]}
    n = con.execute("select count(*) from notes").fetchone()[0]
    cnt = {nm: con.execute("select count(*) from cards where did=?", (int(did),)).fetchone()[0] for nm, did in ndeck.items()}
    tg = collections.Counter(t for (s,) in con.execute("select tags from notes") for t in s.split())
ok = n == len(cards) and all(cnt.get("進級::" + k, 0) == v for k, v in exp.items()) and tg == exp_tag
print(f"notes={n} (cards.jsonl total={len(cards)})")
for k in sorted(cnt): print(f"  {k}: {cnt[k]}")
print("tags match:", tg == exp_tag, "| verify:", "OK" if ok else "NG")
if ok:  # baseline snapshot for incremental check
    json.dump({c["id"]: {"front": c["front"], "back": c["back"]} for c in cards}, open(R/"data/build_snapshot.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("snapshot written")
