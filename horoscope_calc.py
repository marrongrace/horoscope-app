import os
import json
import pytz
import requests
import urllib.parse
import warnings
import swisseph as swefw
from kerykeion import AstrologicalSubject

EPHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "ephe"))
if not EPHE_PATH.endswith(os.path.sep):
    EPHE_PATH += os.path.sep

#if os.path.exists(EPHE_PATH):
#    swe.set_ephe_path(EPHE_PATH)

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

SIGN_RULERS = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Pluto",      # 伝統的には Mars
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Uranus",    # 伝統的には Saturn
    "Pisces": "Neptune"      # 伝統的には Jupiter
}

# 天体とサインのディグニティ対応表（主要7天体）
DIGNITIES = {
    "太陽": {"domicile": ["獅子座"], "exaltation": ["牡羊座"], "detriment": ["水瓶座"], "fall": ["天秤座"]},
    "月":   {"domicile": ["蟹座"],   "exaltation": ["牡牛座"], "detriment": ["山羊座"], "fall": ["蠍座"]},
    "水星": {"domicile": ["双子座", "乙女座"], "exaltation": ["乙女座"], "detriment": ["射手座", "魚座"], "fall": ["魚座"]},
    "金星": {"domicile": ["牡牛座", "天秤座"], "exaltation": ["魚座"], "detriment": ["蠍座", "牡羊座"], "fall": ["乙女座"]},
    "火星": {"domicile": ["牡羊座", "蠍座"],   "exaltation": ["山羊座"], "detriment": ["天秤座", "牡牛座"], "fall": ["蟹座"]},
    "木星": {"domicile": ["射手座", "魚座"],   "exaltation": ["蟹座"], "detriment": ["双子座", "乙女座"], "fall": ["山羊座"]},
    "土星": {"domicile": ["山羊座", "水瓶座"], "exaltation": ["天秤座"], "detriment": ["蟹座", "獅子座"], "fall": ["牡羊座"]}
}

def apply_dignity_color(planet_name, sign_name):
    """
    天体名とサイン名を受け取り、品位に応じて星座部分のみにHTMLカラーとラベルを付与する
    """
    for p, dign in DIGNITIES.items():
        if p in planet_name:
            if any(s == sign_name for s in dign.get("domicile", [])):
                return f'<span style="color: #ff4b4b; font-weight: bold;">{sign_name}</span> <span style="font-size: 0.85em; color: #ff4b4b;">🔴 [Domicile]</span>'
            elif any(s == sign_name for s in dign.get("exaltation", [])):
                return f'<span style="color: #ff69b4; font-weight: bold;">{sign_name}</span> <span style="font-size: 0.85em; color: #ff69b4;">🩷 [Exaltation]</span>'
            elif any(s == sign_name for s in dign.get("detriment", [])):
                return f'<span style="color: #1e90ff; font-weight: bold;">{sign_name}</span> <span style="font-size: 0.85em; color: #1e90ff;">🔵 [Detriment]</span>'
            elif any(s == sign_name for s in dign.get("fall", [])):
                return f'<span style="color: #00bfff; font-weight: bold;">{sign_name}</span> <span style="font-size: 0.85em; color: #00bfff;">🩵 [Fall]</span>'
    
    # 品位に該当しない場合はそのままのサイン名を返す
    return sign_name
    
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

