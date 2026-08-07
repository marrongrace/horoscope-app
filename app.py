import warnings
import datetime
import streamlit as st
import re
import pytz
import os
import swisseph as swe
import requests
import urllib.parse

# パス設定などは最初に一度でOK
swe.set_ephe_path("./ephe")

# ==========================================
# 💡 エフェメリスパスの定義（ここで最初に定義します）
# ==========================================
ephe_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "ephe"))
if not ephe_path.endswith(os.path.sep):
    ephe_path += os.path.sep

if os.path.exists(ephe_path):
    swe.set_ephe_path(ephe_path)
    
# ==========================================
# 📍 地名から緯度・経度を自動取得する関数（国土地理院API）
# ==========================================
def get_lat_lng_from_address(place_name):
    try:
        encoded_name = urllib.parse.quote(place_name)
        url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={encoded_name}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                coords = data[0]["geometry"]["coordinates"]
                return coords[1], coords[0]  # [lat, lng] の順で返す
    except Exception as e:
        print(f"ジオコーディングエラー: {e}")
    return None, None

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(
    page_title="🔮 ホロスコープ鑑定書 / Horoscope Reading",
    page_icon="🔮",
    layout="centered",
)

# ==========================================
# 📍 47都道府県のリスト（都道府県選択用）
# ==========================================
PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "长崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県", "海外・その他"
]

# ==========================================
# 3. UIテキスト辞書（多言語対応用）
# ==========================================
ui_texts = {
    "日本語": {
        "page_title": "🔮 ホロスコープ鑑定書",
        "sidebar_header": "📝 出生データ入力",
        "name_input": "お名前 / ラベル",
        "birth_date": "生年月日",
        "birth_time": "出生時間（初期値：日本時間）",
        "pref_select": "都道府県 (Prefecture)",
        "city_input": "市区町村・地名 (例: 加須市 / Chiyoda-ku)",
        "lat_input": "緯度 (Latitude)",
        "lng_input": "経度 (Longitude)",
        "lat_caption": "💡 Googleマップ等で調べた数値を入力してください",
        "settings_header": "⚙️ 表示設定",
        "aspect_view_label": "アスペクト表示:",
        "aspect_view_options": ["ペア別", "アスペクト別"],
        "unknown_time_checkbox": "出生時間が分からない（12:00仮定 / ハウス除外）",
        "submit_btn": "✨ 鑑定書を作成する",
        "loading": "星の配置を読み解いています... 🌌✨",
        "bodies_header": "天体 ＋ 感受点",
        "houses_header": "12ハウス",
        "aspects_header": "主要アスペクト (星同士の結びつき)",
        "aspects_expander": "詳細なアスペクト一覧を見る",
        "patterns_header": "複合アスペクト (特別な星のパターン)",
        "no_patterns": "*(該当する複合アスペクトなし)*",
    },
    "English": {
        "page_title": "🔮 Horoscope Reading",
        "sidebar_header": "📝 Birth Data Input",
        "name_input": "Name / Label",
        "birth_date": "Birth Date",
        "birth_time": "Birth Time",
        "pref_select": "Prefecture",
        "city_input": "City / Location Name (e.g. Kazo / London)",
        "lat_input": "Latitude",
        "lng_input": "Longitude",
        "lat_caption": "💡 Enter coordinates from Google Maps or similar tools",
        "settings_header": "⚙️ Display Settings",
        "aspect_view_label": "Aspect View:",
        "aspect_view_options": ["By Pair", "By Aspect"],
        "unknown_time_checkbox": "Unknown Birth Time (Assumed 12:00 / Exclude Houses)",
        "submit_btn": "✨ Create Reading",
        "loading": "Decoding the positions of the stars... 🌌✨",
        "bodies_header": "Celestial Bodies & Points",
        "houses_header": "12 Houses",
        "aspects_header": "Main Aspects",
        "aspects_expander": "View Detailed Aspects",
        "patterns_header": "Complex Aspects (Special Patterns)",
        "no_patterns": "*(No complex aspects found)*",
    }
}

