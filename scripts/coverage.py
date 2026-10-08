"""Generate COVERAGE.md from data/depts.json + data/cards. Run: python3 scripts/coverage.py"""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from cardlib import deck_of

depts = json.load(open(R / "data/depts.json", encoding="utf-8"))
# 推測した全科目枠(公式リストではない)。科名は depts.json の dept と完全一致で照合する。
EXPECTED = {
    "内科系": ["循環器内科", "呼吸器内科", "消化器内科", "腎臓内科", "血液内科", "糖尿病・代謝・内分泌内科",
              "脳神経内科", "感染症科", "アレルギー・膠原病内科", "老年内科・総合診療"],
    "外科系": ["消化器外科", "呼吸器外科", "乳腺外科", "心臓血管外科", "脳神経外科", "整形外科", "形成外科",
              "泌尿器科", "小児外科"],
    "その他臨床": ["小児科", "産婦人科", "精神科", "皮膚科", "眼科", "耳鼻咽喉科", "放射線科", "麻酔科", "救急科",
                "リハビリテーション科"],
    "基礎・社会": ["医療倫理・医療文書", "公衆衛生・法医学", "臨床検査"],
}
cnt = {}
for p in sorted((R / "data/cards").glob("*.jsonl")):
    cs = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    if cs:
        cnt[cs[0]["dept"]] = (cs[0]["dept_code"], len(cs), sum(deck_of(c) != "要確認" for c in cs))
md5 = {v["dept"]: v["md5"] for v in depts.values()}

L = ["# 科目カバレッジ", "",
     "> 「想定科目」は作者の推測であり、大学の公式一覧ではありません。実際の科目構成に合わせて `scripts/coverage.py` の `EXPECTED` を編集してください。",
     "", "| 区分 | 科名 | 状態 | コード | 全カード | 本デッキ | 要確認 | 元PDF md5 |", "|---|---|---|---|---|---|---|---|"]
def row(g, n):
    if n in cnt:
        c, t, m = cnt[n]
        return f"| {g} | {n} | ✅ 処理済 | {c} | {t} | {m} | {t - m} | `{md5.get(n, '')}` |"
    return f"| {g} | {n} | ⬜ 未着手 | | | | | |"
known = set()
for g, names in EXPECTED.items():
    for n in names:
        L.append(row(g, n)); known.add(n)
for n in cnt:
    if n not in known:
        L.append(row("(想定外)", n))
tot = sum(v[1] for v in cnt.values()); main = sum(v[2] for v in cnt.values())
L += ["", f"合計: {len(cnt)}科 / {tot}枚(本デッキ {main}、要確認 {tot - main})", ""]
(R / "COVERAGE.md").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L[-3:]))
