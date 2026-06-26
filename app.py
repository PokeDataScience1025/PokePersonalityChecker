import streamlit as st
import plotly.graph_objects as go
import numpy as np
import json
import os
import random
import time

# ==============================================================================
# 0. 画面基本設定
# ==============================================================================
st.set_page_config(page_title="ポケモン性格診断", page_icon="🐾", layout="centered")

st.markdown("""
    <style>
    div.stButton > button {
        width: 100%;
        padding: 0.5rem 0;
        font-size: 1.2rem;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. データの定義（小学生でもわかる表現・短文・重みづけを0.1〜1.0に調整）
# ==============================================================================
QUESTIONS = [
    # --- 優しさ ---
    {
        "a": "相談にのるときは相手のきもちに味方する", 
        "b": "相談にのるときは正しいアドバイスを伝える",
        "effects": {"優しさ": 1.0, "協調性": 0.3, "穏やかさ": 0.1, "自立性": -0.3}
    },
    {
        "a": "困っている人がいたらほっとけない", 
        "b": "相手のことを考えてそっとしておいてあげる",
        "effects": {"優しさ": 1.0, "勇敢さ": 0.3, "情熱": 0.1, "穏やかさ": -0.1}
    },
    {
        "a": "意見があわないときは自分がゆずることが多い", 
        "b": "納得いかないときは自分の意見をしっかり言う",
        "effects": {"優しさ": 1.0, "協調性": 0.3, "穏やかさ": 0.1, "勇敢さ": -0.3, "自立性": -0.3}
    },
    
    # --- 協調性 ---
    {
        "a": "みんなで集まってワイワイ遊ぶのが好き", 
        "b": "ひとりで趣味に集中して過ごすのが好き",
        "effects": {"協調性": 1.0, "優しさ": 0.1, "自立性": -0.3, "マイペースさ": -0.3}
    },
    {
        "a": "外出では相手の行きたい場所に合わせる", 
        "b": "「ここに行こう！」と自分からどんどん提案する",
        "effects": {"協調性": 1.0, "穏やかさ": 0.1, "勇敢さ": -0.3, "マイペースさ": -0.1}
    },
    {
        "a": "チームみんなで一緒にやりたい", 
        "b": "自分の仕事をひとりでやる方が楽",
        "effects": {"協調性": 1.0, "誠実さ": 0.1, "自立性": -0.3}
    },
    
    # --- 好奇心 ---
    {
        "a": "はじめての体験にワクワクする", 
        "b": "お気に入りの場所で過ごすのが落ち着く",
        "effects": {"好奇心": 1.0, "勇敢さ": 0.3, "情熱": 0.1, "穏やかさ": -0.1}
    },
    {
        "a": "新しいものをすぐ調べたくなる", 
        "b": "流行りはあまり気にしない",
        "effects": {"好奇心": 1.0, "知性": 0.3, "誠実さ": 0.1}
    },
    {
        "a": "新しいことにどんどんチャレンジしたい", 
        "b": "得意なことをやり込みたい",
        "effects": {"好奇心": 1.0, "勇敢さ": 0.3, "情熱": 0.1, "マイペースさ": -0.1}
    },
    
    # --- 勇敢さ ---
    {
        "a": "むずかしい目標ほど「やってやる」と燃える", 
        "b": "あんぜんで確実な道を選びたい",
        "effects": {"勇敢さ": 1.0, "好奇心": 0.3, "情熱": 0.3, "知性": -0.1, "誠実さ": -0.1}
    },
    {
        "a": "失敗してもすぐ次にむけて立ち上がる", 
        "b": "失敗をしばらく引きずってしまう",
        "effects": {"勇敢さ": 1.0, "情熱": 0.3, "穏やかさ": -0.1}
    },
    {
        "a": "人前でもあまり緊張しない", 
        "b": "人前では緊張してドキドキする",
        "effects": {"勇敢さ": 1.0, "自立性": 0.1, "穏やかさ": 0.1}
    },
    
    # --- 穏やかさ ---
    {
        "a": "イライラすることはめったにない", 
        "b": "気持ちがすぐ顔に出やすい",
        "effects": {"穏やかさ": 1.0, "優しさ": 0.3, "協調性": 0.1, "情熱": -0.3}
    },
    {
        "a": "まわりを気にせず自分のことに集中できる", 
        "b": "にぎやかすぎる場所はつかれる",
        "effects": {"穏やかさ": 1.0, "マイペースさ": 0.3, "好奇心": -0.1}
    },
    {
        "a": "トラブルにもあわてず冷静にいられる", 
        "b": "あせったりパニックになったりしやすい",
        "effects": {"穏やかさ": 1.0, "知性": 0.1, "情熱": -0.3}
    },
    
    # --- 知性 ---
    {
        "a": "やり方や順番を考えてから動く", 
        "b": "手を動かしてやりながら考える",
        "effects": {"知性": 1.0, "誠実さ": 0.3, "好奇心": -0.1}
    },
    {
        "a": "仕組みを考えるのが好き", 
        "b": "自分のカンやセンスを信じたい",
        "effects": {"知性": 1.0, "誠実さ": 0.3, "マイペースさ": -0.3, "好奇心": -0.1}
    },
    {
        "a": "頭をつかうゲームが得意だ", 
        "b": "体をうごかす方が好き",
        "effects": {"知性": 1.0, "好奇心": 0.1, "情熱": -0.1}
    },
    
    # --- 自立性 ---
    {
        "a": "まわりの意見に流されず自分で決めたい", 
        "b": "みんなの意見をきいて決めたい",
        "effects": {"自立性": 1.0, "マイペースさ": 0.3, "勇敢さ": 0.1, "協調性": -0.3, "優しさ": -0.1}
    },
    {
        "a": "ひとりでの行動も楽しめる", 
        "b": "だれかといっしょに行動したい",
        "effects": {"自立性": 1.0, "穏やかさ": 0.1, "協調性": -0.3}
    },
    {
        "a": "ひとりの時間をとても大切にしている", 
        "b": "なんでもオープンに共有しあえる関係が好き",
        "effects": {"自立性": 1.0, "誠実さ": 0.3, "協調性": -0.3}
    },
    
    # --- 誠実さ ---
    {
        "a": "締め切りや約束の時間は、絶対にまもりたい", 
        "b": "そのときの状況にあわせて変えてもいいと思う",
        "effects": {"誠実さ": 1.0, "知性": 0.1, "マイペースさ": -0.3}
    },
    {
        "a": "まじめにコツコツ取り組む", 
        "b": "最後にいっきに終わらせる",
        "effects": {"誠実さ": 1.0, "知性": 0.3, "情熱": -0.1}
    },
    {
        "a": "お世辞やウソをつくのが苦手", 
        "b": "話を合わせたり盛り上げたりする",
        "effects": {"誠実さ": 1.0, "優しさ": 0.1, "協調性": -0.1}
    },
    
    # --- 情熱 ---
    {
        "a": "時間を忘れて全力で熱中する", 
        "b": "大好きなことでも、どこか冷静なことが多い",
        "effects": {"情熱": 1.0, "好奇心": 0.3, "勇敢さ": 0.1, "穏やかさ": -0.3, "誠実さ": -0.1}
    },
    {
        "a": "感情をはっきり出す方だ", 
        "b": "あまり感情を顔に出さない",
        "effects": {"情熱": 1.0, "勇敢さ": 0.1, "穏やかさ": -0.3}
    },
    {
        "a": "やるからには「一番になりたい」という気持ちがある", 
        "b": "自分が楽しくマイペースにできればOK",
        "effects": {"情熱": 1.0, "マイペースさ": 0.3, "協調性": -0.1}
    },
    
    # --- マイペースさ ---
    {
        "a": "まわりが急かしても自分のペースを絶対に崩さない", 
        "b": "まわりのスピードやその場の空気に自分を合わせる",
        "effects": {"マイペースさ": 1.0, "自立性": 0.3, "穏やかさ": 0.1, "協調性": -0.3}
    },
    {
        "a": "自分が「これが好き」という感覚を信じる", 
        "b": "流行りは遅れないようにチェックする",
        "effects": {"マイペースさ": 1.0, "自立性": 0.3, "好奇心": -0.1, "協調性": -0.1}
    },
    {
        "a": "自分だけのこだわりやルーティンがある", 
        "b": "その場の環境や相手に合わせられる",
        "effects": {"マイペースさ": 1.0, "知性": 0.1, "協調性": -0.3}
    }
]

TRAIT_POSITIVE_TEXT = {
    "優しさ": "誰もが安心できる、バツグンの思いやりと優しさを持っています！",
    "協調性": "みんなの調和を大切にできる、チームの頼れるバランサーです！",
    "好奇心": "新しいことやワクワクすることを見つける、冒険心が旺盛なタイプ！",
    "勇敢さ": "ピンチや新しい挑戦にもひるまない、強い行動力の持ち主です！",
    "穏やかさ": "いつもドシッと構えていて、周囲をホッとさせる癒やし系です！",
    "知性": "物事をじっくり筋道立てて考えられる、スマートな知性派です！",
    "自立性": "自分の軸をしっかり持っていて、一人でも力強く進める人です！",
    "誠実さ": "約束やルールを重んじる、みんなからの信頼がとっても厚い誠実派！",
    "情熱": "これ！と決めたものに全力でエネルギーを注げる熱い心の持ち主！",
    "マイペースさ": "周りに流されず、自分らしい素敵なりずむを大切にできる人です！"
}

TRAIT_NEGATIVE_TEXT = {
    "優しさ": "感情に流されず、状況をピシッと客観的に判断できるクールさを持っています！",
    "協調性": "自分の力で道を切り拓くのが得意な、単独行動もへっちゃらなタイプ！",
    "好奇心": "一つの場所や慣れ親しんだ環境をじっくり大切に育てる、安定感があります！",
    "勇敢さ": "失敗を避けるために一歩立ち止まり、慎重に準備ができる堅実派です！",
    "穏やかさ": "豊かな感受性を持っていて、自分の気持ちに素直に動ける人です！",
    "知性": "理屈にとらわれず、自分のピーンときた直感や感覚を信じて動ける天才肌！",
    "自立性": "みんなと協力したり、上手に甘えたりしながら進める愛され上手！",
    "誠実さ": "ガチガチのルールに縛られず、その場の状況に臨機応変に対応できる柔軟な人！",
    "情熱": "いつも冷静沈着で、どんなときも落ち着いて淡々とこなせるポーカーフェイス！",
    "マイペースさ": "周りの変化や新しい環境にスッとなじめる、高い適応力を持っています！"
}

# ネガティブ表現を避けるための言い換え
TRAIT_ALTERNATIVE_TITLES = {
    "優しさ": "論理的",
    "協調性": "自立心",
    "好奇心": "安定感",
    "勇敢さ": "堅実さ",
    "穏やかさ": "素直さ",
    "知性": "感覚派",
    "自立性": "協調性",
    "誠実さ": "臨機応変",
    "情熱": "冷静さ",
    "マイペースさ": "柔軟性"
}

TRAIT_KEYS = list(TRAIT_POSITIVE_TEXT.keys())

# ==============================================================================
# 2. JSONファイルからデータをロード・統合する関数
# ==============================================================================
@st.cache_data
def load_pokemon_database():
    cache_path = "pokemon_cache_compact.json"
    vectors_path = "pokemon_trait_vectors.json"
    
    if not os.path.exists(cache_path) or not os.path.exists(vectors_path):
        return [
            {"id": 25, "name": "ピカチュウ", "description": "お互いの尻尾をくっつけあって電気を流しあうのが仲間の挨拶だ。", "vector": [0.0]*10, "image": None}
        ]
        
    with open(cache_path, "r", encoding="utf-8") as f:
        cache_data = json.load(f)
    with open(vectors_path, "r", encoding="utf-8") as f:
        vector_data = json.load(f)
        
    compiled_db = []
    
    for poke_id_str, raw_vector in vector_data.items():
        if poke_id_str in cache_data:
            info = cache_data[poke_id_str]
            poke_id = int(poke_id_str)
            poke_name_ja = info.get("name_ja", f"ポケモンNo.{poke_id}")
            
            if isinstance(raw_vector, dict):
                vector = [float(raw_vector.get(trait, 0.0)) for trait in TRAIT_KEYS]
            else:
                vector = [float(v) for v in raw_vector]
            
            poke_data = info.get("pokemon_data", {})
            sprites = poke_data.get("sprites", {})
            
            image_url = sprites.get("other", {}).get("official-artwork", {}).get("front_default")
            if not image_url:
                image_url = sprites.get("front_default")
            
            flavor_entries = []
            if "species_data" in info and isinstance(info["species_data"], dict):
                flavor_entries = info["species_data"].get("flavor_text_entries", [])
            
            japanese_texts = []
            for entry in flavor_entries:
                lang = entry.get("language", {}).get("name", "")
                text = entry.get("flavor_text", "")
                text = text.replace("\n", " ").replace("\f", " ").replace("\t", " ").strip()
                if lang == "ja" and text:
                    if text not in japanese_texts:
                        japanese_texts.append(text)
            
            if japanese_texts:
                description = random.choice(japanese_texts)
            else:
                description = f"{poke_name_ja}は、まだ多くの謎に包まれているポケモンのようです！これからの冒険で生態を解き明かしましょう！"
            
            compiled_db.append({
                "id": poke_id,
                "name": poke_name_ja,
                "description": description,
                "vector": vector,
                "image": image_url
            })
            
    return compiled_db

def find_best_match_pokemon(user_vector):
    database = load_pokemon_database()
    best_pokemon = None
    max_similarity = -1.0
    u_vec = np.array(user_vector)
    u_norm = np.linalg.norm(u_vec)
    if u_norm == 0: u_norm = 1e-9

    for p in database:
        p_vec = np.array(p["vector"])
        p_norm = np.linalg.norm(p_vec)
        if p_norm == 0: p_norm = 1e-9
        similarity = np.dot(u_vec, p_vec) / (u_norm * p_norm)
        if similarity > max_similarity:
            max_similarity = similarity
            best_pokemon = p
                
    return best_pokemon, float(max_similarity)

# ==============================================================================
# 3. アプリケーション状態管理
# ==============================================================================
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "phase" not in st.session_state:
    st.session_state.phase = "start"
if "shuffled_questions" not in st.session_state:
    st.session_state.shuffled_questions = []

# ==============================================================================
# 4. 画面遷移
# ==============================================================================

if st.session_state.phase == "start":
    st.title("🐾 ポケモン性格診断")
    st.write("---")
    st.markdown(f"""
    いくつかの質問に答えるだけで、あなたの行動パターンや性格タイプを分析！\n
    たくさんのポケモンたちの中から、**あなたに一番そっくりな仲間**を見つけ出します。
    
    * **質問の数:** {len(QUESTIONS)}問
    * **かかる時間:** 1〜2分くらい
    * **注意点:** 試作段階です。おかしな結果が出てもお許しください！
    """)
    st.write("")
    if st.button("診断をスタート！", type="primary", use_container_width=True):
        st.session_state.shuffled_questions = random.sample(QUESTIONS, len(QUESTIONS))
        st.session_state.phase = "quiz"
        st.session_state.current_q = 0
        st.session_state.answers = []
        st.rerun()

elif st.session_state.phase == "quiz":
    idx = st.session_state.current_q
    quiz_list = st.session_state.shuffled_questions
    total = len(quiz_list)
    
    # 最後の回答が終わったら、即座に画面遷移
    if idx >= total:
        st.session_state.phase = "loading"
        st.rerun()
        
    st.progress(idx / total)
    st.caption(f"質問 {idx + 1} / {total}")
    
    q = quiz_list[idx]

    # スマホ用の操作補足ガイド
    st.markdown(
        "<div style='text-align: center; font-size: 0.85rem; color: #777777; margin-bottom: 15px;'>"
        "← 左or上の文にあてはまる［ 🔴とても ｜ 🔶すこし ］ 🔷すこし ｜ 🔵とても ］右or下の文にあてはまる →"
        "</div>", 
        unsafe_allow_html=True
    )
    
    st.write("---")
    
    col_left, col1, col2, col3, col4, col_right = st.columns([4, 1.2, 1.2, 1.2, 1.2, 4])

    with col_left:
        st.markdown(f"<div style='text-align: right; font-weight: bold; padding-top: 5px;'>{q['a']}</div>", unsafe_allow_html=True)
        
    with col1:
        if st.button("🔴", help="とてもあてはまる（左側）", key=f"btn_vh_{idx}"):
            st.session_state.answers.append({"effects": q["effects"], "weight": 1.0})
            st.session_state.current_q += 1
            st.rerun()
            
    with col2:
        if st.button("🔶", help="すこしあてはまる（左側）", key=f"btn_vl_{idx}"):
            st.session_state.answers.append({"effects": q["effects"], "weight": 0.5})
            st.session_state.current_q += 1
            st.rerun()
            
    with col3:
        if st.button("🔷", help="すこしあてはまる（右側）", key=f"btn_vr_l_{idx}"):
            st.session_state.answers.append({"effects": q["effects"], "weight": -0.5})
            st.session_state.current_q += 1
            st.rerun()
            
    with col4:
        if st.button("🔵", help="とてもあてはまる（右側）", key=f"btn_vr_h_{idx}"):
            st.session_state.answers.append({"effects": q["effects"], "weight": -1.0})
            st.session_state.current_q += 1
            st.rerun()
            
    with col_right:
        st.markdown(f"<div style='text-align: left; font-weight: bold; padding-top: 5px;'>{q['b']}</div>", unsafe_allow_html=True)

# 演出専用の画面フェーズ
elif st.session_state.phase == "loading":
    st.write("")
    st.write("")
    # 一番見せておきたいメッセージを最初にバシッと表示
    st.markdown("<h3 style='text-align: center;'>あなたに一番そっくりなポケモンは...</h3>", unsafe_allow_html=True)
    st.write("")
    
    # ユーザーに見える形でじっくり演出を出す
    with st.spinner("あなたの心とシンクロする仲間を呼び出しています... 🔍"):
        time.sleep(3.0)  # 3秒間しっかりこの画面をキープして「タメ」を作る
        
    # 演出時間が終わったら自動で結果画面へ
    st.session_state.phase = "result"
    st.rerun()

elif st.session_state.phase == "result":
    st.title("🎉 診断結果発表！")
    st.write("---")
    
    # 性格ベクトルの計算
    trait_scores = {trait: 0.0 for trait in TRAIT_KEYS}
    trait_counts = {trait: 0 for trait in TRAIT_KEYS}
    
    for ans in st.session_state.answers:
        effects = ans["effects"]
        weight = ans["weight"]
        for trait, val in effects.items():
            if trait in trait_scores:
                trait_scores[trait] += val * weight
                trait_counts[trait] += 1
                
    user_vector = []
    for trait in TRAIT_KEYS:
        count = trait_counts[trait]
        avg_score = trait_scores[trait] / count if count > 0 else 0.0
        avg_score = max(-1.0, min(1.0, avg_score))
        user_vector.append(avg_score)
        
    # バックエンドでの計算自体は一瞬で終わる
    best_poke, similarity_score = find_best_match_pokemon(user_vector)
    
    st.markdown(f"### あなたに一番そっくりなポケモンは...")
    st.success(f"## No.{best_poke['id']} {best_poke['name']}")
    st.caption(f"あなたとのシンクロ度: {similarity_score * 100:.1f}%")
    
    if best_poke.get("image"):
        col_img_left, col_img_mid, col_img_right = st.columns([1, 2, 1])
        with col_img_mid:
            st.image(best_poke["image"], use_container_width=True)
            
    st.subheader("📖 このポケモンの特徴（図鑑説明文より）")
    st.markdown(f"> *{best_poke['description']}*")
    
    st.write("---")
    
    st.subheader("📊 あなたの性格グラフ")
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=user_vector + [user_vector[0]], 
        theta=TRAIT_KEYS + [TRAIT_KEYS[0]],
        fill='toself',
        name='あなた',
        line_color='#FF4B4B'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[-1.0, 1.0]
            )
        ),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 特徴抽出
    st.subheader("💡 あなたってどんな人？")
    
    ranked_traits = []
    for i, trait in enumerate(TRAIT_KEYS):
        score = user_vector[i]
        ranked_traits.append({
            "trait": trait,
            "score": score,
            "abs_score": abs(score)
        })
    
    ranked_traits = sorted(ranked_traits, key=lambda x: x["abs_score"], reverse=True)
    
    for item in ranked_traits[:3]:
        trait = item["trait"]
        score = item["score"]
        
        if score >= 0:
            st.write(f"🌟 **{trait}** の傾向：{TRAIT_POSITIVE_TEXT[trait]}")
        else:
            alt_title = TRAIT_ALTERNATIVE_TITLES[trait]
            st.write(f"🍀 **{alt_title}** の傾向：{TRAIT_NEGATIVE_TEXT[trait]}")

    st.write("---")
    
    if st.button("もう一度やってみる！", use_container_width=True):
        st.session_state.current_q = 0
        st.session_state.answers = []
        st.session_state.shuffled_questions = []
        st.session_state.phase = "start"
        st.rerun()