# ==========================================
# 3. 名称辞書と正規化マッピング
# ==========================================
sign_data = {
    "Aries": {"jp": "牡羊座", "en": "Aries"}, "Taurus": {"jp": "牡牛座", "en": "Taurus"},
    "Gemini": {"jp": "双子座", "en": "Gemini"}, "Cancer": {"jp": "蟹座", "en": "Cancer"},
    "Leo": {"jp": "獅子座", "en": "Leo"}, "Virgo": {"jp": "乙女座", "en": "Virgo"},
    "Libra": {"jp": "天秤座", "en": "Libra"}, "Scorpio": {"jp": "蠍座", "en": "Scorpio"},
    "Sagittarius": {"jp": "射手座", "en": "Sagittarius"}, "Capricorn": {"jp": "山羊座", "en": "Capricorn"},
    "Aquarius": {"jp": "水瓶座", "en": "Aquarius"}, "Pisces": {"jp": "魚座", "en": "Pisces"}
}

sign_normalize_map = {
    "Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini", "Can": "Cancer", "Leo": "Leo", "Vir": "Virgo",
    "Lib": "Libra", "Sco": "Scorpio", "Sag": "Sagittarius", "Cap": "Capricorn", "Aqu": "Aquarius", "Pis": "Pisces",
    "牡羊座": "Aries", "牡牛座": "Taurus", "双子座": "Gemini", "蟹座": "Cancer", "獅子座": "Leo", "乙女座": "Virgo",
    "天秤座": "Libra", "蠍座": "Scorpio", "射手座": "Sagittarius", "山羊座": "Capricorn", "水瓶座": "Aquarius", "魚座": "Pisces"
}

def get_s_name_clean(key, mode):
    norm_key = sign_normalize_map.get(str(key).strip(), "Aries")
    s = sign_data.get(norm_key, {"jp": key, "en": key})
    return s['jp'] if mode == "日本語" else s['en']

def format_house_name_clean(house_input, mode):
    digits = re.findall(r'\d+', str(house_input))
    h_num = digits[0] if digits else "1"
    sfx = {"1": "st", "2": "nd", "3": "rd"}.get(h_num, "th")
    if mode == "日本語":
        return f"第{h_num}ハウス"
    else:
        return f"{h_num}{sfx} House"

def get_p_name_clean(key, mode):
    jp_names = {
        "Sun": "太陽", "Moon": "月", "Mercury": "水星", "Venus": "金星", "Mars": "火星",
        "Jupiter": "木星", "Saturn": "土星", "Uranus": "天王星", "Neptune": "海王星", "Pluto": "冥王星",
        "North Node": "ドラゴンヘッド", "South Node": "ドラゴンテイル", "Chiron": "キロン"
    }
    jp_n = jp_names.get(key, key)
    return jp_n if mode == "日本語" else key

# ==========================================
# 【言語選択ウィジェット】サイドバー最上部
# ==========================================
st.sidebar.markdown("### 🌐 Language")
toggle_lang = st.sidebar.radio("表示言語を選択:", ['日本語', 'English'], label_visibility="collapsed")
t = ui_texts[toggle_lang]

st.sidebar.markdown("---")
st.sidebar.caption(f"📁 Ephe Path: `{ephe_path}`\n\n🟢 Status: `{'Loaded' if os.path.exists(ephe_path) else 'Folder Not Found'}`")

st.title(t["page_title"])

# ==========================================
# 1. 【入力設定】サイドバー ＆ フォーム
# ==========================================
st.sidebar.header(t["sidebar_header"])

