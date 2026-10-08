#!/usr/bin/env python3
"""Step 1 mechanical checks on data/rows/*.csv (report only; never edits)."""
import csv, glob, re, collections
for f in sorted(glob.glob('data/rows/*.csv')):
    rows = list(csv.DictReader(open(f, encoding='utf-8')))
    code = f.split('/')[-1][:-4]
    nos = [int(r['no']) for r in rows]
    c = collections.Counter(nos)
    dup = [n for n, k in c.items() if k > 1]
    exp = range(min(nos), max(nos) + 1)
    miss = [n for n in exp if n not in c]
    order = [n for a, n in zip(nos, nos[1:]) if n != a + 1]
    print(f"== {code} rows={len(rows)} No={min(nos)}..{max(nos)} dup={dup} missing={miss} nonseq_after={[a for a,b in zip(nos,nos[1:]) if b!=a+1]}")
    for r in rows:
        n, a, k, cm = r['no'], r['answer'], r['kokushi'], r['comment']
        issues = []
        if not a or not re.fullmatch(r'([a-e]|\d)(,([a-e]|\d))*(?:,?[a-e\d])*', a): issues.append(f'answer={a!r} raw?')
        if r['origin'] == 'kokushi' and not re.fullmatch(r'\d{3}[A-I]\d{1,3}(-\d{1,3})?', k): issues.append(f'kokushi={k!r}')
        if r['comment_note']: issues.append('note:' + r['comment_note'])
        if not cm.strip(): issues.append('comment空')
        if re.search(r'(^|\n)\s*\d{1,2}\s*[a-e]\s*[0-9]{3}[A-I]', cm): issues.append('連結疑い(次問の行が混入)')
        if len(cm) > 220: issues.append(f'長文{len(cm)}字')
        if issues and issues != ['comment空']: print(f"  No{n}: " + '; '.join(issues))
    empty = [int(r['no']) for r in rows if not r['comment'].strip()]
    print(f"  comment空 {len(empty)}件: {empty}")
