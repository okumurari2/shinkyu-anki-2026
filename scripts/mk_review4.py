#!/usr/bin/env python3
"""Step 4: fill sections 4-6 of review/{code}.md (rewrites those sections) from cards + independent review outputs."""
import json, glob, re, collections
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from cardlib import deck_of
R = Path(__file__).resolve().parent.parent
ind = collections.defaultdict(list)
for f in sorted(glob.glob(str(R/'review/indep/output_*.json'))):
    for it in json.load(open(f, encoding='utf-8')): ind[it['id'].split('-')[0]].append(it)
sev = collections.Counter()
for f in sorted(glob.glob(str(R/'data/cards/*.jsonl'))):
    code = Path(f).stem
    C = [json.loads(l) for l in open(f, encoding='utf-8')]
    cm = {x['id']: x for x in C}
    md = (R/f'review/{code}.md').read_text(encoding='utf-8')
    head = md.split('## 4. 要確認カード一覧')[0]
    out = [head + '## 4. 要確認カード一覧(理由別)', '']
    byr = collections.defaultdict(list)
    for x in C:
        if deck_of(x) == '要確認':
            rs = x['risk_flags'] + ([f"content:{x['content_source']}"] if x['content_source'] != 'comment' else []) + (['author_review'] if x.get('force_review') else [])
            for r in rs: byr[r].append(x['id'])
    for r, ids in sorted(byr.items()): out.append(f"- **{r}** ({len(ids)}): {', '.join(ids)}")
    out += ['', '## 5. 独立レビューの指摘(別サブエージェントによる反証レビュー。カードは未変更)', '']
    items = sorted(ind[code], key=lambda i: ({'high': 0, 'medium': 1, 'low': 2}[i['severity']], i['id']))
    if not items: out.append('(指摘なし)')
    for i in items:
        sev[i['severity']] += 1
        out.append(f"- [{i['severity']}/{i['category']}] **{i['id']}** {cm[i['id']]['front'][:40]}… → {i['issue']} (提案: {i['suggestion']})")
    out += ['', '## 6. 件数サマリ', '']
    c = collections.Counter(x['content_source'] for x in C); s = collections.Counter(x['specificity'] for x in C)
    main = sum(1 for x in C if deck_of(x) != '要確認')
    out += [f"- cards: {len(C)} (本デッキ {main} / 要確認 {len(C)-main})", f"- content_source: {dict(c)}", f"- specificity: {dict(s)}",
            f"- 独立レビュー指摘: {len(items)}件 (high {sum(i['severity']=='high' for i in items)} / medium {sum(i['severity']=='medium' for i in items)} / low {sum(i['severity']=='low' for i in items)})"]
    (R/f'review/{code}.md').write_text('\n'.join(out) + '\n', encoding='utf-8')
print(dict(sev), sum(sev.values()))
for c, v in sorted(ind.items()): print(c, len(v), end=' | ')