with st.sidebar.form(key='horoscope_form'):
    user_name = st.text_input(t["name_input"], value="TestUser")

    now_date = datetime.date.today()
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    now_time = datetime.datetime.now(tokyo_tz).time()

    birth_date = st.date_input(
        t["birth_date"], 
        value=now_date, 
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date(2100, 12, 31)
    )

    birth_time = st.time_input(
        t["birth_time"], 
        value=now_time
    )
    
    DEFAULT_HOUR = birth_time.hour
    DEFAULT_MINUTE = birth_time.minute

    # ─── 都道府県選択 ＆ 市町村自由入力（自動座標連動版） ───
    selected_pref = st.selectbox(t["pref_select"], PREFECTURES, index=10)
    
    # セッションステートの初期化（未登録の場合）
    if "input_lat_val" not in st.session_state:
        st.session_state.input_lat_val = 36.1243
    if "input_lng_val" not in st.session_state:
        st.session_state.input_lng_val = 139.5983
    if "last_city_input" not in st.session_state:
        st.session_state.last_city_input = "加須市"

    # ▼【修正】変数名を 'input_city_name' に合わせる
    input_city_name = st.text_input(t["city_input"], value=st.session_state.last_city_input)

    # ▼【修正】条件判定や代入もすべて 'input_city_name' に統一する
    if input_city_name != st.session_state.last_city_input:
        st.session_state.last_city_input = input_city_name
        # 都道府県名＋市町村名で検索するとよりヒット率が上がります
        search_query = f"{selected_pref}{input_city_name}" if selected_pref != "海外・その他" else input_city_name
        lat_res, lng_res = get_lat_lng_from_address(search_query)
        if lat_res is not None and lng_res is not None:
            st.session_state.input_lat_val = lat_res
            st.session_state.input_lng_val = lng_res

    st.markdown(t["lat_caption"])
    input_lat = st.number_input(t["lat_input"], value=st.session_state.input_lat_val, format="%.4f")
    input_lng = st.number_input(t["lng_input"], value=st.session_state.input_lng_val, format="%.4f")

    st.markdown("---")
    st.header(t["settings_header"])
    
    toggle_view_raw = st.radio(t["aspect_view_label"], t["aspect_view_options"])
    toggle_view = "ペア別" if toggle_view_raw in ["ペア別", "By Pair"] else "アスペクト別"

    unknown_checkbox = st.checkbox(t["unknown_time_checkbox"])

    submit_button = st.form_submit_button(label=t["submit_btn"])

# ==========================================
# 2. ホロスコープ計算処理（Kerykeion連携）
# ==========================================
try:
    from kerykeion import AstrologicalSubject
    HAS_LIBS = True
except Exception as e:
    HAS_LIBS = False
    import_error_message = f"インポートエラー: {str(e)}"

def generate_full_horoscope(name, year, month, day, hour, minute, lat, lng, city_display_name):
    if not HAS_LIBS: return None, f"ライブラリ不足: {import_error_message}"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return AstrologicalSubject(
                name=name, year=year, month=month, day=day,
                hour=hour, minute=minute, lat=lat, lng=lng, tz_str="Asia/Tokyo", city=city_display_name
            ), None
        except Exception as e:
            return None, f"ホロスコープ計算エラー: {str(e)}"

