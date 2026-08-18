import datetime
import os
import re
import pytz
import streamlit as st
from horoscope_calc import validate_and_get_coords, get_chart_data, EPHE_PATH, get_cities_for_prefecture

try:
    from horoscope_calc import get_synastry_data
except ImportError:
    get_synastry_data = None

st.set_page_config(
    page_title="🔮 ホロスコープ鑑定書 / Horoscope Reading",
    page_icon="🔮",
    layout="centered",
)

BASE_PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県", "海外・その他"
]

st.sidebar.markdown("### 🌐 言語 / Language")
lang = st.sidebar.radio("言語選択", ["日本語", "English"], label_visibility="collapsed", key="lang_radio")

ui_texts = {
    "日本語": {
        "page_title": "🔮 ホロスコープ作成システム",
        "disclaimer": "※ 計算ライブラリや基準点の設定により、ハウス等の数値にわずかな誤差が生じる場合があります。",
        "sidebar_header": "📝 出生データ入力",
        "mode_select": "🔮 鑑定モード",
        "mode_options": ["ネイタル（出生図）", "シナストリー（相性）", "トランジット（現在の運気）"],
        "p1_header": "1人目",
        "p2_header": "2人目",
        "name_input": "お名前 / ニックネーム",
        "birth_date": "生年月日",
        "birth_time": "出生時間（日本時間）",
        "pref_select": "都道府県",
        "pref_default": "県名を選択してください",
        "city_input": "市区町村・地名 (例: 古河市)",
        "lat_input": "緯度",
        "lng_input": "経度",
        "settings_header": "⚙️ 表示設定",
        "aspect_view_label": "アスペクト表示形式:",
        "aspect_view_options": ["ペア別", "アスペクト別"],
        "unknown_time_checkbox": "出生時間が分からない（12:00仮定 / ハウス除外）",
        "submit_btn": "✨ ホロスコープを作る",
        "loading": "星々の配置を精密に計算中... 🌌✨",
        "bodies_tab": "🌟 天体＋感受点",
        "houses_tab": "🏠 12ハウス",
        "aspects_tab": "🔗 アスペクト",
        "patterns_tab": "💎 複合アスペクト",
        "invalid_pref_error": "都道府県を選択してください",
        "invalid_loc_error": "有効な地名を入力してください（県内に存在しません）"
    },
    "English": {
        "page_title": "🔮 Professional Horoscope Reading",
        "disclaimer": "※ Minor discrepancies in house degrees may occur due to calculation libraries or coordinate settings.",
        "sidebar_header": "📝 Birth Data Input",
        "mode_select": "🔮 Reading Mode",
        "mode_options": ["Single Horoscope", "Synastry (Compatibility)", "Transit"],
        "p1_header": "p1",
        "p2_header": "p2",
        "name_input": "Name / Label",
        "birth_date": "Birth Date",
        "birth_time": "Birth Time",
        "pref_select": "Prefecture",
        "pref_default": "Please select a prefecture",
        "city_input": "City / Location Name",
        "lat_input": "Latitude",
        "lng_input": "Longitude",
        "lat_caption": "💡 Auto-fetched or from Google Maps",
        "settings_header": "⚙️ Display Settings",
        "aspect_view_label": "Aspect View:",
        "aspect_view_options": ["By Pair", "By Aspect"],
        "unknown_time_checkbox": "Unknown Birth Time (Assumed 12:00 / Exclude Houses)",
        "submit_btn": "✨ Create Horoscope",
        "loading": "Calculating planetary positions... 🌌✨",
        "bodies_tab": "🌟 Celestial Bodies",
        "houses_tab": "🏠 12 Houses",
        "aspects_tab": "🔗 Aspects",
        "patterns_tab": "💎 Complex Patterns",
        "invalid_pref_error": "Please select a prefecture",
        "invalid_loc_error": "Please enter a valid location within the prefecture."
    }
}

t = ui_texts[lang]

st.markdown(f"# {t['page_title']}")
st.caption(t["disclaimer"])

PREFECTURES = [t["pref_default"]] + BASE_PREFECTURES

def convert_to_dms(text):
    if not isinstance(text, str):
        text = str(text)
    def replace_deg(match):
        val = float(match.group(1))
        deg = int(val)
        min_val = round((val - deg) * 60)
        if min_val == 60:
            deg += 1
            min_val = 0
        return f"({deg}°{min_val:02d}')"
    return re.sub(r'\((\d+\.\d+)°\)', replace_deg, text)

