import datetime
import os
import re
import pytz
import streamlit as st
from horoscope_calc import validate_and_get_coords, get_chart_data, EPHE_PATH, get_cities_for_prefecture

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

# 1. 言語選択はサイドバーで1つにまとめる
st.sidebar.markdown("### 🌐 Language / 言語")
lang = st.sidebar.radio("言語選択", ["日本語", "English"], label_visibility="collapsed", key="lang_radio")

# 2. 辞書の定義
ui_texts = {
    "日本語": {
        "page_title": "🔮 ホロスコープ作成システム",
        "disclaimer": "※ 計算ライブラリや基準点の設定により、ハウス等の数値にわずかな誤差が生じる場合があります。",
        "sidebar_header": "📝 出生データ入力",
        "name_input": "お名前 / ラベル",
        "birth_date": "生年月日",
        "birth_time": "出生時間（日本時間）",
        "pref_select": "都道府県",
        "pref_default": "県名を選択してください",
        "city_input": "市区町村・地名 (例: 古河市)",
        "lat_input": "緯度 (Latitude)",
        "lng_input": "経度 (Longitude)",
        "settings_header": "⚙️ 表示設定",
        "aspect_view_label": "アスペクト表示形式:",
        "aspect_view_options": ["ペア別", "アスペクト別"],
        "unknown_time_checkbox": "出生時間が分からない（12:00仮定 / ハウス除外）",
        "submit_btn": "✨ ホロスコープを作る",
        "loading": "星々の配置を精密に計算中... 🌌✨",
        "bodies_tab": "🌟 天体 ＋ 感受点",
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
        "name_input": "Name / Label",
        "birth_date": "Birth Date",
        "birth_time": "Birth Time",
        "pref_select": "Prefecture",
        "pref_default": "Please select a prefecture",
        "city_input": "City / Location Name",
        "lat_input": "Latitude",
        "lng_input": "Longitude",
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

# 3. 選択された言語に基づいて `t` を決定
t = ui_texts[lang]

# 4. メイン画面のタイトルと注釈を綺麗に表示する
st.markdown(f"# {t['page_title']}")
st.caption(t["disclaimer"])

PREFECTURES = [t["pref_default"]] + BASE_PREFECTURES

def convert_to_dms(text):
    """
    (16.30°) のような10進数の度数表記を (16°18') の60進数表記に変換する関数
    """
    def replace_deg(match):
        val = float(match.group(1))
        deg = int(val)
        min_val = round((val - deg) * 60)
        if min_val == 60:
            deg += 1
            min_val = 0
        return f"({deg}°{min_val:02d}')"
    
    return re.sub(r'\((\d+\.\d+)°\)', replace_deg, text)
    
with st.sidebar:
    st.header(t["sidebar_header"])
    user_name = st.text_input(t["name_input"], value="TestUser", key="user_name_input")
    
    st.markdown(f"<label style='font-size: 14px; font-weight: 600;'>{t['birth_date']}</label>", unsafe_allow_html=True)
    
    col_y, col_m, col_d = st.columns([1.2, 1.1, 1.1])
    
    with col_y:
        years = list(range(1900, 2101))
        default_year_idx = years.index(2000) if 2000 in years else 0
        selected_year = st.selectbox("年", years, index=default_year_idx, label_visibility="collapsed", key="birth_year_sel")
        st.caption("年" if lang=="日本語" else "Year")
        
    with col_m:
        if lang == "日本語":
            months = [f"{m}月" for m in range(1, 13)]
        else:
            months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        selected_month_idx = st.selectbox("月", range(1, 13), format_func=lambda x: months[x-1], index=0, label_visibility="collapsed", key="birth_month_sel")
        st.caption("月" if lang=="日本語" else "Month")
        
    with col_d:
        if selected_month_idx in [1, 3, 5, 7, 8, 10, 12]:
            max_days = 31
        elif selected_month_idx in [4, 6, 9, 11]:
            max_days = 30
        else:
            y = selected_year
            is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
            max_days = 29 if is_leap else 28
            
        days = list(range(1, max_days + 1))
        current_d_val = st.session_state.get("birth_day_sel", 1)
        if current_d_val > max_days:
            current_d_val = 1
            
        weekdays_jp = ["日", "月", "火", "水", "木", "金", "土"]
        weekdays_en = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        
        def format_day_label(d_num):
            try:
                dt_obj = datetime.date(selected_year, selected_month_idx, d_num)
                w_idx = dt_obj.weekday()
                w_idx_sun = (w_idx + 1) % 7
                if lang == "日本語":
                    return f"{d_num}日 ({weekdays_jp[w_idx_sun]})"
                else:
                    return f"{d_num} ({weekdays_en[w_idx_sun]})"
            except:
                return str(d_num)

        selected_day = st.selectbox("日", days, index=min(current_d_val-1, len(days)-1), format_func=format_day_label, label_visibility="collapsed", key="birth_day_sel")
        st.caption("日" if lang=="日本語" else "Day")

    birth_date = datetime.date(selected_year, selected_month_idx, selected_day)

    default_birth_time = datetime.time(12, 0)
    birth_time = st.time_input(t["birth_time"], value=default_birth_time, key="birth_time_input")

    selected_pref = st.selectbox(t["pref_select"], PREFECTURES, index=0, key="pref_select_input")
    
    available_cities = get_cities_for_prefecture(selected_pref) if selected_pref != t["pref_default"] else []
    
    if selected_pref == "海外・その他":
        input_city_name = st.text_input(t["city_input"], value="ロンドン", key="city_input_text_overseas")
    elif available_cities:
        input_city_name = st.selectbox(t["city_input"], available_cities, index=0, key="city_select_jp")
    else:
        input_city_name = st.text_input(t["city_input"], value="", placeholder="先に都道府県を選択してください" if lang=="日本語" else "Please select a prefecture first", key="city_input_empty")

    is_valid, err_msg, lat_res, lng_res = False, "", None, None
    
    if selected_pref != t["pref_default"]:
        is_valid, err_msg, lat_res, lng_res = validate_and_get_coords(selected_pref, input_city_name)

    if selected_pref == t["pref_default"]:
        st.markdown(f"<p style='color: #ff4b4b; font-size: 0.82em; margin-top: -8px; margin-bottom: 8px;'>⚠️ {t['invalid_pref_error']}</p>", unsafe_allow_html=True)
    elif not is_valid and selected_pref != "海外・その他":
        st.markdown(f"<p style='color: #ff4b4b; font-size: 0.82em; margin-top: -8px; margin-bottom: 8px;'>⚠️ {t['invalid_loc_error']}</p>", unsafe_allow_html=True)

    if is_valid and lat_res is not None and lng_res is not None:
        st.session_state.input_lat_val = lat_res
        st.session_state.input_lng_val = lng_res
    
    if "input_lat_val" not in st.session_state: st.session_state.input_lat_val = 36.1243
    if "input_lng_val" not in st.session_state: st.session_state.input_lng_val = 139.5983

    input_lat = st.number_input(t["lat_input"], value=st.session_state.input_lat_val, format="%.4f", key="lat_number_input")
    input_lng = st.number_input(t["lng_input"], value=st.session_state.input_lng_val, format="%.4f", key="lng_number_input")

    st.caption("※1 緯度・経度は十進数表記です" if lang == "日本語" else "* Please enter coordinates in decimal degrees")

    st.markdown("---")
    st.header(t["settings_header"])
    toggle_view_raw = st.radio(t["aspect_view_label"], t["aspect_view_options"], key="aspect_view_radio")
    toggle_view = "ペア別" if toggle_view_raw in ["ペア別", "By Pair"] else "アスペクト別"
    unknown_checkbox = st.checkbox(t["unknown_time_checkbox"], key="unknown_time_chk")

    submit_button = st.button(label=t["submit_btn"], type="primary", key="submit_btn_main")

if submit_button:
    if selected_pref == t["pref_default"]:
        st.error(t["invalid_pref_error"])
    elif not is_valid and selected_pref != "海外・その他":
        st.error(t["invalid_loc_error"])
    else:
        with st.spinner(t["loading"]):
            data = get_chart_data(
                user_name, birth_date.year, birth_date.month, birth_date.day,
                birth_time.hour, birth_time.minute, input_lat, input_lng,
                input_city_name, lang, toggle_view, unknown_checkbox
            )

        if data.get("error"):
            st.error(data["error"])
        else:
            st.session_state.chart_data = data
            st.session_state.user_name = user_name

# セッションにデータが存在する場合に表示
if "chart_data" in st.session_state:
    data = st.session_state.chart_data
    u_name = st.session_state.get("user_name", "TestUser")

    st.markdown(f"""
    <div style="padding: 20px; border: 2px solid #D4AF37; border-radius: 12px; background: linear-gradient(135deg, rgba(212,175,55,0.05), rgba(75,0,130,0.05)); text-align: center; margin-bottom: 25px;">
        <h2 style="margin: 0; color: #B8860B;">✨ {u_name} {"さんのホロスコープ" if lang=="日本語" else "'s Horoscope Reading"} ✨</h2>
        <p style="margin: 10px 0 0 0; font-size: 1.1em; color: #555;">📅 {data['date_str']}<br>📍 {data['loc_str']}</p>
    </div>
    """, unsafe_allow_html=True)

    if data["angles"]:
        col_a1, col_a2 = st.columns(2)
        col_a1.info(convert_to_dms(data["angles"][0]))
        col_a2.info(convert_to_dms(data["angles"][1]))
        st.write("")

    # タブの作成（全6タブ）
    ruler_tab_label = "ハウスルーラー" if lang == "日本語" else "House Rulers"
    midpoint_tab_label = "ミッドポイント" if lang == "日本語" else "Midpoints"
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        t["bodies_tab"], t["houses_tab"], t["aspects_tab"], 
        t["patterns_tab"], ruler_tab_label, midpoint_tab_label
    ])

    with tab1:
        for p in data["bodies"]:
            st.markdown(f"- {convert_to_dms(p)}", unsafe_allow_html=True)

    with tab2:
        for h in data["houses"]:
            st.markdown(f"- {convert_to_dms(h)}")

    with tab3:
        converted_aspects = convert_to_dms(data["aspects"])
        aspect_lines = [l.strip() for l in converted_aspects.strip().split("\n") if l.strip()]
        current_planet = None
        for line in aspect_lines:
            if " & " in line:
                raw_target = line.lstrip("-* ").strip()
                planet = raw_target.split(" & ")[0].strip()
                if planet != current_planet:
                    current_planet = planet
                    st.markdown(f"\n#### 🌟 {current_planet} のアスペクト")
            st.markdown(line)

    with tab4:
        if data["patterns"]:
            for pat in data["patterns"]:
                st.success(convert_to_dms(pat))
        else:
            st.info("*(該当する複合アスペクトはありません)*" if lang=="日本語" else "*(No complex aspects found)*")

    # 🌟 ハウスルーラーのタブ（重複をスッキリ整理）
    with tab5:
        if data.get("house_rulers"):
            ruler_mode = st.radio(
                "表示モードを選択",
                ["5度前ルール適用なし", "5度前ルール適用あり"],
                key="ruler_mode_radio"
            )
            st.write("")

            if ruler_mode.startswith("5度前ルール適用なし"):
                target_rulers = data.get("house_rulers", [])
            else:
                target_rulers = data.get(
                    "house_rulers_with_5deg", data.get("house_rulers", [])
                )

            for r_line in target_rulers:
                formatted_line = r_line.replace("->", "→").replace("➡️", "→").strip()
                # 1. 「第1ハウス → 第1ハウス → 第11ハウス」のような重複を「第1ハウス → 第11ハウス」に整理
                formatted_line = re.sub(r'^(第\d+ハウス)\s*→\s*\1\s*→\s*', r'\1 → ', formatted_line)
                # 2. 「第8ハウス → 第8ハウス (ドミサイル)」のような1回で完結するものを「第8ハウス (ドミサイル)」に整理
                formatted_line = re.sub(r'^(第\d+ハウス)\s*→\s*\1(\s*\(.*\))$', r'\1\2', formatted_line)
                
                st.markdown(f"- {formatted_line}")
        else:
            st.info("*(出生時間不明のためハウスルーラー除外)*" if lang == "日本語" else "*(House rulers excluded due to unknown birth time)*")

    # 🌟 ミッドポイントのタブ
    with tab6:
        st.caption("主要な感受点・軸に対するミッドポイント・ヒット（オーブ1.5°以内）を表示します。")
        midpoints_data = data.get("midpoints", [])
        if midpoints_data:
            for m_line in midpoints_data:
                clean_m = m_line.lstrip("- ").strip()
                st.markdown(f"- {clean_m}")
        else:
            st.info("*(該当するミッドポイントデータはありません)*" if lang == "日本語" else "*(No midpoint data)*")

    st.divider()

    with st.expander("📋 結果をテキストで一括コピー / Copy All Results"):
        u_name = st.session_state.get("user_name", "TestUser")
        
        def clean_html(text):
            if not isinstance(text, str):
                return str(text)
            text = re.sub(r'<[^>]+>', '', text)
            text = text.replace('**', '').replace('`', '')
            return text

        copy_lines = []
        copy_lines.append(f"【ホロスコープ鑑定データ: {u_name}】")
        copy_lines.append(f"日時: {data['date_str']}")
        copy_lines.append(f"場所: {data['loc_str']}\n")

        if data["angles"]:
            copy_lines.append("[アングル]")
            for a in data["angles"]:
                copy_lines.append(f"- {clean_html(a)}")
            copy_lines.append("")
        
        copy_lines.append("[天体配置]")
        for b in data["bodies"]:
            clean_b = clean_html(b)
            clean_b = clean_b.replace("&nbsp;&nbsp;&nbsp;&nbsp;↳", " ↳ ")
            copy_lines.append(f"- {clean_b}")
            
        copy_lines.append("\n[12ハウス]")
        for h in data["houses"]:
            copy_lines.append(f"- {clean_html(h)}")

        if data.get("house_rulers"):
            ruler_mode = st.session_state.get("ruler_mode_radio", "5度前ルール適用なし")
            
            copy_lines.append(f"\n[ハウスルーラー（{ruler_mode}）]")
            
            target_rulers_for_copy = (
                data.get("house_rulers", []) 
                if ruler_mode.startswith("5度前ルール適用なし") 
                else data.get("house_rulers_with_5deg", data.get("house_rulers", []))
            )
            
            for r_line in target_rulers_for_copy:
                formatted_r = clean_html(r_line).replace('➡️', '->').replace('->', '→')
                formatted_r = re.sub(r'^(第\d+ハウス)\s*→\s*\1\s*→\s*', r'\1 → ', formatted_r)
                formatted_r = re.sub(r'^(第\d+ハウス)\s*→\s*\1(\s*\(.*\))$', r'\1\2', formatted_r)
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

        st.code("\n".join(copy_lines), language="text")