# ==========================================
# 4. アスペクト・複合パターン計算
# ==========================================
def calculate_aspects(bodies, mode="日本語", view_type="ペア別"):
    aspect_defs = [
        ("Conjunction", 0, 7.0, "コンジャンクション (0°)", "Conjunction"),
        ("Opposition", 180, 7.0, "オポジション (180°)", "Opposition"),
        ("Trine", 120, 6.0, "トライン (120°)", "Trine"),
        ("Square", 90, 6.0, "スクエア (90°)", "Square"),
        ("Sextile", 60, 5.0, "セクスタイル (60°)", "Sextile"),
        ("Quincunx", 150, 3.0, "クインカンクス (150°)", "Quincunx")
    ]
    results = []
    n = len(bodies)
    for i in range(n):
        for j in range(i + 1, n):
            b1, b2 = bodies[i], bodies[j]
            diff = min(abs(b1["abs_pos"] - b2["abs_pos"]), 360 - abs(b1["abs_pos"] - b2["abs_pos"]))
            for asp_key, target_ang, orb_limit, jp_label, en_label in aspect_defs:
                orb = abs(diff - target_ang)
                if orb <= orb_limit:
                    lbl = jp_label if mode == "日本語" else en_label
                    results.append({"label": lbl, "b1": b1["key"], "b2": b2["key"], "orb": orb})
    
    if not results: return "*(アスペクトなし)*" if mode == "日本語" else "*(No aspects)*"
    
    lines = []
    if view_type == "アスペクト別":
        grouped = {}
        for r in results: grouped.setdefault(r["label"], []).append(r)
        for label, items in grouped.items():
            lines.append(f"**■ {label}**")
            for item in sorted(items, key=lambda x: x["orb"]):
                lines.append(f"- {get_p_name_clean(item['b1'], mode)} & {get_p_name_clean(item['b2'], mode)} `(orb: {item['orb']:.2f}°)`")
            lines.append("")
    else:
        planet_priority = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "North Node", "South Node", "Chiron"]
        def get_prio(r):
            p1 = planet_priority.index(r["b1"]) if r["b1"] in planet_priority else 99
            p2 = planet_priority.index(r["b2"]) if r["b2"] in planet_priority else 99
            if p1 > p2: r["b1"], r["b2"] = r["b2"], r["b1"]; p1, p2 = p2, p1
            return (p1, p2, r["orb"])
            
        sorted_results = sorted(results, key=get_prio)
        prev = None
        for r in sorted_results:
            if prev and r["b1"] != prev: lines.append("")
            lines.append(f"- {get_p_name_clean(r['b1'], mode)} & {get_p_name_clean(r['b2'], mode)} : **{r['label']}** `(orb: {r['orb']:.2f}°)`")
            prev = r["b1"]
            
    return "\n".join(lines)

