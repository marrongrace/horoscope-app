import warnings
import datetime
import re
import io
import matplotlib.pyplot as plt
import numpy as np

import os
import swisseph as swe
import streamlit as st # これが必要になる場合があります

# ... (パス設定処理の直後) ...
ephe_path = os.path.join(os.path.dirname(__file__), "ephe")
swe.set_ephe_path(ephe_path)

# 【画面に表示して確認する】
st.write(f"DEBUG: 検索しているフォルダパス: {ephe_path}")
st.write(f"DEBUG: フォルダは存在しますか？: {os.path.exists(ephe_path)}")

# 外部ライブラリのインポート（未インストール時のフォールバック用）
try:
    from geopy.geocoders import Nominatim
    from timezonefinder import TimezoneFinder
    from kerykeion import AstrologicalSubject
    HAS_LIBS = True
except Exception as e:
    HAS_LIBS = False
    IMPORT_ERROR_MESSAGE = f"インポートエラー: {str(e)}"

# ==========================================
# 【追加】エフェメリスファイル（.se1）のパスを通す処理
# ==========================================
if HAS_LIBS:
    # スクリプトと同じ階層にある "ephe" フォルダを指定する場合
    ephe_path = os.path.join(os.path.dirname(__file__), "ephe")
    if os.path.exists(ephe_path):
        swe.set_ephe_path(ephe_path)
    else:
        # Streamlit Cloud等でフォルダ階層が異なる場合の保険（カレントディレクトリ等）
        if os.path.exists("ephe"):
            swe.set_ephe_path("ephe")

# ==========================================
# 辞書データ
# ==========================================
SIGN_DATA = {
    "Aries": {"jp": "牡羊座", "en": "Aries"}, "Taurus": {"jp": "牡牛座", "en": "Taurus"},
    "Gemini": {"jp": "双子座", "en": "Gemini"}, "Cancer": {"jp": "蟹座", "en": "Cancer"},
    "Leo": {"jp": "獅子座", "en": "Leo"}, "Virgo": {"jp": "乙女座", "en": "Virgo"},
    "Libra": {"jp": "天秤座", "en": "Libra"}, "Scorpio": {"jp": "蠍座", "en": "Scorpio"},
    "Sagittarius": {"jp": "射手座", "en": "Sagittarius"}, "Capricorn": {"jp": "山羊座", "en": "Capricorn"},
    "Aquarius": {"jp": "水瓶座", "en": "Aquarius"}, "Pisces": {"jp": "魚座", "en": "Pisces"}
}

SIGN_NORM_MAP = {
    # ★ 英語フルネームを追加
    "Aries": "Aries", "Taurus": "Taurus", "Gemini": "Gemini", "Cancer": "Cancer", "Leo": "Leo", "Virgo": "Virgo",
    "Libra": "Libra", "Scorpio": "Scorpio", "Sagittarius": "Sagittarius", "Capricorn": "Capricorn", "Aquarius": "Aquarius", "Pisces": "Pisces",
    # 既存の短縮形や日本語
    "Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini", "Can": "Cancer", "Leo": "Leo", "Vir": "Virgo",
    "Lib": "Libra", "Sco": "Scorpio", "Sag": "Sagittarius", "Cap": "Capricorn", "Aqu": "Aquarius", "Pis": "Pisces",
    "牡羊座": "Aries", "牡牛座": "Taurus", "双子座": "Gemini", "蟹座": "Cancer", "獅子座": "Leo", "乙女座": "Virgo",
    "天秤座": "Libra", "蠍座": "Scorpio", "射手座": "射手座", "山羊座": "Capricorn", "水瓶座": "Aquarius", "魚座": "Pisces"
}

# ==========================================
# ユーティリティ関数
# ==========================================
def get_s_name_clean(key, mode):
    norm_key = SIGN_NORM_MAP.get(str(key).strip(), "Aries")
    s = SIGN_DATA.get(norm_key, {"jp": key, "en": key})
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
# 位置情報・計算の本体関数
# ==========================================
def get_location_and_timezone(city, country):
    if not HAS_LIBS: 
        return None, None, None, f"ライブラリ不足 ({IMPORT_ERROR_MESSAGE})"
    try:
        geolocator = Nominatim(user_agent="astro_streamlit_app")
        location = geolocator.geocode(f"{city}, {country}")
        if not location: 
            return None, None, None, "エラー: 位置情報が見つかりません。"
        lat, lng = location.latitude, location.longitude
        tz_str = TimezoneFinder().timezone_at(lng=lng, lat=lat) or "UTC"
        return lat, lng, tz_str, None
    except Exception as e:
        return None, None, None, f"位置情報取得エラー: {str(e)}"

