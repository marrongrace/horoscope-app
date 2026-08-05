import warnings
import datetime
import streamlit as st
import re

# ==========================================
# ページ設定
# ==========================================
st.set_page_config(
    page_title="🔮 ホロスコープ鑑定書 / Horoscope Reading",
    page_icon="🔮",
    layout="centered",
)

# ==========================================
# 3. UIテキスト辞書（多言語対応用）
# ==========================================
ui_texts = {
    "日本語": {
        "page_title": "🔮 ホロスコープ鑑定書",
        "sidebar_header": "📝 出生データ入力",
        "name_input": "お名前 / ラベル",
        "birth_date": "生年月日",
        "birth_time": "出生時間",
        "city_input": "出生都市名 (英語例: Tokyo, Saitama)",
        "country_input": "国コード (例: JP)",
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
        "initial_info": "👈 サイドバーにデータを入力し、「✨ 鑑定書を作成する」ボタンを押してください。"
    },
    "English": {
        "page_title": "🔮 Horoscope Reading",
        "sidebar_header": "📝 Birth Data Input",
        "name_input": "Name / Label",
        "birth_date": "Birth Date",
        "birth_time": "Birth Time",
        "city_input": "Birth City (e.g. Tokyo, Saitama)",
        "country_input": "Country Code (e.g. JP)",
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
        "initial_info": "👈 Enter your birth data in the sidebar and click \"✨ Create Reading\"."
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
# 【言語選択ウィジェット】サイドバー最上部に配置
# ==========================================
st.sidebar.markdown("### 🌐 Language")
toggle_lang = st.sidebar.radio("表示言語を選択:", ['日本語', 'English'], label_visibility="collapsed")
t = ui_texts[toggle_lang]  # 選択された言語の辞書を取得

st.title(t["page_title"])

# ==========================================
# 1. 【入力設定】サイドバー ＆ フォーム
# ==========================================
st.sidebar.header(t["sidebar_header"])

with st.sidebar.form(key='horoscope_form'):
    user_name = st.text_input(t["name_input"], value="TestUser")

    # 現在の日付と時刻を初期値として取得
    now_date = datetime.date.today()
    now_time = datetime.datetime.now().time()

    birth_date = st.date_input(
        t["birth_date"], 
        value=now_date,  # 現在の日にちに連動
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date(2100, 12, 31)
    )

    birth_time = st.time_input(
        t["birth_time"], 
        value=now_time   # 現在の時刻に連動
    )
    
    DEFAULT_HOUR = birth_time.hour
    DEFAULT_MINUTE = birth_time.minute

    city_name = st.text_input(t["city_input"], value="Saitama")
    country_code = st.text_input(t["country_input"], value="JP")

    st.markdown("---")
    st.header(t["settings_header"])
    
    toggle_view_raw = st.radio(t["aspect_view_label"], t["aspect_view_options"])
    toggle_view = "ペア別" if toggle_view_raw in ["ペア別", "By Pair"] else "アスペクト別"

    unknown_checkbox = st.checkbox(t["unknown_time_checkbox"])

    submit_button = st.form_submit_button(label=t["submit_btn"])

# ==========================================
# 2. 位置情報・タイムゾーン・Kerykeion連携
# ==========================================
try:
    from geopy.geocoders import Nominatim
    from timezonefinder import TimezoneFinder
    from kerykeion import AstrologicalSubject
    HAS_LIBS = True
except Exception as e:
    HAS_LIBS = False
    import_error_message = f"インポートエラー: {str(e)}"

@st.cache_data
def get_location_and_timezone(city, country):
    if not HAS_LIBS: return None, None, None, f"ライブラリ不足 ({import_error_message})"
    try:
        geolocator = Nominatim(user_agent="astro_streamlit_app")
        location = geolocator.geocode(f"{city}, {country}")
        if not location: return None, None, None, f"エラー: 位置情報が見つかりません。"
        lat, lng = location.latitude, location.longitude
        tz_str = TimezoneFinder().timezone_at(lng=lng, lat=lat) or "UTC"
        return lat, lng, tz_str, None
    except Exception as e:
        return None, None, None, f"位置情報取得エラー: {str(e)}"

def generate_full_horoscope(name, year, month, day, hour, minute, city, country):
    if not HAS_LIBS: return None, f"ライブラリ不足: {import_error_message}"
    lat, lng, tz_str, err = get_location_and_timezone(city, country)
    if err: return None, err
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            return AstrologicalSubject(
                name=name, year=year, month=month, day=day,
                hour=hour, minute=minute, lat=lat, lng=lng, tz_str=tz_str, city=city
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
    patterns, aspect_pairs = [], []
    n = len(bodies)
    for i in range(n):
        for j in range(i + 1, n):
            diff = min(abs(bodies[i]["abs_pos"] - bodies[j]["abs_pos"]), 360 - abs(bodies[i]["abs_pos"] - bodies[j]["abs_pos"]))
            if diff <= 6.0: aspect_pairs.append((bodies[i]["key"], bodies[j]["key"], "Conjunction"))
            if abs(diff - 180) <= 6.0: aspect_pairs.append((bodies[i]["key"], bodies[j]["key"], "Opposition"))
            if abs(diff - 90) <= 5.0: aspect_pairs.append((bodies[i]["key"], bodies[j]["key"], "Square"))

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
            m_names = ", ".join([get_p_name_clean(m, mode) for m in major])
            if mode == "日本語":
                patterns.append(f"**ステリウム in {s_loc}** : [{m_names}]")
            else:
                patterns.append(f"**Stellium in {s_loc}** : [{m_names}]")

    opps = [(a, b) for a, b, t in aspect_pairs if t == "Opposition"]
    squares = [(a, b) for a, b, t in aspect_pairs if t == "Square"]
    sq_dict = {}
    for a, b in squares:
        sq_dict.setdefault(a, set()).add(b)
        sq_dict.setdefault(b, set()).add(a)
        
    for op_a, op_b in opps:
        common_sq = sq_dict.get(op_a, set()).intersection(sq_dict.get(op_b, set()))
        for apex in common_sq:
            p_apex = get_p_name_clean(apex, mode)
            p_a = get_p_name_clean(op_a, mode)
            p_b = get_p_name_clean(op_b, mode)
            if mode == "日本語":
                patterns.append(f"**Tスクエア [頂点: {p_apex}]** : {p_a} と {p_b} の対立を {p_apex} が結びます")
            else:
                patterns.append(f"**T-Square [Apex: {p_apex}]** : {p_apex} bridges the opposition between {p_a} and {p_b}")
            
    return patterns

# ==========================================
# 5. データ抽出・画面描画用辞書生成
# ==========================================
def get_chart_data(name, year, month, day, hour, minute, city, country, mode, view_type, is_unknown_time):
    calc_h, calc_m = (12, 0) if is_unknown_time else (hour, minute)
    chart, err = generate_full_horoscope(name, year, month, day, calc_h, calc_m, city, country)
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
    for key, p in celestial_bodies:
        # 辞書型またはオブジェクト型から安全に値を取り出す
        if isinstance(p, dict):
            sign = p.get('sign', 'Aries')
            pos = p.get('position', 0.0)
            # house, house_number, あるいはそれに類するキーを探す
            h_num = p.get('house') or p.get('house_number') or 1
        else:
            sign = getattr(p, 'sign', 'Aries')
            pos = getattr(p, 'position', 0.0)
            # kerykeionのオブジェクトが持つ可能性のあるハウスの属性を総当たりで確認
            h_num = (
                getattr(p, 'house', None) or 
                getattr(p, 'house_number', None) or 
                getattr(p, 'house_name', None) or 
                1
            )

        # デバッグ用：もしうまく取れてない場合に備えて数値に変換しておく処理
        try:
            h_num = int(str(h_num).replace('st', '').replace('nd', '').replace('rd', '').replace('th', ''))
        except:
            h_num = 1

        norm_sign = sign_normalize_map.get(str(sign), "Aries")
        s_idx = list(sign_data.keys()).index(norm_sign) if norm_sign in sign_data else 0
        all_aspect_objs.append({"key": key, "abs_pos": s_idx * 30 + pos})
        
        p_name, s_name = get_p_name_clean(key, mode), get_s_name_clean(sign, mode)
        if is_unknown_time: 
            p_lines.append(f"**{p_name}** : {s_name} `({pos:.2f}°)`")
        else: 
            p_lines.append(f"**{p_name}** : {s_name} ({format_house_name_clean(h_num, mode)}) `({pos:.2f}°)`")

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
        houses = [chart.first_house, chart.second_house, chart.third_house, chart.fourth_house, chart.fifth_house, chart.sixth_house,
                  chart.seventh_house, chart.eighth_house, chart.ninth_house, chart.tenth_house, chart.eleventh_house, chart.twelfth_house]
        for i, h in enumerate(houses, 1):
            h_lines.append(f"**{format_house_name_clean(i, mode)}** : {get_s_name_clean(h.sign, mode)}")
    else:
        h_lines.append("*(出生時間不明のためハウス除外)*" if mode == "日本語" else "*(Houses excluded due to unknown birth time)*")

    time_note = "（12:00仮定）" if is_unknown_time else ""
    return {
        "error": None,
        "date_str": f"{year}年{month}月{day}日 {calc_h}:{calc_m:02d} {time_note}" if mode == "日本語" else f"{year}-{month:02d}-{day:02d} {calc_h}:{calc_m:02d} {'(Assumed 12:00)' if is_unknown_time else ''}",
        "loc_str": f"{city} ({country}) [Lat:{chart.lat:.2f}, Lng:{chart.lng:.2f}]",
        "angles": angles_list,
        "bodies": p_lines,
        "houses": h_lines,
        "aspects": calculate_aspects(all_aspect_objs, mode, view_type),
        "patterns": detect_patterns(all_aspect_objs, mode)
    }

# ==========================================
# 6. メイン画面の描画
# ==========================================
if submit_button:
    calc_year, calc_month, calc_day = birth_date.year, birth_date.month, birth_date.day

    with st.spinner(t["loading"]):
        data = get_chart_data(user_name, calc_year, calc_month, calc_day, DEFAULT_HOUR, DEFAULT_MINUTE, city_name, country_code, toggle_lang, toggle_view, unknown_checkbox)

    if data.get("error"):
        st.error(data["error"])
    else:
        # --- 鑑定書ヘッダー ---
        st.markdown(f"""
        <div style="padding: 20px; border: 2px solid #D4AF37; border-radius: 10px; background-color: rgba(212, 175, 55, 0.05); text-align: center; margin-bottom: 25px;">
            <h2 style="margin: 0; color: #B8860B;">✨ {user_name} {"さんのホロスコープ" if toggle_lang=="日本語" else "'s Horoscope"} ✨</h2>
            <p style="margin: 10px 0 0 0; font-size: 1.1em; color: gray;">{data['date_str']}<br>{data['loc_str']}</p>
        </div>
        """, unsafe_allow_html=True)

        # --- 主要アングル（ASC / MC） ---
        if data["angles"]:
            col_a1, col_a2 = st.columns(2)
            col_a1.info(data["angles"][0])
            col_a2.info(data["angles"][1])
        st.write("")

        # --- 天体とハウスの2カラムレイアウト ---
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"### {t['bodies_header']}")
            for p in data["bodies"]:
                st.markdown(f"- {p}")
                
        with col2:
            st.markdown(f"### {t['houses_header']}")
            for h in data["houses"]:
                st.markdown(f"- {h}")

        st.divider()

        # --- アスペクト ---
        st.markdown(f"### {t['aspects_header']}")
        with st.expander(t["aspects_expander"], expanded=True):
            st.markdown(data["aspects"])

        st.divider()

        # --- 複合アスペクト ---
        st.markdown(f"### {t['patterns_header']}")
        if data["patterns"]:
            for pat in data["patterns"]:
                st.success(pat)
        else:
            st.markdown(t["no_patterns"])
else:
    st.info(t["initial_info"])
