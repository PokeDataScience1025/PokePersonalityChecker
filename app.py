import streamlit as st
import plotly.graph_objects as go
import numpy as np
import json
import os
import random
import time
import uuid
import requests

# ==============================================================================
# 0-1. SNS/note埋め込み用のOGPメタタグをHTMLに差し込む
#      Streamlitは<head>を直接編集するAPIがないため、
#      配布されているindex.html自体に一度だけ書き込む方式をとる。
#      (アプリ起動のたびに実行されるが、st.cache_resourceで1プロセスにつき1回だけ実行される)
# ==============================================================================
@st.cache_resource
def _inject_ogp_meta_tags():
    try:
        import streamlit as _st_pkg
        index_path = os.path.join(os.path.dirname(_st_pkg.__file__), "static", "index.html")
        app_url = "https://pokemon-personality-checker.streamlit.app/"
        ogp_image_url = app_url.rstrip("/") + "/app/static/ogp.png"
        meta_tags = f"""
    <meta property="og:title" content="ポケモン性格診断" />
    <meta property="og:description" content="30の質問に答えると、あなたに一番近いポケモンがわかる性格診断です。" />
    <meta property="og:image" content="{ogp_image_url}" />
    <meta property="og:url" content="{app_url}" />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="twitter:title" content="ポケモン性格診断" />
    <meta name="twitter:description" content="30の質問に答えると、あなたに一番近いポケモンがわかる性格診断です。" />
    <meta name="twitter:image" content="{ogp_image_url}" />
    <meta name="description" content="30の質問に答えると、あなたに一番近いポケモンがわかる性格診断です。" />
    """
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        if "og:title" not in html:
            html = html.replace("<head>", "<head>" + meta_tags, 1)
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(html)
    except Exception:
        pass  # メタタグの挿入に失敗してもアプリ自体は問題なく動く
    return True

_inject_ogp_meta_tags()

