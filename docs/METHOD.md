# 抽出条件と作業手順

詳細な規則は [CLAUDE.md](../CLAUDE.md)(生成時の指示書の原文)にあります。ここでは要点をまとめます。

## 前提
- 元の PDF には問題文も選択肢もなく、あるのは「正解記号・国試番号・コメント 1 行」だけです。
- 正解記号は単体では情報にならないため、カードの材料は実質コメント欄だけです。
- 国試番号から過去問の本文を再構成することはしていません(捏造防止)。番号は出典タグとしてのみ使っています。
- 最優先は「国試の重要知識から逸脱しない・誤りを作らない」です。迷ったらカードを作らず、review に回します。

## 工程(各工程の区切りで人間が確認して進める)
1. **抽出**(`scripts/extract.py` → `data/rows/{code}.csv`)
   - 科名は PDF 1 行目の見出しから読み取る。略称コード(2 文字)は人間が承認する。
   - 列: `dept, no, answer, kokushi, origin, comment, comment_note`。
   - 正解記号は半角・`a,c` 形式に正規化。国試番号は `108E36` 形式に正規化。「オリジナル」「不明」は `origin=original/unknown`。
   - コメント原文は改変しない。ずれや欠落は `comment_misaligned` 候補として報告する。
2. **トピック抽出**(`data/topics/`)
   - 1 行につき 0〜3 トピック。`specificity` は high(コメントに答えそのものがある)/ mid(疾患名・論点名のみ)/ low(話題レベル、または空)。
   - コメントが空、または答えが一意に定まらない行は `skip` とし、`review/{code}.md` に理由を残す。
   - コメントに誤記・不整合がある行は、標準知識に基づく形に直して `comment_discrepancy` を付け、差分を review に記録する。
3. **カード生成**(`data/cards/`)
   - 1 トピック最大 3 枚。Basic 形式、1 カード = 1 つの 1 対 1 知識。
   - **1-hop ルール**: 許されるのは、コメントが指す知識そのものと、その直接の対比・逆向きの問いだけ。
   - `content_source`: `comment`(コメント由来)/ `supplement`(標準知識で補った)/ `inferred`(論点名から推測で補った)。
   - `comment` のカードは `basis` にコメント原文の連続部分文字列を持つ。
   - 補完カードは「教科書レベルで不変・数値や薬剤適応や遺伝子を含まない・1 行で言い切れる」を満たす場合だけ作る。
   - `risk_flags`: `numeric / drug_indication / genetic / guideline / old_exam / modified / comment_discrepancy`。
4. **検証**(`scripts/validate.py` と独立レビュー)
   - 機械チェック: スキーマ、id 重複、front 重複・類似、`basis` が rows に含まれること、skip 行からカードが作られていないこと、フラグの付け漏れ、既存カードの変更検出。
   - 独立レビュー: 生成に関与していない別のサブエージェントが、各カードを反証する立場から検査し、指摘を `review/{code}.md` の「5」に記録した。カードは自動では書き換えない。
5. **ビルド**(`scripts/build.py` → `out/shinkyu.apkg`)
   - genanki を使用。モデル ID は固定、デッキ ID は科名から、ノートの guid はカード id から決定的に生成。
   - デッキ振り分け: `risk_flags` が空かつ条件を満たすカードは `進級::{科名}`、それ以外は `進級::要確認`。
   - 生成後に .apkg を読み戻し、ノート数・デッキ別枚数・タグが cards.jsonl と一致することを確認した。

## 増分運用
- 処理済みかは `data/depts.json` の PDF md5 で判定。新規・変更された PDF だけを処理する。
- 既存科のカード(id, guid, front, back)は、明示的な指示なしに書き換えない。`data/build_snapshot.json` との比較で検出する。

## コマンド例
```
pip install -r requirements.txt
python3 scripts/extract.py     # input/ の新規 PDF だけ処理
python3 scripts/validate.py
python3 scripts/build.py
python3 scripts/coverage.py    # COVERAGE.md を更新
```

## 既知の限界
- 要確認デッキが約半数を占める(数値・薬剤・遺伝子を含むカードを厳しく分けているため)。
- 独立レビューの指摘は記録しているが、全件には対応していない。採否は `review/*.md` の「5」を参照。
- 元コメント自体が誤っている場合がある。該当は `comment_discrepancy` と `review/*.md` の「2」で確認できる。