def get_house_ruler_chains(houses_list, bodies_meta, house_name_map, use_5_deg_rule=False, house_cusp_abs=None):
    """
    各ハウスのカスプのルーラーをたどる連鎖（チェーン）を計算する
    use_5_deg_rule=True の場合は、5度前ルール適用後の天体ハウス位置を採用する
    """
    body_house_map = {}
    major_bodies = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}

    for key, p in bodies_meta:
        h_raw = p.get('house', 'First_House') if isinstance(p, dict) else getattr(p, 'house', 'First_House')
        h_num = house_name_map.get(str(h_raw), 1)
        
        # 5度前ルールが有効、かつ主要天体で条件を満たす場合は次のハウスにスライド
        if use_5_deg_rule and key in major_bodies and house_cusp_abs:
            sign = p.get('sign', 'Aries') if isinstance(p, dict) else getattr(p, 'sign', 'Aries')
            pos = p.get('position', 0.0) if isinstance(p, dict) else getattr(p, 'position', 0.0)
            norm_sign = SIGN_NORM_MAP.get(str(sign), "Aries")
            s_idx = list(SIGN_DATA.keys()).index(norm_sign) if norm_sign in SIGN_DATA else 0
            abs_p_pos = s_idx * 30 + pos
            
            next_idx = (h_num % 12)
            cusp_next = house_cusp_abs[next_idx]
            dist = (cusp_next - abs_p_pos) % 360
            if 0.0 <= dist <= 5.0:
                h_num = next_idx + 1

        body_house_map[key] = h_num

    house_links = {}
    for i, h in enumerate(houses_list, 1):
        sign = h.get('sign', 'Aries') if isinstance(h, dict) else getattr(h, 'sign', 'Aries')
        norm_sign = SIGN_NORM_MAP.get(str(sign), "Aries")
        ruler_key = SIGN_RULERS.get(norm_sign, "Sun")
        target_house = body_house_map.get(ruler_key, i)
        house_links[i] = target_house

    chain_results = []
    for start_h in range(1, 13):
        path = [start_h]
        visited = set([start_h])
        current = start_h
        status = "end"
        loop_target = None
        
        while current in house_links:
            next_house = house_links[current]
            if next_house == current:
                status = "domicile"
                break
            if next_house in visited:
                path.append(next_house)
                status = "loop"
                loop_target = next_house
                break
            visited.add(next_house)
            path.append(next_house)
            current = next_house
            if len(path) > 15:
                break
        
        path_str = " → ".join([f"第{h}ハウス" for h in path])
        if status == "domicile":
            display_text = f"**第{start_h}ハウス** ➡️ {path_str} (ドミサイル)"
        elif status == "loop":
            display_text = f"**第{start_h}ハウス** ➡️ {path_str} (以降 第{loop_target}ハウスとのループ)"
        else:
            display_text = f"**第{start_h}ハウス** ➡️ {path_str}"
        chain_results.append(display_text)
        
    return chain_results