def localize_text(text, lang):
    if lang == "日本語" or not isinstance(text, str):
        return text
    translations = {
        "牡羊座": "Aries", "牡牛座": "Taurus", "双子座": "Gemini", "蟹座": "Cancer",
        "獅子座": "Leo", "乙女座": "Virgo", "天秤座": "Libra", "蠍座": "Scorpio",
        "射手座": "Sagittarius", "山羊座": "Capricorn", "水瓶座": "Aquarius", "魚座": "Pisces",
        "太陽": "Sun", "月": "Moon", "水星": "Mercury", "金星": "Venus",
        "火星": "Mars", "木星": "Jupiter", "土星": "Saturn", "天王星": "Uranus",
        "海王星": "Neptune", "冥王星": "Pluto", "ドラゴンヘッド": "North Node",
        "ドラゴンテイル": "South Node", "キロン": "Chiron",
        "コンジャンクション": "Conjunction", "オポジション": "Opposition",
        "トライン": "Trine", "スクエア": "Square", "セクスタイル": "Sextile",
        "クインカンクス": "Quincunx",
        "ドミサイル": "Domicile", "エグザルテーション": "Exaltation",
        "デトリメント": "Detriment", "フォール": "Fall",
        "5度前ルール適用": "5-degree rule applied",
        "出生時間不明のためハウス除外": "Houses excluded due to unknown birth time",
    }
    for i in range(12, 0, -1):
        suffix = "st" if i == 1 else "nd" if i == 2 else "rd" if i == 3 else "th"
        translations[f"第{i}ハウス"] = f"{i}{suffix} House"
    for jp, en in translations.items():
        text = text.replace(jp, en)
    return text

def render_user_input_form(prefix, default_name, show_header=True):
    if show_header:
        header_text = t["p1_header"] if prefix == "p1" else t["p2_header"]
        st.subheader(header_text)
    
    user_name = st.text_input(t["name_input"], value=default_name, key=f"{prefix}_user_name_input")
    
    default_birth_time = datetime.time(12, 0)
    birth_date = st.date_input(t["birth_date"], value=datetime.date(2000, 1, 1), min_value=datetime.date(1900, 1, 1), max_value=datetime.date(2100, 12, 31), key=f"{prefix}_birth_date_input")
    birth_time = st.time_input(t["birth_time"], value=default_birth_time, key=f"{prefix}_birth_time_input")

    selected_pref = st.selectbox(t["pref_select"], PREFECTURES, index=0, key=f"{prefix}_pref_select_input")
    
    available_cities = get_cities_for_prefecture(selected_pref) if selected_pref != t["pref_default"] else []
    
    if selected_pref == "海外・その他":
        input_city_name = st.text_input(t["city_input"], value="ロンドン", key=f"{prefix}_city_input_text_overseas")
    elif available_cities:
        input_city_name = st.selectbox(t["city_input"], available_cities, index=0, key=f"{prefix}_city_select_jp")
    else:
        input_city_name = st.text_input(t["city_input"], value="", placeholder="先に都道府県を選択してください" if lang=="日本語" else "Please select a prefecture first", key=f"{prefix}_city_input_empty")

    is_valid, err_msg, lat_res, lng_res = False, "", None, None
    
    if selected_pref != t["pref_default"]:
        is_valid, err_msg, lat_res, lng_res = validate_and_get_coords(selected_pref, input_city_name)

    if selected_pref == t["pref_default"]:
        st.markdown(f"<p style='color: #ff4b4b; font-size: 0.82em; margin-top: -8px; margin-bottom: 8px;'>⚠️ {t['invalid_pref_error']}</p>", unsafe_allow_html=True)
    elif not is_valid and selected_pref != "海外・その他":
        st.markdown(f"<p style='color: #ff4b4b; font-size: 0.82em; margin-top: -8px; margin-bottom: 8px;'>⚠️ {t['invalid_loc_error']}</p>", unsafe_allow_html=True)

    lat_key = f"{prefix}_lat_number_input"
    lng_key = f"{prefix}_lng_number_input"

    if is_valid and lat_res is not None and lng_res is not None:
        st.session_state[f"{prefix}_input_lat_val"] = lat_res
        st.session_state[f"{prefix}_input_lng_val"] = lng_res
        st.session_state[lat_key] = lat_res
        st.session_state[lng_key] = lng_res
    
    if f"{prefix}_input_lat_val" not in st.session_state: st.session_state[f"{prefix}_input_lat_val"] = 36.1243
    if f"{prefix}_input_lng_val" not in st.session_state: st.session_state[f"{prefix}_input_lng_val"] = 139.5983

    input_lat = st.number_input(t["lat_input"], value=st.session_state[f"{prefix}_input_lat_val"], format="%.4f", key=lat_key)
    input_lng = st.number_input(t["lng_input"], value=st.session_state[f"{prefix}_input_lng_val"], format="%.4f", key=lng_key)

    st.caption("※1 緯度・経度は十進数表記です" if lang == "日本語" else "* Please enter coordinates in decimal degrees")
    st.markdown("---")

    return {
        "user_name": user_name,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "selected_pref": selected_pref,
        "input_city_name": input_city_name,
        "input_lat": input_lat,
        "input_lng": input_lng,
        "is_valid": is_valid
    }

