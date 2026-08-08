import os
import json
import pytz
import requests
import urllib.parse
import warnings
import swisseph as swe
from kerykeion import AstrologicalSubject

EPHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "ephe"))
if not EPHE_PATH.endswith(os.path.sep):
    EPHE_PATH += os.path.sep

if os.path.exists(EPHE_PATH):
    swe.set_ephe_path(EPHE_PATH)

LOCAL_JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "ja_data.json"))

def load_address_master():
    """ローカルファイルから住所マスターを読み込む。なければ自動ダウンロードして保存する"""
    if os.path.exists(LOCAL_JSON_PATH):
        try:
            with open(LOCAL_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    try:
        url = "https://geolonia.github.io/japanese-addresses/api/ja.json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            with open(LOCAL_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return data
    except Exception as e:
        print(f"住所マスターの取得エラー: {e}")
    
    return {}

SIGN_DATA = {
    "Aries": {"jp": "牡羊座", "en": "Aries"}, "Taurus": {"jp": "牡牛座", "en": "Taurus"},
    "Gemini": {"jp": "双子座", "en": "Gemini"}, "Cancer": {"jp": "蟹座", "en": "Cancer"},
    "Leo": {"jp": "獅子座", "en": "Leo"}, "Virgo": {"jp": "乙女座", "en": "Virgo"},
    "Libra": {"jp": "天秤座", "en": "Libra"}, "Scorpio": {"jp": "蠍座", "en": "Scorpio"},
    "Sagittarius": {"jp": "射手座", "en": "Sagittarius"}, "Capricorn": {"jp": "山羊座", "en": "Capricorn"},
    "Aquarius": {"jp": "水瓶座", "en": "Aquarius"}, "Pisces": {"jp": "魚座", "en": "Pisces"}
}

SIGN_NORM_MAP = {
    "Ari": "Aries", "Tau": "Taurus", "Gem": "Gemini", "Can": "Cancer", "Leo": "Leo", "Vir": "Virgo",
    "Lib": "Libra", "Sco": "Scorpio", "Sag": "Sagittarius", "Cap": "Capricorn", "Aqu": "Aquarius", "Pis": "Pisces",
    "牡羊座": "Aries", "牡牛座": "Taurus", "双子座": "Gemini", "蟹座": "Cancer", "獅子座": "Leo", "乙女座": "Virgo",
    "天秤座": "Libra", "蠍座": "Scorpio", "射手座": "Sagittarius", "山羊座": "Capricorn", "水瓶座": "Aquarius", "魚座": "Pisces"
}

def get_cities_for_prefecture(pref):
    """指定された都道府県の市区町村リストを返す"""
    if pref == "海外・その他":
        return []
    master = load_address_master()
    if master and pref in master:
        return master[pref]
    return []

def validate_and_get_coords(pref, city_name):
    """ローカルの住所マスターで存在チェックを行い、緯度・経度を返す (返り値4つ)"""
    cleaned_city = city_name.strip()
    
    if pref == "海外・その他":
        try:
            encoded_name = urllib.parse.quote(cleaned_city)
            url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={encoded_name}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    coords = data[0]["geometry"]["coordinates"]
                    return True, "", coords[1], coords[0]
        except Exception:
            pass
        return True, "", 35.6812, 139.7671

    # 1. ローカルの住所マスター（Geoloniaデータ）で完全バリデーション
    master = load_address_master()
    if master and pref in master:
        allowed_cities = master[pref]
        matched = any(c == cleaned_city or c.endswith(cleaned_city) or cleaned_city in c for c in allowed_cities)
        if not matched:
            return False, "県内には存在しない地名です", None, None

    # 2. 正確な緯度・経度を国土地理院APIで取得
    search_query = f"{pref}{cleaned_city}"
    try:
        encoded_name = urllib.parse.quote(search_query)
        url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={encoded_name}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                first_res = data[0]
                addr = first_res.get("properties", {}).get("address", "")
                title = first_res.get("properties", {}).get("title", "")
                full_text = addr + title
                if pref in full_text:
                    coords = first_res["geometry"]["coordinates"]
                    return True, "", coords[1], coords[0]
                else:
                    return False, "県内には存在しない地名です", None, None
            else:
                return False, "県内には存在しない地名です", None, None
    except Exception as e:
        print(f"ジオコーディングエラー: {e}")
    
    return False, "地名が見つからないか、通信エラーが発生しました", None, None

def to_dms(val, is_lat=True):
    abs_val = abs(val)
    deg = int(abs_val)
    minutes_float = (abs_val - deg) * 60
    minute = int(minutes_float)
    second = round((minutes_float - minute) * 60)
    
    if second == 60:
        second = 0
        minute += 1
    if minute == 60:
        minute = 0
        deg += 1
        
    if is_lat:
        direction = "北緯" if val >= 0 else "南緯" if mode == "日本語" else ("N" if val >= 0 else "S")
    else:
        direction = "東経" if val >= 0 else "西経" if mode == "日本語" else ("E" if val >= 0 else "W")
            
    # ▼ ここを度.分.秒のドット区切りに変更 ▼
    if mode == "日本語":
        return f"{direction} {deg}.{minute:02d}.{second:02d}"
    else:
        return f"{deg}.{minute:02d}.{second:02d} {direction}"

    lat_str = to_dms(lat, is_lat=True)
    lng_str = to_dms(lng, is_lat=False)
    
    return f"{lat_str}, {lng_str} (十進: {lat:.4f}, {lng:.4f})"

def get_s_name(key, mode="日本語"):
    norm = SIGN_NORM_MAP.get(str(key).strip(), "Aries")
    s = SIGN_DATA.get(norm, {"jp": key, "en": key})
    return s['jp'] if mode == "日本語" else s['en']

def get_p_name(key, mode="日本語"):
    jp_names = {
        "Sun": "太陽", "Moon": "月", "Mercury": "水星", "Venus": "金星", "Mars": "火星",
        "Jupiter": "木星", "Saturn": "土星", "Uranus": "天王星", "Neptune": "海王星", "Pluto": "冥王星",
        "North Node": "ドラゴンヘッド", "South Node": "ドラゴンテイル", "Chiron": "キロン"
    }
    return jp_names.get(key, key) if mode == "日本語" else key

def format_house_name(h_num, mode="日本語"):
    sfx = {"1": "st", "2": "nd", "3": "rd"}.get(str(h_num), "th")
    return f"第{h_num}ハウス" if mode == "日本語" else f"{h_num}{sfx} House"

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
            for _, target_ang, orb_limit, jp_lbl, en_lbl in aspect_defs:
                orb = abs(diff - target_ang)
                if orb <= orb_limit:
                    lbl = jp_lbl if mode == "日本語" else en_lbl
                    results.append({"label": lbl, "b1": b1["key"], "b2": b2["key"], "orb": orb})
    
    if not results:
        return "*(アスペクトなし)*" if mode == "日本語" else "*(No aspects)*"
    
    lines = []
    if view_type == "アスペクト別":
        grouped = {}
        for r in results: grouped.setdefault(r["label"], []).append(r)
        for label, items in grouped.items():
            lines.append(f"**■ {label}**")
            for item in sorted(items, key=lambda x: x["orb"]):
                lines.append(f"- {get_p_name(item['b1'], mode)} & {get_p_name(item['b2'], mode)} `(orb: {item['orb']:.2f}°)`")
            lines.append("")
    else:
        priority = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "North Node", "South Node", "Chiron"]
        def get_prio(r):
            p1 = priority.index(r["b1"]) if r["b1"] in priority else 99
            p2 = priority.index(r["b2"]) if r["b2"] in priority else 99
            if p1 > p2: r["b1"], r["b2"] = r["b2"], r["b1"]
            return (min(p1, p2), max(p1, p2), r["orb"])
        
        sorted_results = sorted(results, key=get_prio)
        prev = None
        for r in sorted_results:
            if prev and r["b1"] != prev: lines.append("")
            lines.append(f"- {get_p_name(r['b1'], mode)} & {get_p_name(r['b2'], mode)} : **{r['label']}** `(orb: {r['orb']:.2f}°)`")
            prev = r["b1"]
            
    return "\n".join(lines)