def generate_full_horoscope(name, year, month, day, hour, minute, city, country):
    if not HAS_LIBS: 
        return None, f"ライブラリ不足: {IMPORT_ERROR_MESSAGE}"
    lat, lng, tz_str, err = get_location_and_timezone(city, country)
    if err: 
        return None, err
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
# チャート画像描画関数
# ==========================================
def create_chart_image(bodies_data, mode="日本語"):
    plt.rcParams['font.family'] = ['Meiryo', 'Yu Gothic', 'sans-serif']
    
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    
    ax.set_rticks([])
    ax.set_xticks(np.linspace(0, 2 * np.pi, 12, endpoint=False))
    
    sign_labels_jp = ['牡羊座', '牡牛座', '双子座', '蟹座', '獅子座', '乙女座', '天秤座', '蠍座', '射手座', '山羊座', '水瓶座', '魚座']
    sign_labels_en = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
    labels = sign_labels_jp if mode == "日本語" else sign_labels_en
    
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 10)
    
    for b in bodies_data:
        rad = np.deg2rad(b["abs_pos"])
        ax.plot(rad, 5, marker='o', markersize=8)
        ax.text(rad, 5.5, get_p_name_clean(b["key"], mode), fontsize=9, ha='center', va='center')

    ax.grid(True)
    ax.set_title("Horoscope Chart" if mode != "日本語" else "ホロスコープ・チャート", va='bottom', fontsize=12)
    
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    
    return buf

# ==========================================
# アスペクト・複合パターン計算
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
    
    if not results: 
        return "*(アスペクトなし)*" if mode == "日本語" else "*(No aspects)*"
    
    lines = []
    if view_type == "アスペクト別":
        grouped = {}
        for r in results: 
            grouped.setdefault(r["label"], []).append(r)
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
            if p1 > p2: 
                r["b1"], r["b2"] = r["b2"], r["b1"]
                p1, p2 = p2, p1
            return (p1, p2, r["orb"])
            
        sorted_results = sorted(results, key=get_prio)
        prev = None
        for r in sorted_results:
            if prev and r["b1"] != prev: 
                lines.append("")
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
        s_keys = list(SIGN_DATA.keys())
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
# メインのデータ構造化関数
# ==========================================
def get_chart_data(name, year, month, day, hour, minute, city, country, mode, view_type, is_unknown_time):
    calc_h, calc_m = (12, 0) if is_unknown_time else (hour, minute)
    chart, err = generate_full_horoscope(name, year, month, day, calc_h, calc_m, city, country)
    if err: 
        return {"error": err}

    celestial_bodies = [
        ("Sun", chart.sun), ("Moon", chart.moon), ("Mercury", chart.mercury),
        ("Venus", chart.venus), ("Mars", chart.mars), ("Jupiter", chart.jupiter),
        ("Saturn", chart.saturn), ("Uranus", chart.uranus), ("Neptune", chart.neptune), ("Pluto", chart.pluto),
    ]

    def get_attr(keys):
        for k in keys:
            if hasattr(chart, k) and getattr(chart, k): 
                return getattr(chart, k)
            if hasattr(chart, 'model') and hasattr(chart.model, k) and getattr(chart.model, k): 
                return getattr(chart.model, k)
        return None

    for key, search_keys in [("North Node", ["true_north_lunar_node", "node"]), ("South Node", ["true_south_lunar_node", "south_node"]), ("Chiron", ["chiron"])]:
        obj = get_attr(search_keys)
        if obj: 
            celestial_bodies.append((key, obj))

    all_aspect_objs, p_lines = [], []
    for key, p in celestial_bodies:
        if isinstance(p, dict):
            sign = p.get('sign', 'Aries')
            pos = p.get('position', 0.0)
            h_num = p.get('house', '1')
        else:
            sign = getattr(p, 'sign', 'Aries')
            pos = getattr(p, 'position', 0.0)
            h_num = getattr(p, 'house', getattr(p, 'house_number', '1'))

        norm_sign = SIGN_NORM_MAP.get(str(sign), "Aries")
        s_idx = list(SIGN_DATA.keys()).index(norm_sign) if norm_sign in SIGN_DATA else 0
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
        "patterns": detect_patterns(all_aspect_objs, mode),
        "chart_image": create_chart_image(all_aspect_objs, mode)
    }