with st.sidebar:
    st.header(t["sidebar_header"])
    
    chart_mode_raw = st.selectbox(t["mode_select"], t["mode_options"], key="chart_mode_select")
    is_synastry = chart_mode_raw in ["シナストリー（相性）", "Synastry (Compatibility)"]
    is_transit = chart_mode_raw in ["トランジット（現在の運気）", "Transit"]

    if is_transit:
        with st.expander("トランジット日時設定", expanded=True):
            transit_date = st.date_input("トランジット日付", value=datetime.date.today())
            transit_time = st.time_input("トランジット時刻", value=datetime.datetime.now().time())
        transit_lat = 35.69
        transit_lng = 139.76
    
    st.markdown("---")

    p1_data = render_user_input_form("p1", "TestUser1", show_header=is_synastry)

    p2_data = None
    if is_synastry:
        p2_data = render_user_input_form("p2", "TestUser2", show_header=True)

    st.header(t["settings_header"])
    toggle_view_raw = st.radio(t["aspect_view_label"], t["aspect_view_options"], key="aspect_view_radio")
    toggle_view = "ペア別" if toggle_view_raw in ["ペア別", "By Pair"] else "アスペクト別"
    unknown_checkbox = st.checkbox(t["unknown_time_checkbox"], key="unknown_time_chk")

    submit_button = st.button(label=t["submit_btn"], type="primary", key="submit_btn_main")

if submit_button:
    p1_error = False
    if p1_data["selected_pref"] == t["pref_default"]:
        st.error(f"1人目: {t['invalid_pref_error']}")
        p1_error = True
    elif not p1_data["is_valid"] and p1_data["selected_pref"] != "海外・その他":
        st.error(f"1人目: {t['invalid_loc_error']}")
        p1_error = True

    p2_error = False
    if is_synastry and p2_data:
        if p2_data["selected_pref"] == t["pref_default"]:
            st.error(f"2人目: {t['invalid_pref_error']}")
            p2_error = True
        elif not p2_data["is_valid"] and p2_data["selected_pref"] != "海外・その他":
            st.error(f"2人目: {t['invalid_loc_error']}")
            p2_error = True

    if not p1_error and not p2_error:
        with st.spinner(t["loading"]):
            transit_info = None
            if is_transit:
                transit_info = {
                    "year": transit_date.year,
                    "month": transit_date.month,
                    "day": transit_date.day,
                    "hour": transit_time.hour,
                    "minute": transit_time.minute,
                    "lat": 35.69,
                    "lng": 139.76
                }

        if is_synastry:
            if get_synastry_data is not None:
                p1_info = {
                    "name": p1_data["user_name"],
                    "year": p1_data["birth_date"].year,
                    "month": p1_data["birth_date"].month,
                    "day": p1_data["birth_date"].day,
                    "hour": p1_data["birth_time"].hour,
                    "minute": p1_data["birth_time"].minute,
                    "lat": p1_data["input_lat"],
                    "lng": p1_data["input_lng"],
                    "city": p1_data["input_city_name"],
                    "is_unknown_time": unknown_checkbox
                }
                p2_info = {
                    "name": p2_data["user_name"],
                    "year": p2_data["birth_date"].year,
                    "month": p2_data["birth_date"].month,
                    "day": p2_data["birth_date"].day,
                    "hour": p2_data["birth_time"].hour,
                    "minute": p2_data["birth_time"].minute,
                    "lat": p2_data["input_lat"],
                    "lng": p2_data["input_lng"],
                    "city": p2_data["input_city_name"],
                    "is_unknown_time": unknown_checkbox
                }
                data = get_synastry_data(p1_info, p2_info, mode=lang)
            else:
                data = get_chart_data(
                    p1_data["user_name"], 
                    p1_data["birth_date"].year, p1_data["birth_date"].month, p1_data["birth_date"].day,
                    p1_data["birth_time"].hour, p1_data["birth_time"].minute, 
                    p1_data["input_lat"], p1_data["input_lng"],
                    p1_data["input_city_name"], lang, toggle_view, unknown_checkbox,
                    transit_info=transit_info
                )
        else:
            data = get_chart_data(
                p1_data["user_name"], 
                p1_data["birth_date"].year, p1_data["birth_date"].month, p1_data["birth_date"].day,
                p1_data["birth_time"].hour, p1_data["birth_time"].minute, p1_data["input_lat"], p1_data["input_lng"],
                p1_data["input_city_name"], lang, toggle_view, unknown_checkbox,
                transit_info=transit_info
            )

        if data.get("error"):
            st.error(data["error"])
        else:
            st.session_state.chart_data = data
            st.session_state.user_name = p1_data["user_name"]
            st.session_state.is_synastry = is_synastry
            st.session_state.is_transit = is_transit
            if is_synastry and p2_data:
                st.session_state.p2_name = p2_data["user_name"]