def get_synastry_data(p1_info, p2_info, mode="日本語", display_mode="ペア別"):
    def get_bodies_for_aspects(info):
        calc_h, calc_m = (12, 0) if info["is_unknown_time"] else (info["hour"], info["minute"])
        chart = AstrologicalSubject(
            name=info["name"], year=info["year"], month=info["month"], day=info["day"],
            hour=calc_h, minute=calc_m, lat=info["lat"], lng=info["lng"], tz_str="Asia/Tokyo", city=info["city"]
        )
        bodies = [
            ("Sun", chart.sun), ("Moon", chart.moon), ("Mercury", chart.mercury),
            ("Venus", chart.venus), ("Mars", chart.mars), ("Jupiter", chart.jupiter),
            ("Saturn", chart.saturn), ("Uranus", chart.uranus), ("Neptune", chart.neptune), ("Pluto", chart.pluto)
        ]
        results = []
        for key, p in bodies:
            sign = p.get('sign', 'Aries')
            pos = p.get('position', 0.0)
            s_idx = list(SIGN_DATA.keys()).index(SIGN_NORM_MAP.get(str(sign), "Aries"))
            abs_pos = s_idx * 30 + pos
            results.append({"key": key, "abs_pos": abs_pos})
        return results

    chart1 = get_chart_data(p1_info["name"], p1_info["year"], p1_info["month"], p1_info["day"], p1_info["hour"], p1_info["minute"], p1_info["lat"], p1_info["lng"], p1_info["city"], mode, display_mode, p1_info["is_unknown_time"])
    chart2 = get_chart_data(p2_info["name"], p2_info["year"], p2_info["month"], p2_info["day"], p2_info["hour"], p2_info["minute"], p2_info["lat"], p2_info["lng"], p2_info["city"], mode, display_mode, p2_info["is_unknown_time"])
    
    bodies1 = get_bodies_for_aspects(p1_info)
    bodies2 = get_bodies_for_aspects(p2_info)
    
    raw_aspects = []
    aspect_defs = [
        {"name": "コンジャンクション" if mode == "日本語" else "Conjunction", "angle": 0.0, "orb": 6.0},
        {"name": "セクスタイル" if mode == "日本語" else "Sextile", "angle": 60.0, "orb": 5.0},
        {"name": "スクエア" if mode == "日本語" else "Square", "angle": 90.0, "orb": 6.0},
        {"name": "トライン" if mode == "日本語" else "Trine", "angle": 120.0, "orb": 6.0},
        {"name": "オポジション" if mode == "日本語" else "Opposition", "angle": 180.0, "orb": 6.0},
    ]

    for b1 in bodies1:
        for b2 in bodies2:
            diff = abs(b1["abs_pos"] - b2["abs_pos"]) % 360.0
            if diff > 180.0: diff = 360.0 - diff
            
            for asp in aspect_defs:
                orb = abs(diff - asp["angle"])
                if orb <= asp["orb"]:
                    raw_aspects.append({
                        "b1_key": b1["key"],
                        "b2_key": b2["key"],
                        "b1_name": get_p_name(b1["key"], mode),
                        "b2_name": get_p_name(b2["key"], mode),
                        "asp_name": asp["name"],
                        "orb": orb
                    })

    synastry_aspects = []
    if not raw_aspects:
        synastry_aspects = ["*(該当するアスペクトはありません)*" if mode == "日本語" else "*(No synastry aspects found)*"]
    else:
        if display_mode == "アスペクト別":
            asp_priority = ["コンジャンクション", "Conjunction", "セクスタイル", "Sextile", "スクエア", "Square", "トライン", "Trine", "オポジション", "Opposition"]
            raw_aspects.sort(key=lambda x: (asp_priority.index(x["asp_name"]) if x["asp_name"] in asp_priority else 99, x["orb"]))
            
            prev_asp = None
            for item in raw_aspects:
                if prev_asp is not None and item["asp_name"] != prev_asp:
                    synastry_aspects.append("")
                
                asp_str = f"- {p1_info['name']}の{item['b1_name']} ＆ {p2_info['name']}の{item['b2_name']}：{item['asp_name']} ({item['orb']:.2f}°)"
                if mode != "日本語":
                    asp_str = f"- {p1_info['name']}'s {item['b1_name']} & {p2_info['name']}'s {item['b2_name']}: {item['asp_name']} ({item['orb']:.2f}°)"
                synastry_aspects.append(asp_str)
                prev_asp = item["asp_name"]
        else:
            priority = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto", "North Node", "South Node", "Chiron"]
            raw_aspects.sort(key=lambda x: (priority.index(x["b1_key"]) if x["b1_key"] in priority else 99, x["orb"]))
            
            prev_b1 = None
            for item in raw_aspects:
                if prev_b1 is not None and item["b1_key"] != prev_b1:
                    synastry_aspects.append("")
                
                asp_str = f"- {p1_info['name']}の{item['b1_name']} ＆ {p2_info['name']}の{item['b2_name']}：{item['asp_name']} ({item['orb']:.2f}°)"
                if mode != "日本語":
                    asp_str = f"- {p1_info['name']}'s {item['b1_name']} & {p2_info['name']}'s {item['b2_name']}: {item['asp_name']} ({item['orb']:.2f}°)"
                synastry_aspects.append(asp_str)
                prev_b1 = item["b1_key"]

    return {
        "person1": chart1,
        "person2": chart2,
        "synastry_aspects": synastry_aspects
    }