def detect_patterns(bodies, mode="日本語"):
    patterns = []
    aspect_pairs = []
    n = len(bodies)
    
    body_map = {b["key"]: b["abs_pos"] for b in bodies}

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

    valid_stellium_bodies = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    
    stellium_edges = []
    filtered_bodies = [b for b in bodies if b["key"] in valid_stellium_bodies]
    fn = len(filtered_bodies)
    
    for i in range(fn):
        for j in range(i + 1, fn):
            b1, b2 = filtered_bodies[i], filtered_bodies[j]
            diff = min(abs(b1["abs_pos"] - b2["abs_pos"]), 360 - abs(b1["abs_pos"] - b2["abs_pos"]))
            
            is_luminary = (b1["key"] in ["Sun", "Moon"] or b2["key"] in ["Sun", "Moon"])
            orb_limit = 10.0 if is_luminary else 7.5
            
            if diff <= orb_limit:
                stellium_edges.append((b1["key"], b2["key"]))

    adj = {}
    for k1, k2 in stellium_edges:
        adj.setdefault(k1, set()).add(k2)
        adj.setdefault(k2, set()).add(k1)

    visited = set()
    stellium_groups = []
    for node in adj:
        if node not in visited:
            component = []
            stack = [node]
            visited.add(node)
            while stack:
                curr = stack.pop()
                component.append(curr)
                for neighbor in adj.get(curr, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)
            if len(component) >= 3:
                stellium_groups.append(component)

    priority = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    for comp in stellium_groups:
        comp_sorted = sorted(comp, key=lambda x: priority.index(x) if x in priority else 99)
        m_names = " & ".join([get_p_name(m, mode) for m in comp_sorted])
        
        avg_pos = sum([body_map[k] for k in comp_sorted]) / len(comp_sorted)
        s_idx = int((avg_pos % 360) // 30)
        s_keys = list(SIGN_DATA.keys())
        s_loc = get_s_name(s_keys[s_idx], mode) if s_idx < len(s_keys) else ""
        
        lbl = f"ステリウム (周辺: {s_loc})" if mode == "日本語" else f"Stellium (approx. {s_loc})"
        patterns.append(f"{lbl} : {m_names}")

    opps = [(a, b) for a, b, t, _ in aspect_pairs if t == "Opposition"]
    squares = [(a, b) for a, b, t, _ in aspect_pairs if t == "Square"]
    trines = [(a, b) for a, b, t, _ in aspect_pairs if t == "Trine"]
    sextiles = [(a, b) for a, b, t, _ in aspect_pairs if t == "Sextile"]
    quincunxes = [(a, b) for a, b, t, _ in aspect_pairs if t == "Quincunx"]

    sq_dict, tr_dict, sex_dict, qui_dict = {}, {}, {}, {}
    for a, b in squares:
        sq_dict.setdefault(a, set()).add(b); sq_dict.setdefault(b, set()).add(a)
    for a, b in trines:
        tr_dict.setdefault(a, set()).add(b); tr_dict.setdefault(b, set()).add(a)
    for a, b in sextiles:
        sex_dict.setdefault(a, set()).add(b); sex_dict.setdefault(b, set()).add(a)
    for a, b in quincunxes:
        qui_dict.setdefault(a, set()).add(b); qui_dict.setdefault(b, set()).add(a)

    for op_a, op_b in opps:
        common_sq = sq_dict.get(op_a, set()).intersection(sq_dict.get(op_b, set()))
        for apex in common_sq:
            p_apex, p_a, p_b = get_p_name(apex, mode), get_p_name(op_a, mode), get_p_name(op_b, mode)
            lbl = f"Tスクエア [頂点: {p_apex}]" if mode == "日本語" else f"T-Square [Apex: {p_apex}]"
            patterns.append(f"{lbl} : {p_apex} & {p_a} & {p_b}")

    checked_gt = set()
    for a, neighbors in tr_dict.items():
        for b in neighbors:
            common_tr = tr_dict.get(a, set()).intersection(tr_dict.get(b, set()))
            for c in common_tr:
                if a < b < c:
                    sorted_key = (a, b, c)
                    if sorted_key not in checked_gt:
                        checked_gt.add(sorted_key)
                        p_a, p_b, p_c = get_p_name(a, mode), get_p_name(b, mode), get_p_name(c, mode)
                        lbl = "グランドトライン" if mode == "日本語" else "Grand Trine"
                        patterns.append(f"{lbl} : {p_a} & {p_b} & {p_c}")

    checked_mt = set()
    for a, neighbors in sex_dict.items():
        for b in neighbors:
            if a < b:
                common_tr = tr_dict.get(a, set()).intersection(tr_dict.get(b, set()))
                for c in common_tr:
                    sorted_key = tuple(sorted([a, b, c]))
                    if sorted_key not in checked_mt:
                        checked_mt.add(sorted_key)
                        p_a, p_b, p_c = get_p_name(sorted_key[0], mode), get_p_name(sorted_key[1], mode), get_p_name(sorted_key[2], mode)
                        lbl = "ミニトライン" if mode == "日本語" else "Mini Trine"
                        patterns.append(f"{lbl} : {p_a} & {p_b} & {p_c}")

    for a, sex_neighbors in sex_dict.items():
        for b in sex_neighbors:
            common_qui = qui_dict.get(a, set()).intersection(qui_dict.get(b, set()))
            for apex in common_qui:
                p_apex, p_a, p_b = get_p_name(apex, mode), get_p_name(a, mode), get_p_name(b, mode)
                lbl = f"ヨッド [頂点: {p_apex}]" if mode == "日本語" else f"Yod [Apex: {p_apex}]"
                patterns.append(f"{lbl} : {p_apex} & {p_a} & {p_b}")

    unique, seen = [], set()
    for pat in patterns:
        if ":" in pat:
            header, body = pat.split(":", 1)
            sig = (header.strip(), tuple(sorted([p.strip() for p in body.split("&")])))
        else:
            sig = pat
        if sig not in seen:
            seen.add(sig)
            unique.append(pat)
    return unique

def format_to_dot_notation(deg, minute=0):
    """
    度と分を '○○.○○' または '○○.○○.○○' の形式に変換する
    """
    return f"{int(deg)}.{int(minute):02d}"

def get_chart_data(name, year, month, day, hour, minute, lat, lng, city_display_name, mode, view_type, is_unknown_time):
    calc_h, calc_m = (12, 0) if is_unknown_time else (hour, minute)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            chart = AstrologicalSubject(
                name=name, year=year, month=month, day=day,
                hour=calc_h, minute=calc_m, lat=lat, lng=lng, tz_str="Asia/Tokyo", city=city_display_name
            )
        except Exception as e:
            return {"error": f"ホロスコープ計算エラー: {str(e)}"}

    bodies_meta = [
        ("Sun", chart.sun), ("Moon", chart.moon), ("Mercury", chart.mercury),
        ("Venus", chart.venus), ("Mars", chart.mars), ("Jupiter", chart.jupiter),
        ("Saturn", chart.saturn), ("Uranus", chart.uranus), ("Neptune", chart.neptune), ("Pluto", chart.pluto)
    ]

    for key, attr_list in [("North Node", ["true_north_lunar_node", "node"]), ("South Node", ["true_south_lunar_node", "south_node"]), ("Chiron", ["chiron"])]:
        for attr in attr_list:
            if hasattr(chart, attr) and getattr(chart, attr):
                bodies_meta.append((key, getattr(chart, attr)))
                break

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
        for h in houses_list:
            s_norm = SIGN_NORM_MAP.get(str(h.sign), "Aries")
            s_idx = list(SIGN_DATA.keys()).index(s_norm) if s_norm in SIGN_DATA else 0
            house_cusp_abs.append(s_idx * 30 + h.position)

    major_bodies = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}

    for key, p in bodies_meta:
        sign = p.get('sign', 'Aries') if isinstance(p, dict) else getattr(p, 'sign', 'Aries')
        pos = p.get('position', 0.0) if isinstance(p, dict) else getattr(p, 'position', 0.0)
        h_raw = p.get('house', 'First_House') if isinstance(p, dict) else getattr(p, 'house', 'First_House')

        h_num = house_name_map.get(str(h_raw), 1)
        norm_sign = SIGN_NORM_MAP.get(str(sign), "Aries")
        s_idx = list(SIGN_DATA.keys()).index(norm_sign) if norm_sign in SIGN_DATA else 0
        abs_p_pos = s_idx * 30 + pos
        all_aspect_objs.append({"key": key, "abs_pos": abs_p_pos})
        
        p_name, s_name = get_p_name(key, mode), get_s_name(sign, mode)
        
        if is_unknown_time:
            p_lines.append(f"**{p_name}** : {s_name} `({pos:.2f}°)`")
        else:
            base_h_label = format_house_name(h_num, mode)
            rule_str = ""
            if key in major_bodies:
                next_idx = (h_num % 12)
                cusp_next = house_cusp_abs[next_idx]
                dist = (cusp_next - abs_p_pos) % 360
                if 0.0 <= dist <= 5.0:
                    eff_h = next_idx + 1
                    eff_label = format_house_name(eff_h, mode)
                    rule_str = f" (5度前ルール適用 ➡️ {eff_label})" if mode == "日本語" else f" (5-degree rule applied ➡️ {eff_label})"
            
            if rule_str:
                p_lines.append(f"**{p_name}** : {s_name} ({base_h_label}) `({pos:.2f}°)`<br>&nbsp;&nbsp;&nbsp;&nbsp;↳{rule_str.strip()}")
            else:
                p_lines.append(f"**{p_name}** : {s_name} ({base_h_label}) `({pos:.2f}°)`")

    angles_list, h_lines = [], []
    if not is_unknown_time:
        asc_s = get_s_name(chart.first_house.sign, mode)
        mc_s = get_s_name(chart.tenth_house.sign, mode)
        asc_lbl = "ASC (アセンダント)" if mode == "日本語" else "ASC (Ascendant)"
        mc_lbl = "MC (ミッドヘブン)" if mode == "日本語" else "MC (Midheaven)"
        angles_list = [
            f"**{asc_lbl}** : {asc_s} `({chart.first_house.position:.2f}°)`",
            f"**{mc_lbl}** : {mc_s} `({chart.tenth_house.position:.2f}°)`"
        ]
        for i, h in enumerate(houses_list, 1):
            h_lines.append(f"**{format_house_name(i, mode)}** : {get_s_name(h.sign, mode)} `({h.position:.2f}°)`")
    else:
        h_lines.append("*(出生時間不明のためハウス除外)*" if mode == "日本語" else "*(Houses excluded due to unknown birth time)*")

    time_note = "（12:00仮定）" if is_unknown_time else ""
    date_str = f"{year}年{month}月{day}日 {calc_h}:{calc_m:02d} {time_note}" if mode == "日本語" else f"{year}-{month:02d}-{day:02d} {calc_h}:{calc_m:02d} {'(Assumed 12:00)' if is_unknown_time else ''}"
    
    dms_loc_str = format_dms(chart.lat, chart.lng, mode)
    loc_str = f"[{city_display_name}] [{dms_loc_str}]"

    return {
        "error": None, "date_str": date_str, "loc_str": loc_str,
        "angles": angles_list, "bodies": p_lines, "houses": h_lines,
        "aspects": calculate_aspects(all_aspect_objs, mode, view_type),
        "patterns": detect_patterns(all_aspect_objs, mode)
    }