if "chart_data" in st.session_state:
    data = st.session_state.chart_data
    u_name = st.session_state.get("user_name", "TestUser")
    current_is_synastry = st.session_state.get("is_synastry", False)
    current_is_transit = st.session_state.get("is_transit", False)
    p2_name = st.session_state.get("p2_name", "TestUser2")

    if current_is_synastry:
        st.markdown(f"""
        <div style="padding: 20px; border: 2px solid #D4AF37; border-radius: 12px; background: linear-gradient(135deg, rgba(212,175,55,0.05), rgba(75,0,130,0.05)); text-align: center; margin-bottom: 25px;">
            <h2 style="margin: 0; color: #B8860B;">✨ {u_name} & {p2_name} ✨</h2>
        </div>
        """, unsafe_allow_html=True)
        
        if isinstance(data, dict) and "bodies" in data:
            for item in data["bodies"]:
                st.markdown(f"- {localize_text(convert_to_dms(item), lang)}")
        else:
            st.write(data)
        
        if isinstance(data, dict) and "bodies" in data:
            for item in data["bodies"]:
                st.markdown(f"- {localize_text(convert_to_dms(item), lang)}")
        else:
            st.write(data)

    else:
        display_loc_str = data['loc_str']
        if lang != "日本語":
            display_loc_str = display_loc_str.replace("北緯", "N").replace("東経", "E").replace("十進:", "Decimal:")

        st.markdown(f"""
        <div style="padding: 20px; border: 2px solid #D4AF37; border-radius: 12px; background: linear-gradient(135deg, rgba(212,175,55,0.05), rgba(75,0,130,0.05)); text-align: center; margin-bottom: 25px;">
            <h2 style="margin: 0; color: #B8860B;">✨ {u_name} {"さんのホロスコープ" if lang=="日本語" else "'s Horoscope Reading"} ✨</h2>
            <p style="margin: 10px 0 0 0; font-size: 1.1em; color: #555;">📅 {data['date_str']}<br>📍 {display_loc_str}</p>
        </div>
        """, unsafe_allow_html=True)

    if current_is_transit and data.get("transit"):
        st.divider()
        st.subheader("トランジット分析結果")
        st.write(f"対象日時: {data['transit']['transit_date']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 👤 ネイタル天体配置")
            for body in data["bodies"]:
                st.markdown(body)
        with col2:
            st.markdown("### 🌌 ネイタルへのトランジット影響")
            if data["transit"]["transit_aspects"]:
                for aspect in data["transit"]["transit_aspects"]:
                    st.markdown(f"- {aspect}")
            else:
                st.info("現在、顕著なトランジット・アスペクトはありません。")
        
        st.stop()

        if data["angles"]:
            col_a1, col_a2 = st.columns(2)
            col_a1.info(localize_text(convert_to_dms(data["angles"][0]), lang))
            col_a2.info(localize_text(convert_to_dms(data["angles"][1]), lang))
            st.write("")

    ruler_tab_label = "🗝️ハウスルーラー" if lang == "日本語" else "🗝️House Rulers"
    midpoint_tab_label = "🎯ミッドポイント" if lang == "日本語" else "🎯Midpoints"
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        t["bodies_tab"], t["houses_tab"], t["aspects_tab"], 
        t["patterns_tab"], ruler_tab_label, midpoint_tab_label
    ])

    with tab1:
        for p in data["bodies"]:
            st.markdown(f"- {localize_text(convert_to_dms(p), lang)}", unsafe_allow_html=True)

    with tab2:
        for h in data["houses"]:
            st.markdown(f"- {localize_text(convert_to_dms(h), lang)}")

    with tab3:
        converted_aspects = localize_text(convert_to_dms(data["aspects"]), lang)
        aspect_lines = [l.strip() for l in converted_aspects.strip().split("\n") if l.strip()]
        current_planet = None
        for line in aspect_lines:
            if " & " in line:
                raw_target = line.lstrip("-* ").strip()
                planet = raw_target.split(" & ")[0].strip()
                if planet != current_planet:
                    current_planet = planet
                    heading_prefix = "Aspects of" if lang != "日本語" else "のアスペクト"
                    st.markdown(f"\n#### 🌟 {current_planet} {heading_prefix}")
            st.markdown(line)

    with tab4:
        if data["patterns"]:
            for pat in data["patterns"]:
                st.success(localize_text(convert_to_dms(pat), lang))
        else:
            st.info("*(該当する複合アスペクトはありません)*" if lang=="日本語" else "*(No complex aspects found)*")

    with tab5:
        if data.get("house_rulers"):
            ruler_mode_options = (
                ["5度前ルール適用なし", "5度前ルール適用あり"] 
                if lang == "日本語" 
                else ["Without 5-degree rule", "With 5-degree rule"]
            )
            ruler_mode_label = "表示モードを選択" if lang == "日本語" else "Select Display Mode"
            
            ruler_mode = st.radio(
                ruler_mode_label,
                ruler_mode_options,
                key="ruler_mode_radio"
            )
            st.write("")

            is_without_5deg = ruler_mode in ["5度前ルール適用なし", "Without 5-degree rule"]

            if is_without_5deg:
                target_rulers = data.get("house_rulers", [])
            else:
                target_rulers = data.get(
                    "house_rulers_type", data.get("house_rulers_with_5deg", data.get("house_rulers", []))
                )

            for r_line in target_rulers:
                formatted_line = (
                    r_line.replace("->", "→").replace("➡️", "→").strip()
                )
                if " → " in formatted_line:
                    separator = "：" if lang == "日本語" else ": "
                    formatted_line = formatted_line.replace(" → ", separator, 1)

                formatted_line = localize_text(formatted_line, lang)
                st.markdown(f"- {formatted_line}")
        else:
            st.info("*(出生時間不明のためハウスルーラー除外)*" if lang == "日本語" else "*(House rulers excluded due to unknown birth time)*")
            
    with tab6:
        st.caption("※1 主要な感受点・軸に対するミッドポイント・ヒット（オーブ1.5°以内）を表示します。" if lang=="日本語" else "*1 Displays midpoint hits to major points/axes (orb within 1.5°).")
        st.caption("※2 出生時間不明の場合、月・Asc・Mcを含む組み合わせは除外してあります。" if lang == "日本語" else "*2 Combinations including Moon, Asc, and MC are excluded if birth time is unknown.")
        midpoints_data = data.get("midpoints", [])
        if midpoints_data:
            for m_line in midpoints_data:
                clean_m = m_line.lstrip("- ").strip()
                st.markdown(f"- {localize_text(clean_m, lang)}")
        else:
            st.info("*(該当するミッドポイントデータはありません)*" if lang=="日本語" else "*(No midpoint data)*")

    st.divider()
    
    with st.expander("📋 結果をテキストで一括コピー / Copy All Results"):
            u_name = st.session_state.get("user_name", "TestUser")
            
            hide_dt_loc = st.checkbox(
                "日時と場所を非表示にする（除外する）" if lang == "日本語" else "Exclude Date, Time & Location",
                value=False,
                key="copy_hide_dt_loc"
            )
            
            def clean_html(text):
                if not isinstance(text, str):
                    return str(text)
                text = re.sub(r'<[^>]+>', '', text)
                text = text.replace('&nbsp;', '')
                text = text.replace('**', '').replace('`', '')
                text = localize_text(text, lang)
                return text

            copy_lines = []
            if lang == "日本語":
                copy_lines.append(f"【ホロスコープ鑑定データ: {u_name}】")
                
                if not hide_dt_loc:
                    copy_lines.append(f"日時: {data['date_str']}")
                    copy_lines.append(f"場所: {data['loc_str']}\n")
                else:
                    copy_lines.append("")

                if data["angles"]:
                    copy_lines.append("[アングル]")
                    for a in data["angles"]:
                        copy_lines.append(f"- {clean_html(a)}")
                    copy_lines.append("")
                
                copy_lines.append("[天体配置]")
                for b in data["bodies"]:
                    clean_b = clean_html(b)
                    clean_b = clean_b.replace("↳", " ↳ ")
                    copy_lines.append(f"- {clean_b}")
                    
                copy_lines.append("\n[12ハウス]")
                for h in data["houses"]:
                    copy_lines.append(f"- {clean_html(h)}")

                if data.get("house_rulers"):
                    ruler_mode = st.session_state.get("ruler_mode_radio", "5度前ルール適用なし")
                    copy_lines.append(f"\n[ハウスルーラー（{ruler_mode}）]")
                    
                    is_without = ruler_mode in ["5度前ルール適用なし", "Without 5-degree rule"]
                    target_rulers_for_copy = (
                        data.get("house_rulers", []) 
                        if is_without 
                        else data.get("house_rulers_with_5deg", data.get("house_rulers", []))
                    )
                    
                    for r_line in target_rulers_for_copy:
                        formatted_r = clean_html(r_line).replace('➡️', '->')
                        copy_lines.append(f"- {formatted_r}")

                copy_lines.append("\n[主要アスペクト]")
                clean_aspects = clean_html(data["aspects"]).replace("■ ", "")
                copy_lines.append(clean_aspects)

                if data["patterns"]:
                    copy_lines.append("\n[複合アスペクト]")
                    for pat in data["patterns"]:
                        copy_lines.append(f"- {clean_html(pat)}")

                midpoints_data = data.get("midpoints", [])
                if midpoints_data:
                    copy_lines.append("\n[ミッドポイント]")
                    for m_line in midpoints_data:
                        clean_m = clean_html(m_line).lstrip("- ").strip()
                        copy_lines.append(f"- {clean_m}")
            else:
                copy_lines.append(f"[Horoscope Reading Data: {u_name}]")
                
                if not hide_dt_loc:
                    copy_lines.append(f"Date & Time: {data['date_str']}")
                    copy_lines.append(f"Location: {display_loc_str}\n")
                else:
                    copy_lines.append("")

                if data["angles"]:
                    copy_lines.append("[Angles]")
                    for a in data["angles"]:
                        copy_lines.append(f"- {clean_html(a)}")
                    copy_lines.append("")
                
                copy_lines.append("[Celestial Bodies]")
                for b in data["bodies"]:
                    clean_b = clean_html(b)
                    clean_b = clean_b.replace("↳", " ↳ ")
                    copy_lines.append(f"- {clean_b}")
                    
                copy_lines.append("\n[12 Houses]")
                for h in data["houses"]:
                    copy_lines.append(f"- {clean_html(h)}")

                if data.get("house_rulers"):
                    ruler_mode_raw = st.session_state.get("ruler_mode_radio", "Without 5-degree rule")
                    if ruler_mode_raw in ["5度前ルール適用なし", "Without 5-degree rule"]:
                        ruler_mode_en = "Without 5-degree rule"
                    else:
                        ruler_mode_en = "With 5-degree rule"
                    
                    copy_lines.append(f"\n[House Rulers ({ruler_mode_en})]")
                    
                    is_without = ruler_mode_raw in ["5度前ルール適用なし", "Without 5-degree rule"]
                    target_rulers_for_copy = (
                        data.get("house_rulers", []) 
                        if is_without 
                        else data.get("house_rulers_with_5deg", data.get("house_rulers", []))
                    )
                    
                    for r_line in target_rulers_for_copy:
                        formatted_r = clean_html(r_line).replace('➡️', '->')
                        copy_lines.append(f"- {formatted_r}")

                copy_lines.append("\n[Main Aspects]")
                clean_aspects = clean_html(data["aspects"]).replace("■ ", "")
                copy_lines.append(clean_aspects)

                if data["patterns"]:
                    copy_lines.append("\n[Complex Patterns]")
                    for pat in data["patterns"]:
                        copy_lines.append(f"- {clean_html(pat)}")

                midpoints_data = data.get("midpoints", [])
                if midpoints_data:
                    copy_lines.append("\n[Midpoints]")
                    for m_line in midpoints_data:
                        clean_m = clean_html(m_line).lstrip("- ").strip()
                        copy_lines.append(f"- {clean_m}")

            st.code("\n".join(copy_lines), language="text")
            
            full_text = "\n".join(copy_lines)
            boms_text = "\ufeff" + full_text
            
            st.download_button(
                label="💾 テキストファイルとしてダウンロード / Download as text",
                data=boms_text,
                file_name=f"horoscope_{u_name}.txt",
                mime="text/plain;charset=utf-8"
            )
            
            st.divider()
            
            st.markdown(f"""
            <div style="background-color: var(--secondary-background-color); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid var(--border-color);">
            <h3 style="margin-top: 0; color: var(--text-color);">❕ 何かお気づきの点がありましたら</h3>
            <p style="color: var(--text-color);">今回のホロスコープのより詳しい解説は、noteの方で発信しています。</p>
            <a href="https://note.com/marroscorps" target="_blank" style="text-decoration: none; display: inline-block; margin-top: 15px;">
            <button style="background-color: #41d1a7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 290px;">
            noteをチェックする / Visit Note
            </button>
            </a>
            <br><br>
            <p style="color: var(--text-color); margin-bottom: 10px;">匿名での質問も可能です。詳しくは以下からどうぞ</p>
            <a href="https://note.com/qa/marroscorps" target="_blank" style="text-decoration: none; display: inline-block;">
            <button style="background-color: #41d1a7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 290px;">
            匿名で質問する / Ask anonymously
            </button>
            </a>
            </div>
            """, unsafe_allow_html=True)
            st.write("")
            