import warnings

def get_transit_chart_data(transit_info, natal_bodies, mode="日本語"):
    """
    指定されたトランジット日時における天体位置を計算し、
    ネイタル天体との間のトランジット・アスペクトを計算して返す
    """
    t_year = transit_info.get("year", 2026)
    t_month = transit_info.get("month", 1)
    t_day = transit_info.get("day", 1)
    t_hour = transit_info.get("hour", 12)
    t_minute = transit_info.get("minute", 0)
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            transit_subject = AstrologicalSubject(
                name="Transit", year=t_year, month=t_month, day=t_day,
                hour=t_hour, minute=t_minute, lat=transit_info.get("lat", 35.6812), lng=transit_info.get("lng", 139.7671), 
                tz_str="Asia/Tokyo", city="Tokyo"
            )
        except Exception as e:
            return {"error": f"トランジット計算エラー: {str(e)}"}

    transit_bodies_meta = [
        ("Sun", transit_subject.sun), ("Moon", transit_subject.moon), ("Mercury", transit_subject.mercury),
        ("Venus", transit_subject.venus), ("Mars", transit_subject.mars), ("Jupiter", transit_subject.jupiter),
        ("Saturn", transit_subject.saturn), ("Uranus", transit_subject.uranus), ("Neptune", transit_subject.neptune), ("Pluto", transit_subject.pluto)
    ]

    transit_bodies = []
    for key, p in transit_bodies_meta:
        sign = p.get('sign', 'Aries') if isinstance(p, dict) else getattr(p, 'sign', 'Aries')
        pos = p.get('position', 0.0) if isinstance(p, dict) else getattr(p, 'position', 0.0)
        norm_sign = SIGN_NORM_MAP.get(str(sign), "Aries")
        s_idx = list(SIGN_DATA.keys()).index(norm_sign) if norm_sign in SIGN_DATA else 0
        abs_p_pos = s_idx * 30 + pos
        
        # 修正: s_name の代わりに norm_sign（または sign）を安全に渡す
        transit_bodies.append({
            "key": "T_" + key, 
            "original_key": key, 
            "abs_pos": abs_p_pos, 
            "sign": norm_sign, 
            "position": pos
        })

    # ネイタル天体とトランジット天体のアスペクト計算
    transit_aspects = calculate_transit_aspects(natal_bodies, transit_bodies, mode=mode)

    return {
        "transit_date": f"{t_year}年{t_month}月{t_day}日 {t_hour}:{t_minute:02d}",
        "transit_aspects": transit_aspects
    }

def calculate_transit_aspects(natal_bodies, transit_bodies, mode="日本語"):
    """
    ネイタル天体（N）とトランジット天体（T）の間のアスペクトを計算する
    """
    aspect_defs = [
        ("Conjunction", 0, 7.0, "コンジャンクション (0°)", "Conjunction"),
        ("Opposition", 180, 7.0, "オポジション (180°)", "Opposition"),
        ("Trine", 120, 6.0, "トライン (120°)", "Trine"),
        ("Square", 90, 6.0, "スクエア (90°)", "Square"),
        ("Sextile", 60, 5.0, "セクスタイル (60°)", "Sextile")
    ]
    
    results = []
    
    for b1 in natal_bodies:
        for b2 in transit_bodies:
            diff = min(abs(b1["abs_pos"] - b2["abs_pos"]), 360 - abs(b1["abs_pos"] - b2["abs_pos"]))
            for _, target_ang, orb_limit, jp_lbl, en_lbl in aspect_defs:
                orb = abs(diff - target_ang)
                if orb <= orb_limit:
                    lbl = jp_lbl if mode == "日本語" else en_lbl
                    results.append({
                        "label": lbl, 
                        "natal": b1["key"], 
                        "transit": b2["original_key"], 
                        "orb": orb
                    })
                    
    if not results:
        return ["*(トランジットアスペクトなし)*" if mode == "日本語" else "*(No transit aspects)*"]
        
    lines = []
    sorted_res = sorted(results, key=lambda x: x["orb"])
    for item in sorted_res:
        n_name = get_p_name(item["natal"], mode)
        t_name = get_p_name(item["transit"], mode)
        lines.append(f"- **T {t_name}** — **N {n_name}** : {item['label']} `(orb: {item['orb']:.2f}°)`")
        
    return lines
    