# ==============================================================================
# 0. 画面基本設定 & デザイン
# ==============================================================================
st.set_page_config(page_title="ポケモン性格診断", page_icon="🐾", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;500;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'M PLUS Rounded 1c', 'Hiragino Maru Gothic ProN', sans-serif; }

    .stApp {
        background: radial-gradient(circle at 10% 0%, #FFF6D8 0%, #FFF0F0 45%, #EAF3FF 100%);
    }
    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 700px; }
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}

    h1 { font-size: clamp(1.6rem, 5.5vw, 2.3rem) !important; font-weight: 800 !important; text-align: center; }
    h2, h3 { font-weight: 800 !important; }

    @keyframes bounce { 0%,100%{transform: translateY(0);} 50%{transform: translateY(-8px);} }
    .bounce { display:inline-block; animation: bounce 1.6s ease-in-out infinite; }

    div.stButton > button {
        width: 100%; min-height: 3.3rem; padding: 0.6rem 1rem;
        font-size: 1.05rem; font-weight: 700; border-radius: 16px;
        border: none; margin-bottom: 0.55rem; transition: all 0.15s ease;
        box-shadow: 0 3px 0 rgba(0,0,0,0.08);
    }
    div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 5px 0 rgba(0,0,0,0.1); }
    div.stButton > button:active { transform: translateY(1px); box-shadow: 0 1px 0 rgba(0,0,0,0.08); }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #FF5B5B 0%, #FF3B3B 100%); color: white;
    }

    .hero {
        background: linear-gradient(135deg, #FFE8A3 0%, #FFD1DC 100%);
        border-radius: 26px; padding: 1.8rem 1.5rem; text-align: center;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08); margin-bottom: 1.3rem;
        color: #5a2030;
    }
    .hero h1 { color: #5a2030 !important; }
    .hero .chips { margin-top: 0.9rem; }
    .chip {
        display: inline-block; background: rgba(255,255,255,0.75); border-radius: 999px;
        padding: 0.35rem 0.9rem; margin: 0.2rem; font-size: 0.85rem; font-weight: 700; color:#a15;
    }

    .progress-wrap { background:#fff; border-radius: 999px; height: 14px; overflow:hidden; margin: 0.4rem 0 1rem 0; box-shadow: inset 0 1px 3px rgba(0,0,0,0.12);}
    .progress-bar { height:100%; background: linear-gradient(90deg,#FFCB05,#FF5B5B); border-radius:999px; transition: width 0.3s ease; }

    .battle-vs { text-align:center; font-weight:800; color:#999; margin: 0.5rem 0; letter-spacing: 2px; }
    .side-a, .side-b {
        border-radius:18px; padding:1rem 1.1rem; margin-bottom:0.7rem; color:#333;
    }
    .side-a { background: linear-gradient(135deg,#FFE3E3,#FFC9C9); }
    .side-b { background: linear-gradient(135deg,#DCEBFF,#C7DFFF); }
    .side-label { font-weight:700; font-size:1.02rem; line-height:1.5; margin-bottom:0.6rem; text-align:center; color:#333;}
    .ab-badge {
        display:inline-block; width:1.6rem; height:1.6rem; line-height:1.6rem;
        border-radius:50%; color:#fff; font-weight:800; text-align:center; margin-right:0.3rem;
    }
    .ab-badge-a { background:#E53935; }
    .ab-badge-b { background:#1E6FE0; }

    /* 回答ボタンの色分け: 左列=Aに近い(赤系)、右列=Bに近い(青系)。
       強さ(とても/やや)は type="primary"かどうかで判定する。
       st.columns()が生成する column要素を列番号で直接指定するため、
       前回までの兄弟セレクタ方式より確実に効く。Streamlitのバージョン差異に備えて
       data-testidが "column" のものと "stColumn" のもの、両方に効くようにしている。 */
    div[data-testid="column"]:nth-of-type(1) div.stButton button,
    div[data-testid="stColumn"]:nth-of-type(1) div.stButton button {
        background: #FFE1DE !important; color: #B71C1C !important;
    }
    div[data-testid="column"]:nth-of-type(1) div.stButton button[kind="primary"],
    div[data-testid="stColumn"]:nth-of-type(1) div.stButton button[kind="primary"] {
        background: linear-gradient(135deg,#FF8A80,#E53935) !important; color:#fff !important;
    }
    div[data-testid="column"]:nth-of-type(2) div.stButton button,
    div[data-testid="stColumn"]:nth-of-type(2) div.stButton button {
        background: #DCEBFF !important; color: #0D47A1 !important;
    }
    div[data-testid="column"]:nth-of-type(2) div.stButton button[kind="primary"],
    div[data-testid="stColumn"]:nth-of-type(2) div.stButton button[kind="primary"] {
        background: linear-gradient(135deg,#64B5F6,#1E6FE0) !important; color:#fff !important;
    }

    .result-card {
        background: linear-gradient(160deg, #FFF7E0 0%, #FFE9EC 100%);
        border-radius: 26px; padding: 1.8rem 1.5rem; text-align: center;
        box-shadow: 0 6px 22px rgba(0,0,0,0.09); margin-bottom: 1.2rem;
        border: 3px solid #fff; color: #5a2030;
    }
    .result-card h2 { color: #5a2030 !important; }
    .result-card img { max-width: min(280px, 78vw); border-radius: 18px; box-shadow: 0 4px 14px rgba(0,0,0,0.15); }
    .sync-badge {
        display:inline-block; margin-top:0.8rem; background:#fff; color:#FF3B3B;
        font-weight:800; padding: 0.4rem 1.1rem; border-radius: 999px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .sub-card { background:#fff; border-radius:18px; padding:1.15rem 1.3rem; margin-bottom:1rem; box-shadow: 0 2px 10px rgba(0,0,0,0.05); color:#333; }
    .personality-line { font-size:1.05rem; font-weight:700; color:#a13; text-align:center; }

    .runner-up { text-align:center; padding:0.7rem; background:#fafafa; border-radius:14px; color:#333; }
    .runner-up img { width:100%; max-width:120px; border-radius:12px; }

    /* st.container(border=True)やexpanderなど、Streamlitのネイティブ要素の見出し・本文の
       文字色も明示しておく(config.tomlのテーマ固定と合わせた二重対策)。 */
    div[data-testid="stExpander"] summary, div[data-testid="stExpander"] p,
    div[data-testid="stVerticalBlockBorderWrapper"] p, div[data-testid="stVerticalBlockBorderWrapper"] b,
    .stMarkdown, .stMarkdown p, .stMarkdown b {
        color: #333 !important;
    }
    .stCaption, [data-testid="stCaptionContainer"] { color: #666 !important; }
    label, .stTextArea textarea { color: #333 !important; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. データ定義: 6軸 x 30問
# ==============================================================================
AXES = ["kindness", "sociability_vs_independence", "curiosity_openness",
        "boldness", "passion_vs_calm", "conscientiousness"]

AXIS_LABEL = {
    "kindness": "🩷 優しさ・思いやり",
    "sociability_vs_independence": "🤝 社交性⇔自立性",
    "curiosity_openness": "🔍 好奇心・開放性",
    "boldness": "🔥 勇敢さ・行動力",
    "passion_vs_calm": "💥 情熱⇔冷静",
    "conscientiousness": "📐 誠実さ・几帳面さ",
}

AXIS_PHRASE = {
    "kindness": {"high": "誰かのために動ける、根っからの優しさを持つタイプ",
                 "low": "感情に流されず、物事を冷静に判断できるタイプ"},
    "sociability_vs_independence": {"high": "仲間と一緒にいるとパワーが出る、みんな大好きタイプ",
                                     "low": "自分のペースを大事にする、しっかり者の一匹狼タイプ"},
    "curiosity_openness": {"high": "新しいことにワクワクが止まらない、冒険好きタイプ",
                            "low": "好きな場所・やり方をとことん極める、こだわりタイプ"},
    "boldness": {"high": "ピンチのときほど燃える、頼れる勇者タイプ",
                 "low": "石橋を叩いて渡る、慎重で堅実なタイプ"},
    "passion_vs_calm": {"high": "気持ちがすぐ表に出る、情熱あふれるタイプ",
                         "low": "どんなときも動じない、冷静沈着タイプ"},
    "conscientiousness": {"high": "コツコツ積み重ねができる、几帳面タイプ",
                           "low": "勢いと直感で動く、自由なタイプ"},
}

QUESTIONS = [
    {"a": "困っている人を見るとほうっておけない", "b": "まずは自分のことを優先する",
     "effects": {"kindness": 1.0, "sociability_vs_independence": 0.3}},
    {"a": "友達が落ち込んでいたら、自分のことのように心配する", "b": "深入りせず、そっと距離をとる",
     "effects": {"kindness": 1.0, "passion_vs_calm": 0.2}},
    {"a": "誰かのために自分の時間を使うのは苦じゃない", "b": "自分の時間は自分のために使いたい",
     "effects": {"kindness": 1.0, "sociability_vs_independence": 0.3}},
    {"a": "勝負ごとでも、弱っている相手には手加減したくなる", "b": "勝負ごとは手加減せず全力でいく",
     "effects": {"kindness": 1.0, "boldness": -0.2}},
    {"a": "人の気持ちの変化によく気づくほうだ", "b": "人の気持ちより物事の結果を重視する",
     "effects": {"kindness": 1.0, "conscientiousness": 0.2}},

    {"a": "みんなでワイワイ過ごす時間が好き", "b": "一人で静かに過ごす時間が好き",
     "effects": {"sociability_vs_independence": 1.0, "kindness": 0.3}},
    {"a": "何をするにも仲間と一緒がいい", "b": "一人で自由に動くほうが性に合う",
     "effects": {"sociability_vs_independence": 1.0, "curiosity_openness": -0.1}},
    {"a": "初対面の人ともすぐ打ち解けられる", "b": "知らない相手には最初、警戒してしまう",
     "effects": {"sociability_vs_independence": 1.0, "boldness": 0.2}},
    {"a": "チームの輪を大事にしたい", "b": "自分のペースを乱されたくない",
     "effects": {"sociability_vs_independence": 1.0, "conscientiousness": -0.1}},
    {"a": "縄張りやテリトリーにあまりこだわらない", "b": "自分の場所や持ち物には強いこだわりがある",
     "effects": {"sociability_vs_independence": 1.0, "kindness": 0.2}},

    {"a": "知らない場所に行くとワクワクする", "b": "慣れた場所にいるのが一番落ち着く",
     "effects": {"curiosity_openness": 1.0, "boldness": 0.3}},
    {"a": "新しいものはすぐ試してみたくなる", "b": "使い慣れたものをずっと使い続けたい",
     "effects": {"curiosity_openness": 1.0, "conscientiousness": -0.2}},
    {"a": "予定が急に変わってもワクワクする方だ", "b": "決まった予定通りに進むと安心する",
     "effects": {"curiosity_openness": 1.0, "conscientiousness": -0.3}},
    {"a": "知らないことはすぐ調べたくなる", "b": "知らないことは知らないままでも気にならない",
     "effects": {"curiosity_openness": 1.0, "passion_vs_calm": 0.1}},
    {"a": "いつもと違うやり方を試したくなる", "b": "いつも同じやり方が一番うまくいくと思う",
     "effects": {"curiosity_openness": 1.0, "conscientiousness": -0.2}},

    {"a": "強い相手ほど、燃えてくる", "b": "強い相手には近づかないようにする",
     "effects": {"boldness": 1.0, "passion_vs_calm": 0.3}},
    {"a": "危険があっても、まず動いてみる", "b": "危険があるなら、様子を見てから動く",
     "effects": {"boldness": 1.0, "curiosity_openness": 0.2}},
    {"a": "注目される場面でも物おじしない", "b": "注目されるとつい緊張してしまう",
     "effects": {"boldness": 1.0, "passion_vs_calm": 0.2}},
    {"a": "やられたら、やり返さないと気がすまない", "b": "争いごとはできるだけ避けたい",
     "effects": {"boldness": 1.0, "kindness": -0.2}},
    {"a": "ピンチのときほど頼りになると言われる", "b": "ピンチのときは誰かに頼りたくなる",
     "effects": {"boldness": 1.0, "sociability_vs_independence": -0.1}},

    {"a": "感情がすぐ顔や態度に出る", "b": "感情はあまり表に出さない",
     "effects": {"passion_vs_calm": 1.0, "boldness": 0.2}},
    {"a": "熱くなると周りが見えなくなることがある", "b": "どんなときも一歩引いて冷静でいられる",
     "effects": {"passion_vs_calm": 1.0, "conscientiousness": -0.2}},
    {"a": "好きなことには全力で夢中になる", "b": "好きなことでも、どこか一歩引いて楽しむ",
     "effects": {"passion_vs_calm": 1.0, "curiosity_openness": 0.1}},
    {"a": "怒るときは思いきり怒る", "b": "腹が立ってもあまり顔に出さない",
     "effects": {"passion_vs_calm": 1.0, "kindness": -0.1}},
    {"a": "テンションの上がり下がりが激しい方だ", "b": "いつも同じくらいのテンションでいる",
     "effects": {"passion_vs_calm": 1.0, "conscientiousness": -0.1}},

    {"a": "毎日同じ時間に同じことをするのが落ち着く", "b": "日によって過ごし方が変わる方が楽しい",
     "effects": {"conscientiousness": 1.0, "curiosity_openness": -0.2}},
    {"a": "物の置き場所や順番をきっちり決めている", "b": "物の場所は特に決めずその都度置く",
     "effects": {"conscientiousness": 1.0, "passion_vs_calm": -0.1}},
    {"a": "一度決めたルールは最後まで守りたい", "b": "状況に応じてルールは変えてもいいと思う",
     "effects": {"conscientiousness": 1.0, "curiosity_openness": -0.1}},
    {"a": "コツコツ準備してから物事に取りかかる", "b": "勢いに任せてまず取りかかる",
     "effects": {"conscientiousness": 1.0, "boldness": -0.2}},
    {"a": "忘れ物や遅刻はほとんどしない", "b": "うっかり忘れ物や遅刻をしてしまうことがある",
     "effects": {"conscientiousness": 1.0}},
]

LOADING_MESSAGES = [
    "図鑑を読み込み中... 📖", "性格の波長を調べています... 📡",
    "似たタイプの仲間を探索中... 🔍", "相棒を呼び出しています... ✨",
]

# ==============================================================================
# 2. データロード
# ==============================================================================
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
VEC_PATH = os.path.join(DATA_DIR, "pokemon_trait_vectors_v2.json")
DISP_PATH = os.path.join(DATA_DIR, "pokemon_display_data.json")
EXCLUDED_PATH = os.path.join(DATA_DIR, "excluded_pokemon_full.json")

@st.cache_data
def load_excluded_pokemon():
    if not os.path.exists(EXCLUDED_PATH):
        return []
    with open(EXCLUDED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_pokemon_database():
    with open(VEC_PATH, "r", encoding="utf-8") as f:
        vectors = json.load(f)
    with open(DISP_PATH, "r", encoding="utf-8") as f:
        display = json.load(f)

    db = []
    for pid_str, v in vectors.items():
        disp = display.get(pid_str, {})
        vec = [float(v["scores"][a]) for a in AXES]
        db.append({
            "id": int(pid_str),
            "name": v.get("name_ja") or disp.get("name_ja", f"ポケモンNo.{pid_str}"),
            "vector": vec,
            "description": disp.get("description", ""),
            "image": disp.get("image_url"),
            "evidence": v.get("evidence", ""),
        })

    mat = np.array([p["vector"] for p in db])
    mean = mat.mean(axis=0)
    std = mat.std(axis=0)
    std[std == 0] = 1.0
    return db, mean, std

# 標準化空間での距離を「シンクロ度(%)」に変換するための固定基準値。
# 982匹データ・実際の質問セットでのシミュレーションから、
# 「一番近い match の中央値」がだいたい90%前後になるよう校正した固定値。
# 上位8件はどれもこの基準に対して近い距離のため、選ばれた結果と近いタイプの
# 候補とで数値が矛盾しない（=シンクロ度が逆転しない）ようにするのが狙い。
SYNC_DISTANCE_REF = 8.5

def _distance_to_sync(d):
    return max(0.0, min(100.0, 100.0 * (1 - d / SYNC_DISTANCE_REF)))

def find_match(user_vector):
    """標準化ユークリッド距離で最も近い1体を「診断結果」として確定で選ぶ(常に本当の最近傍)。
    2位・3位を「近いタイプの仲間」として表示するため、シンクロ度は
    結果 >= 仲間1 >= 仲間2 の順で必ず一貫する（逆転しない）。
    戻り値: {"chosen": dict, "sync_score": float, "runner_ups": [(dict, float), ...]} または None
    """
    db, mean, std = load_pokemon_database()
    if not db:
        return None

    u = (np.array(user_vector) - mean) / std
    dists = []
    for p in db:
        v = (np.array(p["vector"]) - mean) / std
        dists.append(float(np.linalg.norm(u - v)))

    order = np.argsort(dists)  # 距離が近い順
    ranked = [(db[i], dists[i]) for i in order]

    chosen, chosen_d = ranked[0]
    runner_ups = [(p, _distance_to_sync(d)) for p, d in ranked[1:3]]
    sync_score = _distance_to_sync(chosen_d)
    return {"chosen": chosen, "sync_score": sync_score, "runner_ups": runner_ups}

def personality_blurb(user_vector):
    deviations = [(AXES[i], abs(user_vector[i] - 50), user_vector[i]) for i in range(len(AXES))]
    deviations.sort(key=lambda x: x[1], reverse=True)
    lines = []
    for axis, _, score in deviations[:2]:
        pole = "high" if score >= 50 else "low"
        lines.append(AXIS_PHRASE[axis][pole])
    return "、それに".join(lines) + "。"

# ==============================================================================
# 3. Supabase 連携（未設定でもアプリは動く）
# ==============================================================================
def _supabase_conf():
    try:
        return st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"]
    except Exception:
        return None, None

def log_play_event(event_type, result_pokemon_id=None, sync_score=None):
    url, key = _supabase_conf()
    if not url:
        return
    try:
        requests.post(
            f"{url}/rest/v1/play_events",
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json", "Prefer": "return=minimal"},
            json={"session_id": st.session_state.get("session_id"), "event_type": event_type,
                  "result_pokemon_id": result_pokemon_id, "sync_score": sync_score},
            timeout=3,
        )
    except Exception:
        pass

def submit_feedback(message, related_pokemon_id=None):
    url, key = _supabase_conf()
    if not url:
        return False
    try:
        resp = requests.post(
            f"{url}/rest/v1/feedback",
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json", "Prefer": "return=minimal"},
            json={"message": message, "related_pokemon_id": related_pokemon_id,
                  "session_id": st.session_state.get("session_id")},
            timeout=5,
        )
        return resp.status_code < 300
    except Exception:
        return False

# ==============================================================================
# 4. データファイルの存在チェック（ここで落ちないようにする）
# ==============================================================================
missing = [p for p in (VEC_PATH, DISP_PATH) if not os.path.exists(p)]
if missing:
    st.error(
        "性格データファイルが見つかりません。以下のファイルを `app.py` と同じフォルダに置いてください。\n\n"
        + "\n".join(f"- {os.path.basename(p)}" for p in missing)
        + f"\n\napp.pyのフォルダ: `{DATA_DIR}`"
    )
    st.stop()

# ==============================================================================
# 5. アプリ状態管理
# ==============================================================================
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "phase" not in st.session_state:
    st.session_state.phase = "start"
if "shuffled_questions" not in st.session_state:
    st.session_state.shuffled_questions = []
if "result" not in st.session_state:
    st.session_state.result = None

# ==============================================================================
# 6. 画面遷移
# ==============================================================================

if st.session_state.phase == "start":
    st.markdown("""
    <div class="hero">
      <div style="font-size:3rem;" class="bounce">🐾</div>
      <h1>きみの相棒ポケモンを見つけよう！</h1>
      <p style="color:#a15; font-weight:600;">30個の質問に答えるだけで、あなたの性格タイプを分析。<br>
      約1000匹の中から<b>あなたにいちばんそっくりな1匹</b>を診断します。</p>
      <div class="chips">
        <span class="chip">📝 30問</span>
        <span class="chip">⏱ 1〜2分</span>
        <span class="chip">🐣 約1000匹から診断</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("✨ 診断をスタート！", type="primary", use_container_width=True):
        st.session_state.shuffled_questions = random.sample(QUESTIONS, len(QUESTIONS))
        st.session_state.phase = "quiz"
        st.session_state.current_q = 0
        st.session_state.answers = []
        st.session_state.result = None
        log_play_event("start")
        st.rerun()

    st.caption(
        "🔍 981種類のポケモンが結果として出現します。"
        "本当は全ポケモンを出したかったのですが、性格を示す図鑑説明文が少なかった"
        "一部のポケモンは、診断の精度を保つため対象外としました。"
    )

elif st.session_state.phase == "quiz":
    idx = st.session_state.current_q
    quiz_list = st.session_state.shuffled_questions
    total = len(quiz_list)

    if idx >= total:
        st.session_state.phase = "loading"
        st.rerun()

    pct = int(idx / total * 100)
    st.markdown(f"""
    <div class="progress-wrap"><div class="progress-bar" style="width:{pct}%;"></div></div>
    <div style="text-align:center; color:#999; font-weight:700; margin-bottom:0.6rem;">質問 {idx + 1} / {total}</div>
    """, unsafe_allow_html=True)

    q = quiz_list[idx]

    with st.container(border=True):
        st.markdown('<div style="text-align:center; color:#888; font-weight:800; margin-bottom:0.5rem;">'
                    'AとB、どちらに近い？</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="side-a"><div class="side-label">'
                    f'<span class="ab-badge ab-badge-a">A</span>{q["a"]}</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="battle-vs">V S</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="side-b"><div class="side-label">'
                    f'<span class="ab-badge ab-badge-b">B</span>{q["b"]}</div></div>', unsafe_allow_html=True)

        st.markdown('<div style="text-align:center; color:#999; font-weight:700; margin: 0.9rem 0 0.5rem 0;">'
                    '👇 この中から一番近いものを1つだけ選んでね</div>', unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("とてもAに近い！", key=f"va_{idx}", type="primary", use_container_width=True):
                st.session_state.answers.append({"effects": q["effects"], "weight": 1.0})
                st.session_state.current_q += 1
                st.rerun()
            if st.button("ややAに近いかな", key=f"sa_{idx}", use_container_width=True):
                st.session_state.answers.append({"effects": q["effects"], "weight": 0.5})
                st.session_state.current_q += 1
                st.rerun()
        with col_b:
            if st.button("ややBに近いかな", key=f"sb_{idx}", use_container_width=True):
                st.session_state.answers.append({"effects": q["effects"], "weight": -0.5})
                st.session_state.current_q += 1
                st.rerun()
            if st.button("とてもBに近い！", key=f"vb_{idx}", type="primary", use_container_width=True):
                st.session_state.answers.append({"effects": q["effects"], "weight": -1.0})
                st.session_state.current_q += 1
                st.rerun()

    if idx > 0:
        if st.button("⬅ 前の質問に戻る", key=f"back_{idx}"):
            st.session_state.current_q -= 1
            st.session_state.answers.pop()
            st.rerun()

elif st.session_state.phase == "loading":
    st.markdown("<h3 style='text-align:center; color:#5a2030;'>あなたに一番そっくりなポケモンは...</h3>", unsafe_allow_html=True)
    ph = st.empty()
    # 軸ごとに「係数の絶対値」で重み付けした加重平均を取る。
    # 単純に件数で割ると、強い設問(係数1.0)と副次的な設問(係数0.1〜0.3)が
    # 同じ重みで平均されてしまい、スコアが50点付近に寄って0/100に届きにくくなるため。
    trait_scores = {a: 0.0 for a in AXES}
    trait_weight_sum = {a: 0.0 for a in AXES}
    for ans in st.session_state.answers:
        for trait, coef in ans["effects"].items():
            trait_scores[trait] += coef * ans["weight"]
            trait_weight_sum[trait] += abs(coef)

    user_vector = []
    for a in AXES:
        wsum = trait_weight_sum[a]
        avg = trait_scores[a] / wsum if wsum > 0 else 0.0
        avg = max(-1.0, min(1.0, avg))
        user_vector.append(50.0 + 50.0 * avg)

    for msg in LOADING_MESSAGES:
        ph.markdown(f"<div style='text-align:center; font-size:1.1rem; color:#888;'>{msg}</div>", unsafe_allow_html=True)
        time.sleep(0.5)

    match = find_match(user_vector)
    st.session_state.result = {"user_vector": user_vector, "match": match}
    if match:
        log_play_event("complete", result_pokemon_id=match["chosen"]["id"], sync_score=match["sync_score"])

    st.session_state.phase = "result"
    st.rerun()

elif st.session_state.phase == "result":
    result = st.session_state.result
    match = result["match"] if result else None

    if not match:
        st.error("診断結果を計算できませんでした。データファイルの中身をご確認ください。")
        if st.button("最初からやり直す"):
            st.session_state.phase = "start"
            st.rerun()
        st.stop()

    chosen = match["chosen"]
    sync_score = match["sync_score"]
    user_vector = result["user_vector"]

    st.markdown(f"""
    <div class="result-card">
      <div style="font-size:1rem; color:#a15; font-weight:700;">あなたに一番そっくりなポケモンは…</div>
      <h2 style="margin:0.3rem 0;">No.{chosen['id']} {chosen['name']}</h2>
      {'<img src="' + chosen['image'] + '">' if chosen.get('image') else ''}
      <div><span class="sync-badge">シンクロ度 {sync_score:.1f}%</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sub-card">
      <div class="personality-line">💡 きみは「{personality_blurb(user_vector)}」</div>
    </div>
    """, unsafe_allow_html=True)

    share_text = f"私は「{chosen['name']}」タイプでした！(シンクロ度{sync_score:.0f}%) #ポケモン性格診断"
    share_url = "https://pokemon-personality-checker.streamlit.app/"
    st.link_button(
        "🐦 診断結果をXでシェアする",
        f"https://twitter.com/intent/tweet?text={requests.utils.quote(share_text)}&url={requests.utils.quote(share_url)}",
        use_container_width=True,
    )

    if chosen.get("description"):
        st.markdown(f"""
        <div class="sub-card"><b>📖 図鑑説明文より</b><br>
        <span style="color:#555;">{chosen['description']}</span></div>
        """, unsafe_allow_html=True)

    if chosen.get("evidence"):
        with st.expander("🔍 診断のポイント"):
            st.caption(f"図鑑説明文から要約した、{chosen['name']}の性格はこちらです。")
            st.write(f"→ {chosen['evidence']}")

    if match["runner_ups"]:
        with st.container(border=True):
            st.markdown("<b style='color:#333;'>🥈 あなたと近いタイプの仲間たち</b>"
                         "<div style='color:#777; font-size:0.8rem; margin-bottom:0.6rem;'>"
                         "同じ「シンクロ度」の基準で計算した、次点候補です。</div>", unsafe_allow_html=True)
            cols = st.columns(2)
            for i, (p, sc) in enumerate(match["runner_ups"]):
                with cols[i % 2]:
                    if p.get("image"):
                        st.image(p["image"], use_container_width=True)
                    st.markdown(f"<div style='text-align:center; font-weight:700; color:#333;'>{p['name']}</div>"
                                 f"<div style='text-align:center; color:#777; font-size:0.85rem;'>シンクロ度 {sc:.0f}%</div>",
                                 unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("<b style='color:#333;'>📊 あなたの性格グラフ</b>", unsafe_allow_html=True)
        fig = go.Figure()
        labels = [AXIS_LABEL[a] for a in AXES]
        fig.add_trace(go.Scatterpolar(r=user_vector + [user_vector[0]], theta=labels + [labels[0]],
                                       fill='toself', name='あなた', line_color='#FF4B4B'))
        fig.add_trace(go.Scatterpolar(r=chosen["vector"] + [chosen["vector"][0]], theta=labels + [labels[0]],
                                       fill='toself', name=chosen["name"], line_color='#FFA500', opacity=0.5))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                           showlegend=True, margin=dict(t=20, b=20, l=20, r=20), height=380)
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("💬 ご意見・ご感想（開発者にだけ届きます）"):
        fb_text = st.text_area("感想", key="fb_text", label_visibility="collapsed", placeholder="ここに入力...")
        if st.button("送信する", key="fb_submit"):
            if fb_text.strip():
                ok = submit_feedback(fb_text.strip(), related_pokemon_id=chosen["id"])
                if ok:
                    st.success("送信しました。ありがとうございます！")
                else:
                    st.info("送信を受け付けました。")
            else:
                st.warning("内容を入力してください。")

    st.write("")
    if st.button("🔁 もう一度やってみる！", use_container_width=True):
        st.session_state.current_q = 0
        st.session_state.answers = []
        st.session_state.shuffled_questions = []
        st.session_state.result = None
        st.session_state.phase = "start"
        st.rerun()