else:
        # 🌟 シナストリーモード用の表示（左右に分ける）
        st.markdown(f"""
        <div style="padding: 20px; border: 2px solid #D4AF37; border-radius: 12px; background: linear-gradient(135deg, rgba(212,175,55,0.05), rgba(75,0,130,0.05)); text-align: center; margin-bottom: 25px;">
        <h2 style="margin: 0; color: #B8860B;">✨ {u_name} & {p2_name} {"のシナストリー鑑定" if lang=="日本語" else "'s Synastry Reading"} ✨</h2>
        </div>
        """, unsafe_allow_html=True)

        synastry_tabs_labels = (
            ["🌟 2人分の天体配置", "🔗 2人分のアスペクト比較"] 
            if lang == "日本語" 
            else ["🌟 Celestial Bodies", "🔗 Aspects Comparison"]
        )
        stab1, stab2 = st.tabs(synastry_tabs_labels)

        # 🌟 安全なデータ取得用ヘルパー（ここで person1 / person2 を正しくキャッチ）
        p1_data = data.get("person1", data)
        p2_data = data.get("person2", {})

        with stab1:
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(f"#### 👤 {u_name}")
                p1_bodies = p1_data.get("bodies", [])
                for p in p1_bodies:
                    st.markdown(f"- {localize_text(convert_to_dms(p), lang)}", unsafe_allow_html=True)
            with col_r:
                st.markdown(f"#### 👤 {p2_name}")
                p2_bodies = p2_data.get("bodies", [])
                for p in p2_bodies:
                    st.markdown(f"- {localize_text(convert_to_dms(p), lang)}", unsafe_allow_html=True)

        with stab2:
            col_l, col_r = st.columns(2)
            
            def render_aspect_column(name, aspects_data):
                st.markdown(f"#### 👤 {name} " + ("のアスペクト" if lang=="日本語" else "'s Aspects"))
                if aspects_data and aspects_data is not Ellipsis:
                    if isinstance(aspects_data, str):
                        lines = [l.strip() for l in aspects_data.split("\n") if l.strip()]
                    elif isinstance(aspects_data, list):
                        lines = []
                        for item in aspects_data:
                            if item is not Ellipsis and str(item) != "Ellipsis":
                                if isinstance(item, str):
                                    lines.extend([l.strip() for l in item.split("\n") if l.strip()])
                                else:
                                    lines.append(str(item))
                    else:
                        lines = [str(aspects_data)]

                    valid_lines = [l for l in lines if l and str(l) != "Ellipsis"]
                    if valid_lines:
                        current_planet = None
                        for line in valid_lines:
                            converted_line = localize_text(convert_to_dms(line), lang)
                            if " & " in converted_line:
                                raw_target = converted_line.lstrip("-* ").strip()
                                planet = raw_target.split(" & ")[0].strip()
                                if planet != current_planet:
                                    current_planet = planet
                                    heading_prefix = "Aspects of" if lang != "日本語" else "のアスペクト"
                                    st.markdown(f"\n#### 🌟 {current_planet} {heading_prefix}")
                            st.markdown(converted_line if converted_line.startswith("-") else f"- {converted_line}")
                    else:
                        st.info("*(データなし)*" if lang=="日本語" else "*(No data)*")
                else:
                    st.info("*(データなし)*" if lang=="日本語" else "*(No data)*")

            with col_l:
                p1_aspects = p1_data.get("aspects", p1_data.get("person1_aspects", []))
                render_aspect_column(u_name, p1_aspects)

            with col_r:
                p2_aspects = p2_data.get("aspects", p2_data.get("person2_aspects", []))
                render_aspect_column(p2_name, p2_aspects)

        st.divider()

        with st.expander("📋 結果をテキストで一括コピー / Copy All Results"):
            def clean_html(text):
                if not isinstance(text, str):
                    return str(text)
                text = re.sub(r'<[^>]+>', '', text)
                text = text.replace('&nbsp;', '')
                text = text.replace('**', '').replace('`', '')
                text = localize_text(text, lang)
                return text

            copy_lines = []
            if lang == "日本語":
                copy_lines.append(f"【シナストリー鑑定データ: {u_name} & {p2_name}】\n")
                
                copy_lines.append(f"--- 👤 {u_name} の天体配置 ---")
                for p in p1_data.get("bodies", []):
                    copy_lines.append(f"- {clean_html(convert_to_dms(p))}")
                
                copy_lines.append(f"\n--- 👤 {u_name} のアスペクト ---")
                p1_asp = p1_data.get("aspects", p1_data.get("person1_aspects", []))
                if isinstance(p1_asp, list):
                    for a in p1_asp:
                        if a is not Ellipsis and str(a) != "Ellipsis":
                            copy_lines.append(f"- {clean_html(convert_to_dms(a))}")
                elif isinstance(p1_asp, str):
                    for line in p1_asp.split("\n"):
                        if line.strip():
                            copy_lines.append(f"- {clean_html(convert_to_dms(line))}")

                copy_lines.append(f"\n--- 👤 {p2_name} の天体配置 ---")
                for p in p2_data.get("bodies", []):
                    copy_lines.append(f"- {clean_html(convert_to_dms(p))}")

                copy_lines.append(f"\n--- 👤 {p2_name} のアスペクト ---")
                p2_asp = p2_data.get("aspects", p2_data.get("person2_aspects", []))
                if isinstance(p2_asp, list):
                    for a in p2_asp:
                        if a is not Ellipsis and str(a) != "Ellipsis":
                            copy_lines.append(f"- {clean_html(convert_to_dms(a))}")
                elif isinstance(p2_asp, str):
                    for line in p2_asp.split("\n"):
                        if line.strip():
                            copy_lines.append(f"- {clean_html(convert_to_dms(line))}")
            else:
                copy_lines.append(f"[Synastry Reading Data: {u_name} & {p2_name}]\n")
                
                copy_lines.append(f"--- 👤 {u_name}'s Celestial Bodies ---")
                for p in p1_data.get("bodies", []):
                    copy_lines.append(f"- {clean_html(convert_to_dms(p))}")
                
                copy_lines.append(f"\n--- 👤 {u_name}'s Aspects ---")
                p1_asp = p1_data.get("aspects", p1_data.get("person1_aspects", []))
                if isinstance(p1_asp, list):
                    for a in p1_asp:
                        if a is not Ellipsis and str(a) != "Ellipsis":
                            copy_lines.append(f"- {clean_html(convert_to_dms(a))}")
                elif isinstance(p1_asp, str):
                    for line in p1_asp.split("\n"):
                        if line.strip():
                            copy_lines.append(f"- {clean_html(convert_to_dms(line))}")

                copy_lines.append(f"\n--- 👤 {p2_name}'s Celestial Bodies ---")
                for p in p2_data.get("bodies", []):
                    copy_lines.append(f"- {clean_html(convert_to_dms(p))}")

                copy_lines.append(f"\n--- 👤 {p2_name}'s Aspects ---")
                p2_asp = p2_data.get("aspects", p2_data.get("person2_aspects", []))
                if isinstance(p2_asp, list):
                    for a in p2_asp:
                        if a is not Ellipsis and str(a) != "Ellipsis":
                            copy_lines.append(f"- {clean_html(convert_to_dms(a))}")
                elif isinstance(p2_asp, str):
                    for line in p2_asp.split("\n"):
                        if line.strip():
                            copy_lines.append(f"- {clean_html(convert_to_dms(line))}")

            st.code("\n".join(copy_lines), language="text")
            
            full_text = "\n".join(copy_lines)
            boms_text = "\ufeff" + full_text
            
            st.download_button(
                label="💾 テキストファイルとしてダウンロード / Download as text",
                data=boms_text,
                file_name=f"synastry_{u_name}_{p2_name}.txt",
                mime="text/plain;charset=utf-8"
            )