def calculate_midpoints(bodies, chart_angles=None, mode="日本語", is_unknown_time=False):
    """
    指定された条件に特化したミッドポイント（ハーフサム）を計算する
    ※ 同一天体ペア、および木星以降の大天体同士のペアを除外
    ※ is_unknown_time が True の場合、Moon, ASC, MC を除外
    """
    body_map = {b["key"]: b["abs_pos"] for b in bodies}
    planet_keys = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    outer_planets = {"Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"}
    
    # 出生時間不明時に除外するキー
    unknown_exclude_keys = {"Moon", "ASC", "MC"}
    
    priority = [
        "Sun", "Moon", "Mercury", "Venus", "Mars",
        "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
        "Chiron", "North Node", "South Node", "ASC", "MC"
    ]
    
    def get_prio(key):
        return priority.index(key) if key in priority else 99

    def get_midpoint_pos(pos1, pos2):
        diff = abs(pos1 - pos2)
        if diff > 180:
            mp = (pos1 + pos2 + 360) / 2
        else:
            mp = (pos1 + pos2) / 2
        return mp % 360

    hit_results = []
    aspect_angles = [0, 90, 180]
    orb_limit = 1.5

    # ★ ここで is_unknown_time に応じて Moon, ASC, MC を除外する
    all_points = []
    for k, pos in body_map.items():
        if is_unknown_time and k in unknown_exclude_keys:
            continue
        all_points.append((k, pos))

    n = len(all_points)

    for i in range(n):
        for j in range(i + 1, n):
            k1, pos1 = all_points[i]
            k2, pos2 = all_points[j]
            
            if k1 in outer_planets and k2 in outer_planets:
                continue
            
            is_node_involved = (k1 in ["North Node", "South Node"] or k2 in ["North Node", "South Node"])
            if is_node_involved:
                if not (k1 in planet_keys or k2 in planet_keys):
                    continue

            if not (k1 in planet_keys or k2 in planet_keys) and not is_node_involved:
                # ※ もし Moon, ASC, MC が除外された場合、ここでの ASC/MC ペアの扱いも自動的に安全になります
                allowed_pairs = {("Sun", "Moon"), ("Moon", "Sun"), ("ASC", "MC"), ("MC", "ASC")}
                if (k1, k2) not in allowed_pairs and (k2, k1) not in allowed_pairs:
                    continue

            if get_prio(k1) > get_prio(k2):
                k1, k2 = k2, k1
                pos1, pos2 = pos2, pos1

            mp_pos = get_midpoint_pos(pos1, pos2)
            mp_name = f"{get_p_name(k1, mode)}/{get_p_name(k2, mode)}"

            for target_k, target_pos in all_points:
                if target_k == k1 or target_k == k2:
                    continue
                
                diff = min(abs(mp_pos - target_pos), 360 - abs(mp_pos - target_pos))
                for ang in aspect_angles:
                    orb = abs(diff - ang)
                    if orb <= orb_limit:
                        asp_label = "0°" if ang == 0 else ("90°" if ang == 90 else "180°")
                        hit_results.append({
                            "prio1": get_prio(k1),
                            "prio2": get_prio(k2),
                            "axis": mp_name,
                            "target": get_p_name(target_k, mode),
                            "aspect": asp_label,
                            "orb": orb
                        })

    unique_hits = {}
    for h in hit_results:
        key = (h["axis"], h["target"], h["aspect"])
        if key not in unique_hits or h["orb"] < unique_hits[key]["orb"]:
            unique_hits[key] = h

    formatted_lines = []
    sorted_hits = sorted(unique_hits.values(), key=lambda x: (x["prio1"], x["prio2"], x["orb"]))
    for h in sorted_hits:
        line = f"- **{h['axis']}** ＝ **{h['target']}** `({h['aspect']} / orb: {h['orb']:.2f}°)`"
        formatted_lines.append(line)

    if not formatted_lines:
        return ["*(該当するミッドポイントヒットはありません)*" if mode == "日本語" else "*(No midpoint hits found)*"]
        
    return formatted_lines