def detect_patterns(bodies, mode="日本語"):
    patterns = []
    aspect_pairs = []
    n = len(bodies)
    for i in range(n):
        for j in range(i + 1, n):
            pos1, pos2 = bodies[i]["abs_pos"], bodies[j]["abs_pos"]
            k1, k2 = bodies[i]["key"], bodies[j]["key"]
            diff = min(abs(pos1 - pos2), 360 - abs(pos1 - pos2))
            
            if diff <= 6.0: aspect_pairs.append((k1, k2, "Conjunction", diff))
            if abs(diff - 180) <= 6.0: aspect_pairs.append((k1, k2, "Opposition", abs(diff - 180)))
            if abs(diff - 120) <= 6.0: aspect_pairs.append((k1, k2, "Trine", abs(diff - 120)))
            if abs(diff - 90) <= 5.0: aspect_pairs.append((k1, k2, "Square", abs(diff - 90)))
            if abs(diff - 60) <= 5.0: aspect_pairs.append((k1, k2, "Sextile", abs(diff - 60)))
            if abs(diff - 150) <= 3.0: aspect_pairs.append((k1, k2, "Quincunx", abs(diff - 150)))

    # ステリウム
    sign_counts = {}
    for b in bodies:
        s_idx = int(b["abs_pos"] // 30)
        s_keys = list(sign_data.keys())
        if s_idx < len(s_keys):
            sign_counts.setdefault(s_keys[s_idx], []).append(b["key"])
            
    for s_name, members in sign_counts.items():
        major = [m for m in members if m not in ["North Node", "South Node", "Chiron"]]
        if len(major) >= 3:
            s_loc = get_s_name_clean(s_name, mode)
            m_names = " & ".join([get_p_name_clean(m, mode) for m in major])
            if mode == "日本語":
                patterns.append(f"ステリウム in {s_loc} : {m_names}")
            else:
                patterns.append(f"Stellium in {s_loc} : {m_names}")

    opps = [(a, b) for a, b, t, _ in aspect_pairs if t == "Opposition"]
    squares = [(a, b) for a, b, t, _ in aspect_pairs if t == "Square"]
    trines = [(a, b) for a, b, t, _ in aspect_pairs if t == "Trine"]
    sextiles = [(a, b) for a, b, t, _ in aspect_pairs if t == "Sextile"]
    quincunxes = [(a, b) for a, b, t, _ in aspect_pairs if t == "Quincunx"]

    sq_dict = {}
    for a, b in squares:
        sq_dict.setdefault(a, set()).add(b)
        sq_dict.setdefault(b, set()).add(a)

    tr_dict = {}
    for a, b in trines:
        tr_dict.setdefault(a, set()).add(b)
        tr_dict.setdefault(b, set()).add(a)

    sex_dict = {}
    for a, b in sextiles:
        sex_dict.setdefault(a, set()).add(b)
        sex_dict.setdefault(b, set()).add(a)

    qui_dict = {}
    for a, b in quincunxes:
        qui_dict.setdefault(a, set()).add(b)
        qui_dict.setdefault(b, set()).add(a)

    # Tスクエア
    for op_a, op_b in opps:
        common_sq = sq_dict.get(op_a, set()).intersection(sq_dict.get(op_b, set()))
        for apex in common_sq:
            p_apex, p_a, p_b = get_p_name_clean(apex, mode), get_p_name_clean(op_a, mode), get_p_name_clean(op_b, mode)
            if mode == "日本語":
                patterns.append(f"Tスクエア [頂点: {p_apex}] : {p_apex} & {p_a} & {p_b}")
            else:
                patterns.append(f"T-Square [Apex: {p_apex}] : {p_apex} & {p_a} & {p_b}")

    # グランドクロス
    checked_gc = set()
    for i in range(len(opps)):
        for j in range(i + 1, len(opps)):
            op1_a, op1_b = opps[i]
            op2_a, op2_b = opps[j]
            all_nodes = {op1_a, op1_b, op2_a, op2_b}
            if len(all_nodes) == 4:
                pairs_to_check = [(op1_a, op2_a), (op1_a, op2_b), (op1_b, op2_a), (op1_b, op2_b)]
                if all(any((min(a,b)==min(x,y) and max(a,b)==max(x,y)) for a,b,t,_ in aspect_pairs if t=="Square") for x,y in pairs_to_check):
                    sorted_key = tuple(sorted(list(all_nodes)))
                    if sorted_key not in checked_gc:
                        checked_gc.add(sorted_key)
                        names = " & ".join([get_p_name_clean(k, mode) for k in sorted_key])
                        if mode == "日本語":
                            patterns.append(f"グランドクロス : {names}")
                        else:
                            patterns.append(f"Grand Cross : {names}")

    # グランドトライン
    checked_gt = set()
    for a, neighbors in tr_dict.items():
        for b in neighbors:
            common_tr = tr_dict.get(a, set()).intersection(tr_dict.get(b, set()))
            for c in common_tr:
                if a < b < c:
                    sorted_key = (a, b, c)
                    if sorted_key not in checked_gt:
                        checked_gt.add(sorted_key)
                        p_a, p_b, p_c = get_p_name_clean(a, mode), get_p_name_clean(b, mode), get_p_name_clean(c, mode)
                        if mode == "日本語":
                            patterns.append(f"グランドトライン : {p_a} & {p_b} & {p_c}")
                        else:
                            patterns.append(f"Grand Trine : {p_a} & {p_b} & {p_c}")

    # ミニトライン
    checked_mt = set()
    for a, neighbors in sex_dict.items():
        for b in neighbors:
            if a < b:
                common_tr = tr_dict.get(a, set()).intersection(tr_dict.get(b, set()))
                for c in common_tr:
                    sorted_key = tuple(sorted([a, b, c]))
                    if sorted_key not in checked_mt:
                        checked_mt.add(sorted_key)
                        p_a, p_b, p_c = get_p_name_clean(sorted_key[0], mode), get_p_name_clean(sorted_key[1], mode), get_p_name_clean(sorted_key[2], mode)
                        if mode == "日本語":
                            patterns.append(f"ミニトライン : {p_a} & {p_b} & {p_c}")
                        else:
                            patterns.append(f"Mini Trine : {p_a} & {p_b} & {p_c}")

    # メディエーション
    checked_med = set()
    for op_a, op_b in opps:
        mediators = (sex_dict.get(op_a, set()).intersection(tr_dict.get(op_b, set()))).union(
                    tr_dict.get(op_a, set()).intersection(sex_dict.get(op_b, set()))
                  )
        for med in mediators:
            sorted_key = tuple(sorted([op_a, op_b])) + (med,)
            if sorted_key not in checked_med:
                checked_med.add(sorted_key)
                p_a, p_b, p_med = get_p_name_clean(op_a, mode), get_p_name_clean(op_b, mode), get_p_name_clean(med, mode)
                if mode == "日本語":
                    patterns.append(f"メディエーション [調停] : {p_med} & {p_a} & {p_b}")
                else:
                    patterns.append(f"Mediation [Mediator] : {p_med} & {p_a} & {p_b}")

    # ヨッド
    for a, sex_neighbors in sex_dict.items():
        for b in sex_neighbors:
            common_qui = qui_dict.get(a, set()).intersection(qui_dict.get(b, set()))
            for apex in common_qui:
                p_apex = get_p_name_clean(apex, mode)
                p_a, p_b = get_p_name_clean(a, mode), get_p_name_clean(b, mode)
                if mode == "日本語":
                    patterns.append(f"ヨッド [頂点: {p_apex}] : {p_apex} & {p_a} & {p_b}")
                else:
                    patterns.append(f"Yod [Apex: {p_apex}] : {p_apex} & {p_a} & {p_b}")

    # 重複排除処理
    unique_patterns = []
    seen = set()
    for pat in patterns:
        if ":" in pat:
            header, body = pat.split(":", 1)
            planets_sorted = tuple(sorted([p.strip() for p in body.split("&")]))
            signature = (header.strip(), planets_sorted)
        else:
            signature = pat
            
        if signature not in seen:
            seen.add(signature)
            unique_patterns.append(pat)

    return unique_patterns

# ==========================================
# 5. データ抽出・画面描画用辞書生成
# ==========================================
def get_chart_data(name, year, month, day, hour, minute, lat, lng, city_display_name, mode, view_type, is_unknown_time):
    calc_h, calc_m = (12, 0) if is_unknown_time else (hour, minute)
    chart, err = generate_full_horoscope(name, year, month, day, calc_h, calc_m, lat, lng, city_display_name)
    if err: return {"error": err}

    celestial_bodies = [
        ("Sun", chart.sun), ("Moon", chart.moon), ("Mercury", chart.mercury),
        ("Venus", chart.venus), ("Mars", chart.mars), ("Jupiter", chart.jupiter),
        ("Saturn", chart.saturn), ("Uranus", chart.uranus), ("Neptune", chart.neptune), ("Pluto", chart.pluto),
    ]

    def get_attr(keys):
        for k in keys:
            if hasattr(chart, k) and getattr(chart, k): return getattr(chart, k)
            if hasattr(chart, 'model') and hasattr(chart.model, k) and getattr(chart.model, k): return getattr(chart.model, k)
        return None

    for key, search_keys in [("North Node", ["true_north_lunar_node", "node"]), ("South Node", ["true_south_lunar_node", "south_node"]), ("Chiron", ["chiron"])]:
        obj = get_attr(search_keys)
        if obj: celestial_bodies.append((key, obj))

    all_aspect_objs, p_lines = [], []
    
    house_name_map = {
        "First_House": 1, "Second_House": 2, "Third_House": 3, "Fourth_House": 4,
        "Fifth_House": 5, "Sixth_House": 6, "Seventh_House": 7, "Eighth_House": 8,
        "Ninth_House": 9, "Tenth_House": 10, "Eleventh_House": 11, "Twelfth_House": 12
    }

    houses_list = [
        chart.first_house, chart.second_house, chart.third_house, chart.fourth_house,
        chart.fifth_house, chart.sixth_house, chart.seventh_house, chart.eighth_house,
        chart.ninth_house, chart.tenth_house, chart.eleventh_house, chart.twelfth_house
    ] if not is_unknown_time else []

    house_cusp_abs = []
    if not is_unknown_time:
        for idx, h in enumerate(houses_list):
            s_norm = sign_normalize_map.get(str(h.sign), "Aries")
            s_idx = list(sign_data.keys()).index(s_norm) if s_norm in sign_data else 0
            house_cusp_abs.append(s_idx * 30 + h.position)

    major_bodies_for_rule = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}

    for key, p in celestial_bodies:
        if isinstance(p, dict):
            sign = p.get('sign', 'Aries')
            pos = p.get('position', 0.0)
            h_raw = p.get('house', 'First_House')
        else:
            sign = getattr(p, 'sign', 'Aries')
            pos = getattr(p, 'position', 0.0)
            h_raw = getattr(p, 'house', 'First_House')

        h_num = house_name_map.get(str(h_raw), 1)
        norm_sign = sign_normalize_map.get(str(sign), "Aries")
        s_idx = list(sign_data.keys()).index(norm_sign) if norm_sign in sign_data else 0
        abs_p_pos = s_idx * 30 + pos
        all_aspect_objs.append({"key": key, "abs_pos": abs_p_pos})
        
        p_name, s_name = get_p_name_clean(key, mode), get_s_name_clean(sign, mode)
        
        if is_unknown_time:
            p_lines.append(f"**{p_name}** : {s_name} `({pos:.2f}°)`")
        else:
            base_h_label = format_house_name_clean(h_num, mode)
            rule_applied_str = ""
            
            if key in major_bodies_for_rule:
                current_h_idx = h_num - 1
                next_h_idx = (current_h_idx + 1) % 12
                
                cusp_next = house_cusp_abs[next_h_idx]
                dist_to_next_cusp = (cusp_next - abs_p_pos) % 360
                
                if 0.0 <= dist_to_next_cusp <= 5.0:
                    effective_h_num = next_h_idx + 1
                    next_h_label = format_house_name_clean(effective_h_num, mode)
                    if mode == "日本語":
                        rule_applied_str = f" (5度前ルール適用 ➡️ {next_h_label})"
                    else:
                        rule_applied_str = f" (5-degree rule applied ➡️ {next_h_label})"

            if rule_applied_str:
                p_lines.append(f"**{p_name}** : {s_name} ({base_h_label}) `({pos:.2f}°)`<br>&nbsp;&nbsp;&nbsp;&nbsp;↳{rule_applied_str.strip()}")
            else:
                p_lines.append(f"**{p_name}** : {s_name} ({base_h_label}) `({pos:.2f}°)`")

    angles_list, h_lines = [], []
    if not is_unknown_time:
        asc_s = get_s_name_clean(chart.first_house.sign, mode)
        mc_s = get_s_name_clean(chart.tenth_house.sign, mode)
        if mode == "日本語":
            angles_list = [
                f"**ASC (アセンダント)** : {asc_s} `({chart.first_house.position:.2f}°)`",
                f"**MC (ミッドヘブン)** : {mc_s} `({chart.tenth_house.position:.2f}°)`"
            ]
        else:
            angles_list = [
                f"**ASC (Ascendant)** : {asc_s} `({chart.first_house.position:.2f}°)`",
                f"**MC (Midheaven)** : {mc_s} `({chart.tenth_house.position:.2f}°)`"
            ]
        for i, h in enumerate(houses_list, 1):
            h_lines.append(f"**{format_house_name_clean(i, mode)}** : {get_s_name_clean(h.sign, mode)} `({h.position:.2f}°)`")
    else:
        h_lines.append("*(出生時間不明のためハウス除外)*" if mode == "日本語" else "*(Houses excluded due to unknown birth time)*")

    time_note = "（12:00仮定）" if is_unknown_time else ""
    return {
        "error": None,
        "date_str": f"{year}年{month}月{day}日 {calc_h}:{calc_m:02d} {time_note}" if mode == "日本語" else f"{year}-{month:02d}-{day:02d} {calc_h}:{calc_m:02d} {'(Assumed 12:00)' if is_unknown_time else ''}",
        "loc_str": f"[{selected_pref}] {city_display_name} [Lat:{chart.lat:.2f}, Lng:{chart.lng:.2f}]",
        "angles": angles_list,
        "bodies": p_lines,
        "houses": h_lines,
        "aspects": calculate_aspects(all_aspect_objs, mode, view_type),
        "patterns": detect_patterns(all_aspect_objs, mode)
    }

