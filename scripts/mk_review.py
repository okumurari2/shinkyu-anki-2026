#!/usr/bin/env python3
"""Step 2: write sections 1-3 of review/{code}.md from topics + rows (later sections are appended by later steps)."""
import csv, json, glob, collections
from pathlib import Path
R = Path(__file__).resolve().parent.parent
tot = collections.Counter(); spec = collections.Counter()
for f in sorted(glob.glob(str(R/'data/topics/*.jsonl'))):
    code = Path(f).stem
    rows = {int(r['no']): r for r in csv.DictReader(open(R/f'data/rows/{code}.csv', encoding='utf-8'))}
    T = [json.loads(l) for l in open(f, encoding='utf-8')]
    dept = rows[min(rows)]['dept']
    per = collections.defaultdict(list)
    for t in T: per[t['src_no']].append(t)
    skiprows = [n for n, ts in per.items() if all(t['card_policy'] == 'skip' for t in ts)]
    out = [f'# {code} {dept}', '', '## 1. 問題冊子がないと作れない行(skipした行と理由)', '']
    out += ['| No | 国試番号 | コメント | 理由 |', '|---|---|---|---|']
    for n in sorted(per):
        for t in per[n]:
            if t['card_policy'] == 'skip':
                c = rows[n]['comment'].replace('\n', '').replace('|', '/')
                c = (c[:60] + '…') if len(c) > 60 else c
                out.append(f"| {n} | {rows[n]['kokushi'] or rows[n]['origin']} | {c or '(空)'} | {t['note']} 〔{t['topic']}〕 |")
    out += ['', '## 2. 元コメントとの差分(不整合行と、直した内容)', '']
    d = [t for t in T if 'disc' in t['flags']]
    if not d: out.append('(該当なし)')
    for t in d:
        c = rows[t['src_no']]['comment'].replace('\n', '')
        out += [f"- **No{t['src_no']}** ({t['card_policy']}) 元コメント: 「{c}」", f"  - 対応: {t['topic']} / {t['note']}"]
    out += ['', '## 3. コメントのずれが疑われる箇所', '']
    m = [t for t in T if 'misaligned' in t['flags']]
    if not m: out.append('(該当なし)')
    for t in m: out.append(f"- No{t['src_no']}: {t['note']}")
    out += ['', '## 4. 要確認カード一覧', '(Step 3以降)', '', '## 5. 独立レビューの指摘', '(Step 4)', '', '## 6. 件数サマリ', '']
    c1 = collections.Counter(t['specificity'] for t in T); c2 = collections.Counter(t['card_policy'] for t in T)
    out.append(f"- topics: {len(T)} (make {c2['make']} / skip {c2['skip']})")
    out.append(f"- specificity: high {c1['high']} / mid {c1['mid']} / low {c1['low']}")
    out.append(f"- skipのみの行: {len(skiprows)}行 / 全{len(rows)}行")
    (R/f'review/{code}.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
    print(f"{code:2} {dept[:12]:14} rows={len(rows):3} topics={len(T):3} make={c2['make']:3} skip={c2['skip']:3} | high={c1['high']:3} mid={c1['mid']:3} low={c1['low']:3} | skip-only rows={len(skiprows):2} disc={len(d)}")
    spec.update(c1); tot.update(c2)
print('TOTAL', dict(tot), dict(spec))
