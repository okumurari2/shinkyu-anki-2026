"""Shared helpers for card generation / validation / build."""
import re, unicodedata

def nfkc_ns(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", s or ""))

DRUG_KW = ["薬", "阻害", "ステロイド", "コルチコイド", "製剤", "抗菌", "ペニシリン", "セフェム", "アドレナリン", "インスリン",
           "ワルファリン", "ワーファリン", "DOAC", "ヘパリン", "ワクチン", "レチノイン", "亜ヒ酸", "ATRA", "R-CHOP", "ABVD",
           "TKI", "チロシンキナーゼ", "ベリムマブ", "ヒドロキシクロロキン", "HCQ", "メトホルミン", "ビタミンK", "ビタミンB",
           "ビタミンD", "鉄剤", "ニトログリセリン", "ドパミン", "リルゾール", "エダラボン", "rt-PA", "リドカイン", "ヌシネルセン",
           "リスジプラム", "シクロスポリン", "アシクロビル", "リツキシマブ", "メポリズマブ", "NSAID", "β遮断", "ACE", "ARB",
           "サイアザイド", "利尿", "プロトンポンプ", "核酸アナログ", "ベンゾジアゼピン", "ゲフィチニブ", "ハイドレア",
           "ヒドロキシカルバミド", "抗コリン", "ATRA", "チアゾリジン", "SGLT2", "アスピリン", "ビスホスホネート", "オマリズマブ",
           "エタネルセプト", "トシリズマブ", "ステント", "高張食塩水", "生理食塩水", "血漿交換", "化学療法", "R-CHOP", "ミコフェノール",
           "炭酸リチウム", "抗毒素", "ST合剤", "セフトリアキソン", "ドレナージ"]
DRUG_KW = [k for k in DRUG_KW if k not in ("ドレナージ", "ステント", "血漿交換")]
GENE_KW = ["遺伝", "染色体", "リピート", "顕性", "潜性", "優性", "劣性", "X連鎖", "BRCA", "PIG-A", "JAK2", "BCR", "HTT", "DMPK",
           "SMN", "フィブリリン", "ABCG2", "LDL受容体異常", "URAT1", "Philadelphia", "Ph陽性", "EGFR遺伝子", "遺伝子"]
NUM_ALLOW = re.compile(
    r"(CHADS2|BRCA[12]|IgG4|IgG|IgA|IgM|IgE|B12|B1|B6|SMN2|T1|T2|β2|Hb|PaO2|PaCO2|A-aDO2|AaDO2|SaO2|SpO2|CO2|O2|PIVKA-II|"
    r"II型|I型|III型|2型|1型|DM1|CD\d+|MEN1|HbA1c|SGLT2|H2|V[1-6]|[CTL][0-9]+|#4PD|COVID-19|JAK2|PD-L1|IL-\d+|5T|3Ps|ABCG2|"
    r"PIG-A|HER2|GLP-1|IGF-I|21水酸化酵素|第[0-9一二三]+世代|第[0-9IVX]+因子|VIII|IX|CS1|URAT1|β1|β2|β-D|Brinkman|"
    r"[0-9０-９]+(?=(主徴|原則|大原因|つ|種類|項目|要素|条件|徴|兆|段階|枝|次|軸|点|大|剤|相|型|分類|群|期|度|肢)))")

def has_number(text):
    return bool(re.search(r"[0-9０-９]", NUM_ALLOW.sub("", text)))

def auto_flags(front, back):
    t = front + back
    f = set()
    if has_number(t): f.add("numeric")
    if any(k in t for k in DRUG_KW): f.add("drug_indication")
    if any(k in t for k in GENE_KW): f.add("genetic")
    return f

TOPIC_FLAG_MAP = {"numeric": "numeric", "drug": "drug_indication", "genetic": "genetic",
                  "guideline": "guideline", "disc": "comment_discrepancy"}
FLAG_ORDER = ["numeric", "drug_indication", "genetic", "guideline", "old_exam", "modified", "comment_discrepancy"]

def kokushi_year(k):
    m = re.match(r"(\d{2,3})[A-I]", k or "")
    return int(m.group(1)) if m else None

def deck_of(card):
    """main deck iff no risk flags (content_source supplement/inferred cards flagged R by author carry 'review' in note-> see build)."""
    return "要確認" if (card["risk_flags"] or card.get("force_review")) else card["dept"]