# ==========================================
# 6. メイン画面の描画（修正版：複合アスペクト表示を無効化）
# ==========================================
if submit_button:
    calc_year, calc_month, calc_day = birth_date.year, birth_date.month, birth_date.day

    with st.spinner(t["loading"]):
        data = get_chart_data(user_name, calc_year, calc_month, calc_day, DEFAULT_HOUR, DEFAULT_MINUTE, input_lat, input_lng, input_city_name, toggle_lang, toggle_view, unknown_checkbox)

    if data.get("error"):
        st.error(data["error"])
    else:
        st.markdown(f"""
        <div style="padding: 20px; border: 2px solid #D4AF37; border-radius: 10px; background-color: rgba(212, 175, 55, 0.05); text-align: center; margin-bottom: 25px;">
            <h2 style="margin: 0; color: #B8860B;">✨ {user_name} {"さんのホロスコープ" if toggle_lang=="日本語" else "'s Horoscope"} ✨</h2>
            <p style="margin: 10px 0 0 0; font-size: 1.1em; color: gray;">{data['date_str']}<br>{data['loc_str']}</p>
        </div>
        """, unsafe_allow_html=True)

        if data["angles"]:
            col_a1, col_a2 = st.columns(2)
            col_a1.info(data["angles"][0])
            col_a2.info(data["angles"][1])
        st.write("")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"### {t['bodies_header']}")
            for p in data["bodies"]:
                st.markdown(f"- {p}", unsafe_allow_html=True)
                
        with col2:
            st.markdown(f"### {t['houses_header']}")
            for h in data["houses"]:
                st.markdown(f"- {h}")

        st.divider()

        # ─── 複合アスペクト表示をコメントアウト ───
        # st.markdown(f"### {t['patterns_header']}")
        # if data["patterns"]:
        #     for pat in data["patterns"]:
        #         st.success(pat)
        # else:
        #     st.markdown(t["no_patterns"])
        # ──────────────────────────────────────────
            
        st.divider()
        st.markdown(f"### {'📋 結果をテキストで一括コピー' if toggle_lang=='日本語' else '📋 Copy All Results'}")
        
        copy_lines = []
        copy_lines.append(f"【ホロスコープ鑑定データ: {user_name}】")
        copy_lines.append(f"日時: {data['date_str']}")
        copy_lines.append(f"場所: {data['loc_str']}")
        copy_lines.append("\n[天体配置]")
        for b in data["bodies"]:
            clean_b = b.replace("**", "").replace("<br>", "").replace("&nbsp;&nbsp;&nbsp;&nbsp;↳", " ↳ ")
            copy_lines.append(f"- {clean_b}")
            
        if data["angles"]:
            copy_lines.append("\n[アングル]")
            for a in data["angles"]:
                clean_a = a.replace("**", "").replace("`", "")
                copy_lines.append(f"- {clean_a}")
                
        copy_lines.append("\n[主要アスペクト]")
        clean_aspects = data["aspects"].replace("**", "").replace("`", "").replace("■ ", "")
        copy_lines.append(clean_aspects)
        
        # 複合アスペクトのコピー処理も同様に除外
        full_copy_text = "\n".join(copy_lines)
        st.code(full_copy_text, language="text")
