import streamlit as st
import requests
import math
from bs4 import BeautifulSoup
from datetime import datetime

# --- 基礎工具函式 ---
def calculate_combinations(n, k):
    """計算 n 選 k 的組合數 (碰數)"""
    if n < k:
        return 0
    return math.comb(n, k)

# --- 1. 網頁基本配置 ---
st.set_page_config(page_title="539 專業管理系統", layout="wide")

# --- 全局字體加大 CSS ---
st.markdown("""
    <style>
    html, body, [class*="st-"] { font-size: 1.15rem; }
    .stMarkdown p { line-height: 1.8; }
    .stMarkdown span[style*="color: red"] { font-size: 1.3rem !important; font-weight: 900 !important; }
    [data-testid="stSidebar"] { font-size: 1.1rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 初始化 Session State ---
if 'page' not in st.session_state:
    st.session_state.page = "首頁"
if 'my_bets' not in st.session_state:
    st.session_state.my_bets = []
if 'reset_id' not in st.session_state:
    st.session_state.reset_id = 0

# --- 導覽函式 ---
def go_to(page_name):
    st.session_state.page = page_name
    st.rerun()

# ==========================================
# 🏠 首頁入口
# ==========================================
if st.session_state.page == "首頁":
    st.title("🎰 539 專業管理系統")
    st.write("### 請選擇功能模組：")
    st.divider()
    
    col1, col2 = st.columns(2)
    
    # 定義統一的文字顏色，避免白字看不見
    text_color = "#31333F" # 深灰色，安全色
    
    with col1:
        st.markdown(f"""
            <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #ddd;">
                <h1 style="font-size: 50px; margin-bottom: 0;">🔮</h1>
                <h3 style="color: {text_color}; margin-top: 10px;">號碼預測</h3>
                <p style="color: #555; font-size: 0.9rem;">大數據統計與熱門號碼分析</p>
            </div>
        """, unsafe_allow_html=True)
        st.write("") # 留一點間距
        if st.button("進入預測區 (開發中)", use_container_width=True):
            st.toast("預測功能開發中...")
        
    with col2:
        st.markdown(f"""
            <div style="background-color: #fff4f4; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #ffcccc;">
                <h1 style="font-size: 50px; margin-bottom: 0;">🏆</h1>
                <h3 style="color: {text_color}; margin-top: 10px;">即時對獎</h3>
                <p style="color: #555; font-size: 0.9rem;">自動抓取開獎號碼與損益計算</p>
            </div>
        """, unsafe_allow_html=True)
        st.write("") # 留一點間距
        if st.button("點擊進入對獎區", use_container_width=True):
            go_to("兌獎")

# ==========================================
# 🏆 兌獎區 (完整功能整合)
# ==========================================
elif st.session_state.page == "兌獎":
    # 頂部控制列
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ 返回首頁"):
            go_to("首頁")
    with col_title:
        st.title("📅 今彩 539 專業兌獎系統")

    # --- 2. 側邊欄：全局參數設定 (僅在兌獎頁顯示) ---
    st.sidebar.header("⚙️ 全局參數設定")
    st.sidebar.subheader("📉 成本 (本金) 設定")
    with st.sidebar.expander("🚗 坐車成本 (10元基準)", expanded=True):
        base_rate = 10 
        base_cost_val = st.sidebar.number_input(f"坐車 {base_rate} 元 = ? (成本)", value=304, step=1, key="sb_base_cost")
        per_unit_cost = base_cost_val / base_rate

    with st.sidebar.expander("💥 連碰成本設定 (折扣)", expanded=True):
        combo_discount = st.sidebar.number_input("連碰折扣 (預設 0.78)", value=0.78, step=0.01, format="%.2f", key="sb_combo_discount")

    st.sidebar.subheader("💰 獎金 (賠率) 設定")
    with st.sidebar.expander("🚗 坐車獎金", expanded=True):
        prize_car_base = st.sidebar.number_input(f"坐車 {base_rate} 元 = ? (獎金)", value=2120, step=10, key="sb_p_car")

    with st.sidebar.expander("💥 連碰獎金 (每 10 元倍率)", expanded=True):
        p_2star_val = st.sidebar.number_input("二星獎金 (10元/碰)", value=530, step=10, key="sb_p2")
        p_3star_val = st.sidebar.number_input("三星獎金 (10元/碰)", value=5700, step=100, key="sb_p3")
        p_4star_val = st.sidebar.number_input("四星獎金 (10元/碰)", value=800000, step=1000, key="sb_p4")

    # --- 3. 爬蟲邏輯 (抓取歷史號碼) ---
    def get_539_data_by_date(target_date):
        tmonth = target_date.strftime("%m")
        tday = target_date.strftime("%d")
        tyear_short = target_date.strftime("%y")
        target_str = f"{tmonth}/{tday}{tyear_short}"
        url = f"https://www.pilio.idv.tw/lto539/list.asp?year={target_date.year}&month={target_date.month}"
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            response.encoding = response.apparent_encoding 
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 2 and target_str in tds[0].get_text():
                    for td in tds:
                        val = td.get_text(strip=True)
                        if ',' in val:
                            parts = val.split(',')
                            if len(parts) == 5:
                                return sorted([int(n) for n in parts])
            return None 
        except: return None

    pick_date = st.date_input("請選擇開獎日期", value=datetime.now())
    draw_numbers = get_539_data_by_date(pick_date)

    if draw_numbers:
        st.success(f"✅ {pick_date} 開獎：{', '.join([f'{n:02d}' for n in draw_numbers])}")
    else:
        st.warning("🔍 找不到該日期資料")
        draw_numbers = []

    st.divider()

    # --- 4. 投注輸入區 (Tabs) ---
    st.subheader("🕹️ 選擇投注玩法")
    tab1, tab2, tab3 = st.tabs(["💥 連碰 (二三四星)", "🚗 坐車 (單選)", "🐾 坐尾數"])
    rid = st.session_state.reset_id

    with tab1:
        bet_combo = st.multiselect("選擇連碰號碼：", options=range(1, 40), format_func=lambda x: f"{x:02d}", key=f"ms_combo_{rid}")
        combo_amt = st.number_input("連碰下注金額 (倍率)", value=10, step=5, min_value=1, key=f"ni_combo_amt_{rid}")
        play_level = st.radio("選擇下注模式：", ["僅二星", "二三星連玩", "二三四星全連"], horizontal=True, key=f"combo_level_{rid}")
        
        if st.button("➕ 加入連碰下注", key="btn_combo"):
            n = len(bet_combo)
            if n < 2: st.warning("至少選 2 個號碼")
            else:
                p2, p3, p4 = calculate_combinations(n, 2), calculate_combinations(n, 3), calculate_combinations(n, 4)
                use_p2 = True
                use_p3 = True if "三星" in play_level or "四星" in play_level else False
                use_p4 = True if "四星" in play_level else False
                active_touches = (p2 if use_p2 else 0) + (p3 if use_p3 else 0) + (p4 if use_p4 else 0)
                total_cost = active_touches * (combo_amt * combo_discount)
                st.session_state.my_bets.append({
                    "type": "連碰", "subtype": play_level, "nums": sorted(bet_combo),
                    "bet_amount": combo_amt, "actual_cost": round(total_cost, 2),
                    "stars_bought": (use_p2, use_p3, use_p4),
                    "p2_count": p2 if use_p2 else 0, "p3_count": p3 if use_p3 else 0, "p4_count": p4 if use_p4 else 0
                })
                st.toast(f"已加入連碰，共 {active_touches} 碰")

    with tab2:
        bet_car = st.multiselect("選擇坐車號碼：", options=range(1, 40), format_func=lambda x: f"{x:02d}", key=f"ms_car_{rid}")
        car_amt = st.number_input("下注金額 (倍率)", value=10, step=5, key=f"ni_car_amt_{rid}")
        c_cost = round(len(bet_car) * (car_amt * per_unit_cost))
        if st.button("➕ 加入坐車", key="btn_car"):
            if not bet_car: st.warning("請選號碼")
            else:
                st.session_state.my_bets.append({"type": "坐車", "nums": sorted(bet_car), "bet_amount": car_amt, "actual_cost": c_cost})
                st.toast("已加入坐車")

    with tab3:
        tail_n = st.number_input("選擇尾數 (0-9)", 0, 9, 5, key=f"ni_tail_{rid}")
        tail_amt = st.number_input("尾數下注金額", value=10, step=5, key=f"ni_tail_amt_{rid}")
        tail_nos = [i * 10 + tail_n for i in range(4) if 1 <= i * 10 + tail_n <= 39]
        t_cost = round(len(tail_nos) * (tail_amt * per_unit_cost))
        if st.button("➕ 加入尾數", key="btn_tail"):
            st.session_state.my_bets.append({"type": f"{tail_n}尾", "nums": tail_nos, "bet_amount": tail_amt, "actual_cost": t_cost})
            st.toast("已加入尾數")

    # --- 5. 顯示下注清單 ---
    if st.session_state.my_bets:
        st.write("---")
        st.subheader("📝 我的下注清單")
        col_title, col_clear = st.columns([4, 1.2])
        with col_clear:
            if st.button("🗑️ 全部清除清單", use_container_width=True):
                st.session_state.my_bets = []
                st.session_state.reset_id += 1 
                st.rerun()

        for idx, bet in enumerate(st.session_state.my_bets):
            st.markdown("<div style='margin: 10px 0;'>", unsafe_allow_html=True)
            c1, c2 = st.columns([4, 1.2])
            
            # --- 修正後的標題邏輯 ---
            play_type = bet['type']
            subtype_str = f"({bet['subtype']})" if 'subtype' in bet else ""
            title = f"**【{play_type}{subtype_str}-{bet['bet_amount']}元】**"
            # ----------------------

            if play_type == "連碰":
                touch_details = []
                if bet.get('p2_count', 0) > 0: touch_details.append(f"2星{bet['p2_count']}碰")
                if bet.get('p3_count', 0) > 0: touch_details.append(f"3星{bet['p3_count']}碰")
                if bet.get('p4_count', 0) > 0: touch_details.append(f"4星{bet['p4_count']}碰")
                detail_info = f"(成本:{bet['actual_cost']}元 / {'、'.join(touch_details)})"
            else:
                detail_info = f"(成本:{bet['actual_cost']}元)"
            
            nums_str = ", ".join([f"{n:02d}" for n in bet['nums']])
            c1.markdown(f"#### {idx+1}. {title}: :red[**{nums_str}**]  \n&nbsp;&nbsp;&nbsp;&nbsp;{detail_info}")
            if c2.button("單項刪除", key=f"del_{idx}"):
                st.session_state.my_bets.pop(idx)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # --- 6. 全量對獎 ---
    if st.button("🚀 開始全量對獎"):
        if not draw_numbers: st.error("無開獎號碼")
        elif not st.session_state.my_bets: st.warning("清單為空")
        else:
            st.header("🏆 對獎結果明細")
            g_cost, g_prize = 0, 0
            for idx, bet in enumerate(st.session_state.my_bets):
                matched = sorted(list(set(bet['nums']) & set(draw_numbers)))
                count = len(matched)
                current_prize = 0
                g_cost += bet['actual_cost']
                with st.expander(f"組合 {idx+1}: 【{bet['type']}】 (中 {count} 碼)", expanded=True):
                    if count > 0:
                        st.success(f"🎯 對中號碼：{', '.join([f'{n:02d}' for n in matched])}")
                        mul = bet.get('bet_amount', 10) / 10
                        if "車" in bet['type'] or "尾" in bet['type']:
                            current_prize = mul * prize_car_base * count
                        elif bet['type'] == "連碰":
                            p2_w, p3_w, p4_w = calculate_combinations(count, 2), calculate_combinations(count, 3), calculate_combinations(count, 4)
                            h2, h3, h4 = bet['stars_bought']
                            p2_p = (p2_w * p_2star_val) * mul if h2 else 0
                            p3_p = (p3_w * p_3star_val) * mul if h3 else 0
                            p4_p = (p4_w * p_4star_val) * mul if h4 else 0
                            current_prize = p2_p + p3_p + p4_p
                            if p2_w > 0: st.write(f"🥈 二星：{p2_w} 碰" + (f" (獎金 ${p2_p:,.0f})" if h2 else " (未下注)"))
                            if p3_w > 0: st.write(f"🥇 三星：{p3_w} 碰" + (f" (獎金 ${p3_p:,.0f})" if h3 else " (未下注)"))
                            if p4_w > 0: st.write(f"💎 四星：{p4_w} 碰" + (f" (獎金 ${p4_p:,.0f})" if h4 else " (未下注)"))
                        g_prize += current_prize
                        st.markdown(f"#### 💰 中獎金額：${current_prize:,.0f}")
                    else: st.write("❌ 本組未中獎 (金額: $0)")

            st.divider()
            st.header("🏁 今日總結")
            f_profit = g_prize - g_cost
            ca, cb, cc = st.columns(3)
            ca.metric("總成本", f"${g_cost:,.1f}")
            cb.metric("總獎金", f"${g_prize:,.1f}")
            cc.metric("總最終損益", f"${f_profit:,.1f}", delta=float(f_profit))
            if f_profit > 0: st.balloons()