def format_deg_min(decimal_deg):
    deg = int(decimal_deg)
    minutes = round((decimal_deg - deg) * 60)
    if minutes == 60:
        deg += 1
        minutes = 0
    return f"{deg}°{minutes:02d}′"

def to_dms(val, is_lat=True, mode="日本語"):
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
            
    if mode == "日本語":
        return f"{direction} {deg}.{minute:02d}.{second:02d}"
    else:
        return f"{deg}.{minute:02d}.{second:02d} {direction}"

def get_s_name(key, mode="日本語"):
    norm = SIGN_NORM_MAP.get(str(key).strip(), "Aries")
    s = SIGN_DATA.get(norm, {"jp": key, "en": key})
    return s['jp'] if mode == "日本語" else s['en']

def get_p_name(key, mode="日本語"):
    jp_names = {
        "Sun": "太陽", "Moon": "月", "Mercury": "水星", "Venus": "金星", "Mars": "火星",
        "Jupiter": "木星", "Saturn": "土星", "Uranus": "天王星", "Neptune": "海王星", "Pluto": "冥王星",
        "North Node": "ドラゴンヘッド", "South Node": "ドラゴンテイル", "Chiron": "キロン",
        "ASC": "ASC", "MC": "MC"
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

def calculate_composite_bodies(bodies_p1, bodies_p2):
    map1 = {b["key"]: b["abs_pos"] for b in bodies_p1}
    map2 = {b["key"]: b["abs_pos"] for b in bodies_p2}
    
    composite_bodies = []
    
    # 既存のミッドポイント計算関数（角度の平均を出す処理）
    def get_midpoint_pos(pos1, pos2):
        diff = abs(pos1 - pos2)
        if diff > 180:
            mp = (pos1 + pos2 + 360) / 2
        else:
            mp = (pos1 + pos2) / 2
        return mp % 360

    for key in map1.keys():
        if key in map2:
            comp_pos = get_midpoint_pos(map1[key], map2[key])
            # 必要に応じてサインや度数などの情報を持たせた辞書を作る
            composite_bodies.append({
                "key": key,
                "abs_pos": comp_pos,
                # 星座(sign)や度数(degree)の算出処理は既存のネイタル計算ロジックに合わせる
            })
            
    return composite_bodies
    
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

def get_chart_data(name, year, month, day, hour, minute, lat, lng, city_display_name, mode, view_type, is_unknown_time, transit_info=None):
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
        formatted_pos = format_deg_min(pos)
        
        # 品位を考慮した色付きサイン名を取得
        colored_sign = apply_dignity_color(p_name, s_name)
        
        if is_unknown_time:
            base_str = f"**{p_name}** : {colored_sign} `({formatted_pos})`"
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
                base_str = f"**{p_name}** : {colored_sign} ({base_h_label}) `({formatted_pos})`<br>&nbsp;&nbsp;&nbsp;&nbsp;↳{rule_str.strip()}"
            else:
                base_str = f"**{p_name}** : {colored_sign} ({base_h_label}) `({formatted_pos})`"

        p_lines.append(base_str)

    angles_list, h_lines = [], []
    ruler_list = []
    ruler_list_with_5deg = []
    
    if not is_unknown_time:
        asc_s = get_s_name(chart.first_house.sign, mode)
        mc_s = get_s_name(chart.tenth_house.sign, mode)
        asc_lbl = "ASC (アセンダント)" if mode == "日本語" else "ASC (Ascendant)"
        mc_lbl = "MC (ミッドヘブン)" if mode == "日本語" else "MC (Midheaven)"
        
        asc_pos_str = format_deg_min(chart.first_house.position)
        mc_pos_str = format_deg_min(chart.tenth_house.position)
        
        angles_list = [
            f"**{asc_lbl}** : {asc_s} `({asc_pos_str})`",
            f"**{mc_lbl}** : {mc_s} `({mc_pos_str})`"
        ]
        
        asc_abs_pos = 0
        for h_idx, h in enumerate(houses_list):
            if h_idx == 0:
                s_norm = SIGN_NORM_MAP.get(str(h.sign), "Aries")
                s_idx_asc = list(SIGN_DATA.keys()).index(s_norm) if s_norm in SIGN_DATA else 0
                asc_abs_pos = s_idx_asc * 30 + h.position
            if h_idx == 9:
                s_norm = SIGN_NORM_MAP.get(str(h.sign), "Aries")
                s_idx_mc = list(SIGN_DATA.keys()).index(s_norm) if s_norm in SIGN_DATA else 0
                mc_abs_pos = s_idx_mc * 30 + h.position

        for item in all_aspect_objs:
            if item["key"] == "ASC":
                item["abs_pos"] = asc_abs_pos
            elif item["key"] == "MC":
                item["abs_pos"] = mc_abs_pos

        for i, h in enumerate(houses_list, 1):
            h_pos_str = format_deg_min(h.position)
            h_lines.append(f"**{format_house_name(i, mode)}** : {get_s_name(h.sign, mode)} `({h_pos_str})`")
        
        # ハウスルーラー（5度前適用なし）
        ruler_list = get_house_ruler_chains(houses_list, bodies_meta, house_name_map, use_5_deg_rule=False)
        # ハウスルーラー（5度前適用あり）
        ruler_list_with_5deg = get_house_ruler_chains(houses_list, bodies_meta, house_name_map, use_5_deg_rule=True, house_cusp_abs=house_cusp_abs)
    else:
        h_lines.append("*(出生時間不明のためハウス除外)*" if mode == "日本語" else "*(Houses excluded due to unknown birth time)*")

    time_note = "（12:00仮定）" if is_unknown_time else ""
    date_str = f"{year}年{month}月{day}日 {calc_h}:{calc_m:02d} {time_note}" if mode == "日本語" else f"{year}-{month:02d}-{day:02d} {calc_h}:{calc_m:02d} {'(Assumed 12:00)' if is_unknown_time else ''}"
    
    lat_str = to_dms(chart.lat, is_lat=True, mode=mode)
    lng_str = to_dms(chart.lng, is_lat=False, mode=mode)
    loc_str = f"[{city_display_name}] [{lat_str}, {lng_str} (十進: {chart.lat:.4f}, {chart.lng:.4f})]"

    midpoints = calculate_midpoints(all_aspect_objs, chart_angles=angles_list, mode=mode, is_unknown_time=is_unknown_time)
    
    # トランジット情報の計算（transit_info が渡された場合）
    transit_results = None
    if transit_info:
        transit_results = get_transit_chart_data(transit_info, all_aspect_objs, mode=mode)

    return {
        "error": None, "date_str": date_str, "loc_str": loc_str,
        "angles": angles_list, "bodies": p_lines, "houses": h_lines,
        "house_rulers": ruler_list,
        "house_rulers_with_5deg": ruler_list_with_5deg,
        "midpoints": midpoints,
        "transit": transit_results,  # ここで渡す
        "aspects": calculate_aspects(all_aspect_objs, mode, view_type),
        "patterns": detect_patterns(all_aspect_objs, mode)
    }
