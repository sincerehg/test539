import streamlit as st
import requests
import math
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import itertools
import pandas as pd
import json  # 👈 用來處理詳細的下注資料

# ==========================================
# 🗄️ 資料庫初始化與工具函式
# ==========================================
st.set_page_config(layout="wide")

def calculate_combinations(n, k):
    if n < k: return 0
    return math.comb(n, k)

def get_tail_numbers(tail_digit):
    return [i * 10 + tail_digit for i in range(4) if 1 <= i * 10 + tail_digit <= 39]

def calculate_lizhu_touches(counts, star_level):
    if len(counts) < star_level: return 0
    total = 0
    for combo in itertools.combinations(counts, star_level):
        prod = 1
        for c in combo: prod *= c
        total += prod
    return total

# ==========================================
# 💡 老弟特製版：X光掃描法 (無視網頁排版，強制抓取)
# ==========================================
@st.cache_data(ttl=600)  # 快取 10 分鐘，不卡頓
def get_recent_100_draws():
    import re # 引入正則表達式模組
    results = []
    session = requests.Session()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # 雙重保險：BIG 版抓不到就抓標準版
    urls = [f"https://www.pilio.idv.tw/lto539/list539BIG.asp?indexpage={i}&orderby=new" for i in range(1, 4)]
    urls += [f"https://www.pilio.idv.tw/lto539/list.asp?indexpage={i}&orderby=new" for i in range(1, 4)]
    
    for url in urls:
        if len(results) >= 100: break # 抓滿 100 筆就停
        try:
            r = session.get(url, headers=headers, timeout=10)
            try: html_text = r.content.decode('big5')
            except: html_text = r.content.decode('utf-8', errors='ignore')
                
            soup = BeautifulSoup(html_text, "html.parser")
            
            # 掃描每一行
            for row in soup.find_all("tr"):
                row_text = row.get_text(separator=' ', strip=True)
                
                # 1. 找日期 (特徵：YYYY/MM/DD)
                date_match = re.search(r'(\d{4}/\d{2}/\d{2})', row_text)
                if not date_match: continue
                dt_str = date_match.group(1)
                
                # 2. 找號碼 (特徵：5個 2位數)
                nums = []
                for cell in row.find_all(['td', 'span', 'div', 'font']):
                    # 把所有的逗號、全形頓號、隱藏空白全部變成普通空白
                    c_text = cell.get_text(strip=True).replace(',', ' ').replace('、', ' ').replace('\xa0', ' ')
                    
                    # 把字串切開，只要長度是 2 且都是數字的，就收起來
                    tokens = [t for t in c_text.split() if t.isdigit() and len(t) == 2]
                    
                    if len(tokens) >= 5: # 成功抓到至少 5 個號碼
                        nums = sorted([int(t) for t in tokens[:5]])
                        break
                        
                    # 防呆：如果網頁把數字黏在一起 (例如 0102030405)
                    if len(c_text) == 10 and c_text.isdigit():
                        nums = sorted([int(c_text[k:k+2]) for k in range(0, 10, 2)])
                        break
                        
                # 確保有抓到且不重複
                if len(nums) == 5 and not any(d == dt_str for d, n in results):
                    results.append((dt_str, nums))
        except Exception as e:
            continue
            
    return results

# --- 1. 網頁基本配置 ---
st.set_page_config(page_title="539 專業管理系統", layout="wide")

# 💡 第一步：修改 CSS 樣式區塊
# 💡 第一步：修正後的 CSS
# 💡 第一步：注入針對手機優化的計算機專屬 CSS
st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    </head>
    <style>
        /* 1. 液晶螢幕縮小，讓出更多空間給按鈕 */
        .calc-screen {
            background-color: #f0f2f6;
            color: #111111;
            padding: 5px 10px;
            border-radius: 8px;
            text-align: right;
            font-family: 'Courier New', Courier, monospace;
            font-size: clamp(18px, 5vw, 28px) !important;
            font-weight: 900;
            min-height: 50px;
            margin-bottom: 5px;
            border: 2px solid #b3b3b3;
        }
        .calc-res { font-size: 14px; color: #0055ff; }

        /* 2. 🔥 核心：強制計算機按鈕橫向排版不准換行 */
        [data-testid="stVerticalBlock"]:has(.calc-marker) [data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 2px !important; /* 縮小按鈕間的縫隙 */
        }

        /* 3. 強制每個按鈕佔滿比例，且絕對不准變大 */
        [data-testid="stVerticalBlock"]:has(.calc-marker) [data-testid="column"] {
            flex: 1 1 25% !important;
            min-width: 0 !important;
            max-width: 25% !important;
        }

        /* 4. 針對「3星、4星、結算」那排做特殊比例 */
        [data-testid="stVerticalBlock"]:has(.calc-marker) [data-testid="stHorizontalBlock"]:last-of-type [data-testid="column"]:last-child {
            flex: 2 1 50% !important;
            max-width: 50% !important;
        }

        /* 5. 縮小按鈕高度，讓畫面塞得進去 */
        [data-testid="stVerticalBlock"]:has(.calc-marker) button {
            height: 40px !important; /* 高度縮小 */
            font-size: 14px !important; /* 字體縮小 */
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* 6. 修復兌獎區勾選框間距 */
        div[data-testid="stCheckbox"] { margin-bottom: -10px !important; }
    </style>
    """, unsafe_allow_html=True)



# --- 初始化 Session State ---
if 'logged_in_user' not in st.session_state: st.session_state.logged_in_user = None
if 'page' not in st.session_state: st.session_state.page = "首頁"
if 'my_bets' not in st.session_state: st.session_state.my_bets = []
if 'reset_id' not in st.session_state: st.session_state.reset_id = 0
if 'show_result' not in st.session_state: st.session_state.show_result = False
if "history_df" not in st.session_state:
    import pandas as pd # 確保有載入 pandas
    st.session_state.history_df = pd.DataFrame()

def go_to(page_name):
    st.session_state.page = page_name
    st.session_state.show_result = False 
    st.rerun()

# ==========================================
# ☁️ Google Firebase 雲端資料庫初始化 (機密安全版)
# ==========================================
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import json

if not firebase_admin._apps:
    try:
        # 判斷是否在 Streamlit Cloud 雲端環境
        if "firebase" in st.secrets:
            # ☁️ 從 Streamlit 雲端機密保險箱讀取
            key_dict = json.loads(st.secrets["firebase"]["my_project_settings"])
            cred = credentials.Certificate(key_dict)
        else:
            # 💻 本地端電腦測試時，讀取實體檔案
            cred = credentials.Certificate('firebase_key.json')
            
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Firebase 初始化失敗，請檢查金鑰設定！錯誤訊息：{e}")
        st.stop()

db = firestore.client()

# ==========================================
# 🧮 計算機初始化與核心運算邏輯 (終極文字解析版)
# ==========================================
if 'calc_text' not in st.session_state: st.session_state.calc_text = ""
if 'calc_result' not in st.session_state: st.session_state.calc_result = ""

def handle_calc(key):
    import math
    import re
    
    # 💡 將粗體按鈕符號轉換為運算邏輯符號
    if key == '➕': key = '+'
    elif key == '➖': key = '-'
    elif key == '✖': key = '×'
    elif key == '➗': key = '÷'
    
    # 1. 處理清除鍵
    if key == 'C':
        st.session_state.calc_text = ""
        st.session_state.calc_result = ""
        return
        
    # 2. 處理回退鍵 (Backspace)
    if key == '⌫':
        if st.session_state.calc_result:
            st.session_state.calc_result = ""
        elif st.session_state.calc_text:
            if st.session_state.calc_text.endswith('星'):
                st.session_state.calc_text = st.session_state.calc_text[:-2]
            else:
                st.session_state.calc_text = st.session_state.calc_text[:-1]
        return
        
    # 3. 如果畫面上已經有答案
    if st.session_state.calc_result:
        if key in ['+', '-', '×', '÷']:
            try:
                if not any(k in st.session_state.calc_text for k in ['柱', '碰', '車', '星']):
                    val = eval(st.session_state.calc_text.replace('×', '*').replace('÷', '/'))
                    if isinstance(val, float) and val.is_integer(): val = int(val)
                    st.session_state.calc_text = str(val) + key
                else:
                    st.session_state.calc_text = key
            except:
                st.session_state.calc_text = key
        elif key != '=':
            st.session_state.calc_text = key
        st.session_state.calc_result = ""
        if key == '=': return

    # 4. 一般輸入 (累積字串)
    if key != '=':
        st.session_state.calc_text += key
        return
        
    # 5. 處理「=」結算邏輯
    text = st.session_state.calc_text
    if not text: return
    
    # 【模式 A】 539 專業模式
    if any(k in text for k in ['柱', '碰', '車', '星']):
        if '車' in text:
            cars = re.findall(r'(\d+)車', text)
            if not cars: 
                st.session_state.calc_result = "<span style='color:#ff4b4b;'>⚠️ 格式錯誤 (例: 5車)</span>"
                return
            n = int(cars[-1])
            if n > 39 or n < 1:
                st.session_state.calc_result = "<span style='color:#ff4b4b;'>⚠️ 號碼數量請介於 1~39</span>"
                return
            
            car_cost = 304 ; car_prize = 2120 
            total_cost = n * car_cost
            win_scenarios = []
            for hits in range(min(n, 5), 0, -1):
                prize = hits * car_prize
                win_scenarios.append(f"<span style='color:#555;'>若中 {hits} 顆</span> ➔ <span style='color:#ff0000; font-weight:bold;'>{prize:,} 元</span>")
            
            win_html = "<div style='margin-top:15px; border-top:2px dashed #ccc; padding-top:15px; font-size:22px; line-height:1.6; text-align:right;'>" + "<br>".join(win_scenarios) + "</div>"
            st.session_state.calc_result = f"買 {n} 個號碼坐車<br><span style='color:#0000ff; font-size:28px;'>總成本約 {total_cost:,} 元</span>{win_html}"

        elif '柱' in text:
            cols = [int(c) for c in re.findall(r'(\d+)柱', text)]
            stars = [int(s) for s in re.findall(r'(\d)星', text)]
            if len(cols) < 2:
                st.session_state.calc_result = "<span style='color:#ff4b4b;'>⚠️ 立柱至少需 2 柱</span>"
                return
            if any(c == 0 for c in cols):
                st.session_state.calc_result = "<span style='color:#ff4b4b;'>⚠️ 每柱至少需 1 個號碼</span>"
                return
            if not stars:
                st.session_state.calc_result = "<span style='color:#ff4b4b;'>⚠️ 請選擇星等</span>"
                return
                
            total_touches = 0; res_texts = []; prizes = {2: 530, 3: 5700, 4: 800000}
            for k in stars:
                touches = calculate_lizhu_touches(cols, k)
                res_texts.append(f"{k}星 x {touches:,}碰")
                total_touches += touches
            
            cost = math.ceil(total_touches * 10 * 0.78)
            res_str = "、".join(res_texts)
            win_scenarios = []
            for hits in range(min(len(cols), 5), 1, -1):
                scenario_prize = 0; scenario_texts = []
                for k in stars:
                    if hits >= k:
                        w_touches = calculate_combinations(hits, k)
                        if w_touches > 0:
                            scenario_prize += (w_touches * prizes[k])
                            scenario_texts.append(f"{k}星{w_touches}碰")
                if scenario_prize > 0:
                    win_scenarios.append(f"<span style='color:#555;'>中 {hits} 顆(皆不同柱)</span> ➔ <span style='color:#ff0000; font-weight:bold;'>{scenario_prize:,} 元</span>")
            
            win_html = "<div style='margin-top:15px; border-top:2px dashed #ccc; padding-top:15px; font-size:22px; line-height:1.6; text-align:right;'>" + "<br>".join(win_scenarios) + "</div>" if win_scenarios else ""
            st.session_state.calc_result = f"{res_str}<br><span style='color:#0000ff; font-size:28px;'>共 {total_touches:,} 碰 ➔ 成本約 {cost:,} 元</span>{win_html}"

        elif '碰' in text:
            nums = [int(n) for n in re.findall(r'(\d+)碰', text)]
            stars = [int(s) for s in re.findall(r'(\d)星', text)]
            if not nums:
                st.session_state.calc_result = "<span style='color:#ff4b4b;'>⚠️ 格式錯誤 (例: 5碰2星)</span>"
                return
            n = nums[-1] 
            if n < 2:
                st.session_state.calc_result = "<span style='color:#ff4b4b;'>⚠️ 連碰至少需 2 個號碼</span>"
                return
            if not stars:
                st.session_state.calc_result = "<span style='color:#ff4b4b;'>⚠️ 請選擇星等</span>"
                return
                
            total_touches = 0; res_texts = []; prizes = {2: 530, 3: 5700, 4: 800000}
            for k in stars:
                touches = calculate_combinations(n, k)
                res_texts.append(f"{k}星 x {touches:,}碰")
                total_touches += touches
            
            cost = math.ceil(total_touches * 10 * 0.78)
            res_str = "、".join(res_texts)
            win_scenarios = []
            for hits in range(min(n, 5), 1, -1):
                scenario_prize = 0; scenario_texts = []
                for k in stars:
                    if hits >= k:
                        w_touches = calculate_combinations(hits, k)
                        if w_touches > 0:
                            scenario_prize += (w_touches * prizes[k])
                            scenario_texts.append(f"{k}星{w_touches}碰")
                if scenario_prize > 0:
                    win_scenarios.append(f"<span style='color:#555;'>若中 {hits} 顆</span> ➔ <span style='color:#ff0000; font-weight:bold;'>{scenario_prize:,} 元</span>")
            
            win_html = "<div style='margin-top:15px; border-top:2px dashed #ccc; padding-top:15px; font-size:22px; line-height:1.6; text-align:right;'>" + "<br>".join(win_scenarios) + "</div>" if win_scenarios else ""
            st.session_state.calc_result = f"{res_str}<br><span style='color:#0000ff; font-size:28px;'>共 {total_touches:,} 碰 ➔ 成本約 {cost:,} 元</span>{win_html}"
    
    # 【模式 B】 一般數學模式
    else:
        try:
            math_text = text.replace('×', '*').replace('÷', '/')
            val = eval(math_text)
            if isinstance(val, float) and val.is_integer(): val = int(val)
            elif isinstance(val, float): val = round(val, 4) 
            # 💡 一般數學的答案也放大
            st.session_state.calc_result = f"<div style='font-size:45px; color:#ff0000; margin-top:15px; font-weight:900;'>{val:,}</div>"
        except Exception as e:
            st.session_state.calc_result = "<span style='color:#ff4b4b;'>⚠️ 數學公式錯誤</span>"
# ==========================================
# 🔒 登入與註冊系統
# ==========================================
if st.session_state.logged_in_user is None:
    st.title("🎰 歡迎使用 539 智多星系統")
    st.info("請先登入或註冊以儲存您的雲端損益紀錄")

    # 🌟 關鍵就是這一行，一定要在 with 之前！
    tab_login, tab_reg = st.tabs(["🔐 帳號登入", "📝 快速註冊"])

    # --- 註冊分頁 ---
    with tab_reg:
        with st.form("reg_form", clear_on_submit=False):
            r_user = st.text_input("設定帳號", key="r_user")
            r_nick = st.text_input("設定暱稱", key="r_nick") 
            r_pass = st.text_input("設定密碼", type="password", key="r_pass")
            if st.form_submit_button("註冊", use_container_width=True):
                if r_user and r_pass and r_nick:
                    user_ref = db.collection('users').document(r_user)
                    if user_ref.get().exists:
                        st.error("❌ 此帳號已被使用，請換一個！")
                    else:
                        user_ref.set({"password": r_pass, "nickname": r_nick})
                        st.success("✅ 註冊成功！請切換到登入頁面登入。")
                else:
                    st.warning("⚠️ 請輸入完整的註冊資料")

    # --- 登入分頁 ---
    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            l_user = st.text_input("帳號", key="l_user")
            l_pass = st.text_input("密碼", type="password", key="l_pass")
            if st.form_submit_button("登入", use_container_width=True):
                user_doc = db.collection('users').document(l_user).get()
                if user_doc.exists:
                    u_data = user_doc.to_dict()
                    if u_data['password'] == l_pass:
                        st.session_state.logged_in_user = l_user
                        st.session_state.nickname = u_data.get('nickname', l_user)
                        st.success("🎉 登入成功！")
                        time.sleep(1); st.rerun()
                    else:
                        st.error("❌ 密碼錯誤！")
                else:
                    st.error("❌ 帳號不存在！")

    st.stop() 

# ==========================================
# 🏠 首頁入口 (功能選單：改為 4 欄位，移除計算機 UI)
# ==========================================
if st.session_state.page == "首頁":
    display_name = st.session_state.get('nickname', st.session_state.logged_in_user)
    st.title(f"🎰 歡迎回來，{display_name}！")
    st.write("### 請選擇功能模組：")
    st.divider()
    
    # 💡 這裡將原本的 3 欄改為 4 欄
    col1, col2, col3, col4 = st.columns(4)
    text_color = "#31333F" 
    
    with col1:
        st.markdown(f'<div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #ddd;"><h1 style="margin-bottom: 0;">🔮</h1><h3 style="color: {text_color}; margin-top: 10px;">號碼預測</h3></div>', unsafe_allow_html=True)
        st.write("") 
        if st.button("進入預測區", use_container_width=True): go_to("預測")
    with col2:
        st.markdown(f'<div style="background-color: #fff4f4; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #ffcccc;"><h1 style="margin-bottom: 0;">🏆</h1><h3 style="color: {text_color}; margin-top: 10px;">即時對獎</h3></div>', unsafe_allow_html=True)
        st.write("") 
        if st.button("點擊進入對獎區", use_container_width=True): go_to("兌獎")
    with col3:
        st.markdown(f'<div style="background-color: #e6f9e6; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #b3e6b3;"><h1 style="margin-bottom: 0;">📊</h1><h3 style="color: {text_color}; margin-top: 10px;">個人損益表</h3></div>', unsafe_allow_html=True)
        st.write("") 
        if st.button("查看歷史紀錄", use_container_width=True): go_to("損益表")
    
    # 💡 新增：第四個按鈕進入「專業計算機」頁面
    with col4:
        st.markdown(f'<div style="background-color: #fffde6; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #eee8aa;"><h1 style="margin-bottom: 0;">🧮</h1><h3 style="color: {text_color}; margin-top: 10px;">專業計算機</h3></div>', unsafe_allow_html=True)
        st.write("") 
        if st.button("開啟試算機", use_container_width=True): go_to("計算機")
        
    st.divider()
    
    # 這裡只留下帳戶設定與登出，原本下方的計算機大區塊已經全部刪除
    c_set1, c_set2 = st.columns(2)
    with c_set1:
        if st.button("⚙️ 帳戶個人設定", use_container_width=True): go_to("帳戶設定")
    with c_set2:
        if st.button("🚪 登出系統", use_container_width=True):
            st.session_state.logged_in_user = None
            st.rerun()

# ==========================================
# 🧮 獨立計算機頁面區塊 (RWD 適配版結構)
# ==========================================
elif st.session_state.page == "計算機":
    # 💡 終極寬度爆發版：手機不動，電腦版按鈕「橫向增肌」
    st.markdown("""
    <style>
        /* 📱 手機版：維持完美現狀 (不動) */
        div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: repeat(4, 1fr) !important;
            gap: 4px !important; 
            width: 100% !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3):last-child {
            grid-column: span 2 !important;
        }
        div[data-testid="column"] { width: 100% !important; min-width: 0px !important; padding: 0 !important; }
        div[data-testid="stHorizontalBlock"] button { width: 100% !important; height: 60px !important; }
        div[data-testid="stHorizontalBlock"] button p { font-size: 20px !important; font-weight: 900 !important; }

        /* 💻 電腦版：解決「瘦長按鈕」的終極方案 */
        @media (min-width: 768px) {
            /* 1. 擴張主容器，給按鈕生長的空間 */
            .block-container, [data-testid="stMainBlockContainer"] {
                max-width: 1200px !important; 
            }
            
            /* 2. 🔥 核心：強迫每一格(Column)把左右寬度「撐滿」 */
            div[data-testid="column"] {
                padding: 0 1px !important; /* 間距縮到最小，只有 1px 縫隙 */
                flex: 1 1 auto !important;
            }

            /* 3. 🔥 關鍵：讓按鈕寬度直接「暴力橫向擴張」 */
            div[data-testid="stHorizontalBlock"] button {
                height: 90px !important;     /* 高度適中 */
                width: 100% !important;      /* 寬度填滿 */
                min-width: 200px !important; /* 👈 強制設定最小寬度！按鈕絕對會變寬，字就不會被壓縮！ */
                margin: 0 !important;
                border-radius: 10px !important;
            }
            
            /* 4. 字體放大並鎖定 */
            div[data-testid="stHorizontalBlock"] button p {
                font-size: 32px !important; 
                width: 100% !important;
                text-align: center !important;
            }
            
            /* 5. 液晶螢幕同步橫向擴張 */
            .calc-screen {
                font-size: 50px !important; 
                min-height: 100px;
                line-height: 80px;
                max-width: 100% !important;
            }
        }
    </style>
    """, unsafe_allow_html=True)

    if st.button("⬅️ 返回首頁"): go_to("首頁")

    st.subheader("🧮 539 雙效能智能計算機")

    with st.container():
        # (這裡不用再加 marker 了，直接套用上面的樣式)
        
        log_text = st.session_state.calc_text if st.session_state.calc_text else "0"
        # ... (下面繼續接你的 res_text = ... 還有按鈕們) ...
        res_text = f"<div class='calc-res'>{st.session_state.calc_result}</div>" if st.session_state.calc_result else ""
        st.markdown(f"<div class='calc-screen'>{log_text}{res_text}</div>", unsafe_allow_html=True)
        
        # 鍵盤佈局 (每一排 st.columns(4) 都會被 CSS 強制鎖定在同一橫排)
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        r1c1.button("7", on_click=handle_calc, args=("7",), use_container_width=True)
        r1c2.button("8", on_click=handle_calc, args=("8",), use_container_width=True)
        r1c3.button("9", on_click=handle_calc, args=("9",), use_container_width=True)
        r1c4.button("⌫", on_click=handle_calc, args=("⌫",), use_container_width=True)
        
        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        r2c1.button("4", on_click=handle_calc, args=("4",), use_container_width=True)
        r2c2.button("5", on_click=handle_calc, args=("5",), use_container_width=True)
        r2c3.button("6", on_click=handle_calc, args=("6",), use_container_width=True)
        r2c4.button("C", on_click=handle_calc, args=("C",), use_container_width=True)
            
        r3c1, r3c2, r3c3, r3c4 = st.columns(4)
        r3c1.button("1", on_click=handle_calc, args=("1",), use_container_width=True)
        r3c2.button("2", on_click=handle_calc, args=("2",), use_container_width=True)
        r3c3.button("3", on_click=handle_calc, args=("3",), use_container_width=True)
        r3c4.button("➗", on_click=handle_calc, args=("➗",), use_container_width=True)
        
        r4c1, r4c2, r4c3, r4c4 = st.columns(4)
        r4c1.button("0", on_click=handle_calc, args=("0",), use_container_width=True)
        r4c2.button("✖", on_click=handle_calc, args=("✖",), use_container_width=True)
        r4c3.button("➖", on_click=handle_calc, args=("➖",), use_container_width=True)
        r4c4.button("➕", on_click=handle_calc, args=("➕",), use_container_width=True)
        
        r5c1, r5c2, r5c3, r5c4 = st.columns(4)
        r5c1.button("柱", on_click=handle_calc, args=("柱",), use_container_width=True, type="primary")
        r5c2.button("碰", on_click=handle_calc, args=("碰",), use_container_width=True, type="primary")
        r5c3.button("車", on_click=handle_calc, args=("車",), use_container_width=True, type="primary")
        r5c4.button("2星", on_click=handle_calc, args=("2星",), use_container_width=True, type="primary")
        
        r6c1, r6c2, r6c3 = st.columns([1, 1, 2])
        r6c1.button("3星", on_click=handle_calc, args=("3星",), use_container_width=True, type="primary")
        r6c2.button("4星", on_click=handle_calc, args=("4星",), use_container_width=True, type="primary")
        with r6c3:
             st.button("🟰 結算", on_click=handle_calc, args=("=",), use_container_width=True, type="primary")

    with st.expander("💡 查看計算機指令教學", expanded=False):
        st.info("🔸 一般連碰：`5` `碰` `2星` `3星` `=` \n🔸 立柱玩法：`3` `柱` `4` `柱` `2星` `=` \n🔸 坐車試算：`5` `車` `=`")

elif st.session_state.page == "預測":
    if st.button("⬅️ 返回首頁"): go_to("首頁")

    # ==========================================
    # 🌟 新增：最上方「最新開出獎號」展示與手動更新
    # ==========================================
    with st.spinner("⏳ 正在取得最新開獎數據..."):
        # 💡 先讀取資料，把最新的號碼抓出來
        raw_draws = get_recent_100_draws()

    if raw_draws:
        latest_date, latest_nums = raw_draws[0] # 抓出最新一期的日期與號碼
        
        st.markdown(f"#### 🎰 本期最新開出獎號 ({latest_date})")
        
        # 佈局：左邊放球，右邊放更新按鈕 (比例 3:1)
        c_balls, c_btn = st.columns([3, 1])
        
        with c_balls:
            # 💡 用 CSS 畫出超逼真的圓形獎球 (黃底黑字)
            balls_html = "".join([f"<div style='display:inline-block; width: 45px; height: 45px; line-height: 45px; text-align: center; border-radius: 50%; background-color: #ffcc00; color: #111; font-weight: 900; font-size: 20px; margin: 0 4px; box-shadow: 2px 2px 5px rgba(0,0,0,0.2);'>{n:02d}</div>" for n in latest_nums])
            st.markdown(f"<div style='padding-top: 5px;'>{balls_html}</div>", unsafe_allow_html=True)
            
        with c_btn:
            # 推一點空白，讓按鈕乖乖對齊到右下方
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 更新號碼", use_container_width=True):
                get_recent_100_draws.clear()  # 💡 殺掉 Streamlit 的舊快取
                st.rerun()                    # 重新整理網頁，強制重新抓取

        st.write("---") # 畫一條分隔線區隔下方預測區

    # ==========================================
    # 原本的預測區標題與資料轉換
    # ==========================================
    st.subheader("🤖 專業大數據預測與趨勢分析")

    # 把它轉換成預測區需要的格式
    all_draws = []
    if raw_draws:
        for dt, nums in raw_draws:
            all_draws.append({
                "date": dt,
                "nums": nums
            })

    # ==========================================
    # 防呆機制與專業運算區
    # ==========================================
    if not all_draws:
        st.warning("⚠️ 網站嚴重改版或連線受阻，目前暫時無法取得最新開獎數據。")
    else:
        import pandas as pd
        
        # 💡 只嚴格取最近 50 期
        recent_50 = all_draws[:50]
        
        stats = []
        for n in range(1, 40):
            # 計算出現次數
            count = sum(1 for d in recent_50 if n in d['nums'])
            last_date = "50期內未開"
            distance = "超過50期"
            
            # 尋找最後一次出現的日期與距離期數
            for i, d in enumerate(recent_50):
                if n in d['nums']:
                    last_date = d['date']
                    distance = i
                    break
                    
            stats.append({
                "號碼": str(n).zfill(2),
                "出現次數": count,
                "上期出現日期": last_date,
                "距離本期有幾期": distance
            })
            
        stats_df = pd.DataFrame(stats)
        
        # 熱門前 10 名
        hot_df = stats_df.sort_values(by=["出現次數"], ascending=False).head(10)
        
        # 冷門前 5 名 (為了排序，把'超過50期'暫時當作 50)
        stats_df["sort_dist"] = stats_df["距離本期有幾期"].apply(lambda x: 50 if x == "超過50期" else x)
        cold_df = stats_df.sort_values(by=["出現次數", "sort_dist"], ascending=[True, False]).head(10)
        
        # 欄位整理
        display_cols = ["號碼", "出現次數", "上期出現日期", "距離本期有幾期"]
        hot_display = hot_df[display_cols]
        cold_display = cold_df[display_cols]
        
        # AI 包牌精選
        ai_picks = sorted([
            hot_display.iloc[0]["號碼"], hot_display.iloc[1]["號碼"], hot_display.iloc[2]["號碼"],
            cold_display.iloc[0]["號碼"], cold_display.iloc[1]["號碼"]
        ])

        # ==========================================
        # 畫面呈現區 (強制置中與字體放大 HTML 渲染版)
        # ==========================================
        
        # 💡 老弟特製：100% 強制置中的 HTML 表格產生器
       # 💡 老弟特製：100% 強制置中的 HTML 表格產生器 (防爆壓縮版)
        def render_custom_table(df):
            # 把換行符號 (\n) 全部刪除，防止 Streamlit 把這段當作程式碼區塊！
            raw_html = df.to_html(index=False, classes="custom-table").replace('\n', '')
            
            # CSS 樣式寫成緊湊的一坨，避免產生不必要的縮排空格
            custom_css = """<style>
                .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                .custom-table th { background-color: #f0f2f6 !important; color: #31333F !important; font-weight: bold !important; font-size: 18px !important; text-align: center !important; padding: 10px !important; border: 1px solid #ddd !important; }
                .custom-table td { text-align: center !important; font-size: 18px !important; padding: 10px !important; border: 1px solid #ddd !important; background-color: white !important; }
            </style>"""
            
            # 外面再包一層 div，徹底切斷 Markdown 的干擾
            return f"<div>{custom_css}{raw_html}</div>"
            
            # 給這個表格穿上最強的 CSS 裝甲 (!important 強制覆蓋)
            custom_css = """
            <style>
                .custom-table {
                    width: 100%; /* 撐滿寬度 */
                    border-collapse: collapse;
                    font-size: 18px !important; /* 👈 內容字體大小 */
                    margin-bottom: 20px;
                }
                .custom-table th {
                    background-color: #f0f2f6 !important; /* 標題列背景色 */
                    color: #31333F !important;
                    font-weight: bold !important;
                    font-size: 18px !important; /* 👈 標題字體大小 */
                    text-align: center !important; /* 🎯 強制標題置中 */
                    padding: 12px !important;
                    border: 1px solid #ddd !important;
                }
                .custom-table td {
                    text-align: center !important; /* 🎯 強制內容置中 */
                    padding: 10px !important;
                    border: 1px solid #ddd !important;
                }
            </style>
            """
            return custom_css + raw_html

        # 💡 將原本的 2 欄改成 3 欄！(比例為 左4.5 : 中1 : 右4.5)
        c1, c_mid, c2 = st.columns([4.5, 1, 4.5])
        
        with c1:
            st.markdown("### 🔥 50 期 TOP 10 熱門號碼")
            st.markdown(render_custom_table(hot_display), unsafe_allow_html=True)
            
        with c_mid:
            # 💡 老弟特製：霸氣「VS對對碰」垂直分隔線
            st.markdown("""
            <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; min-height: 550px;">
                <div style="border-left: 3px dashed #ccc; height: 150px; margin-bottom: 10px;"></div>
                <div style="background-color: #31333F; color: white; padding: 10px 10px; border-radius: 50px; font-weight: bold; font-size: 18px; box-shadow: 0px 4px 6px rgba(0,0,0,0.2); letter-spacing: 2px;">VS</div>
                <div style="border-left: 3px dashed #ccc; height: 150px; margin-top: 10px;"></div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown("### ❄️ 50 期 TOP 10 冷門號碼")
            st.markdown(render_custom_table(cold_display), unsafe_allow_html=True)

        st.markdown("---")
        # 下面接續你的 AI 推薦組合代碼...


        st.markdown("### 🎯 老弟的 AI 綜合推薦組合")
        st.markdown("> **選號邏輯**：擷取近期最強勢的 3 個熱門號，搭配 2 個潛水極深的冷門號博反彈。")
        st.success(f"### 🎱 本期推薦包牌： **{', '.join(ai_picks)}**")
        
        if st.button("將此組合帶入計算機試算", type="primary"):
            st.session_state.calc_text = " ".join(ai_picks) + " "
            go_to("計算機")
            
        st.caption("⚠️ 免責聲明：本預測僅依據歷史數據進行機率統計，539 為獨立隨機事件，不保證中獎，請視為娛樂參考，量力而為！")

# ==========================================
# ⚙️ 帳戶設定區 
# ==========================================
elif st.session_state.page == "帳戶設定":
    col_back, _ = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ 返回首頁"): go_to("首頁")
    st.title("⚙️ 帳戶個人設定")
    
    curr_nick = st.session_state.get('nickname', st.session_state.logged_in_user)
    
    with st.form("settings_form"):
        new_nick = st.text_input("修改暱稱", value=curr_nick)
        new_pass = st.text_input("修改新密碼 (不改請留空)", type="password")
        if st.form_submit_button("💾 儲存修改設定", use_container_width=True):
            user_ref = db.collection('users').document(st.session_state.logged_in_user)
            update_data = {"nickname": new_nick}
            if new_pass.strip():
                update_data["password"] = new_pass
            try:
                user_ref.update(update_data)
                st.session_state.nickname = new_nick 
                st.success("✅ 雲端設定已同步更新！"); time.sleep(1); st.rerun()
            except Exception as e:
                st.error(f"❌ 雲端更新失敗：{e}")

# ===# ==========================================
# 📊 個人損益表區 (升級：自訂日期區間查詢)
# ==========================================
elif st.session_state.page == "損益表":
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ 返回首頁"): go_to("首頁")
    with col_title:
        st.title("📊 個人歷史損益表")
        
    today = datetime.now().date()
    
    # 💡 調整版面比例，讓日期選擇器有足夠空間
    col_filter, col_space, col_del = st.columns([2, 1.5, 1.5])
    
    with col_filter:
        # 💡 加入「自訂區間」選項
        time_filter = st.selectbox("📅 選擇查詢範圍", ["全部紀錄", "近一周", "近一個月", "自訂區間"], index=0)
        
        custom_date_range = None
        # 如果選擇自訂區間，跳出日期選擇器
        if time_filter == "自訂區間":
            custom_date_range = st.date_input(
                "📌 請選擇起訖日期 (點擊選取兩次)", 
                value=(today - timedelta(days=7), today), # 預設選最近7天
                max_value=today
            )
    
    with col_del:
        # 配合左邊元件高度，把按鈕往下推一點
        if time_filter == "自訂區間":
            st.write("")
            st.write("")
        st.write("")
        st.write("")
        
        with st.popover("🗑️ 清空所有紀錄", use_container_width=True):
            st.warning("⚠️ 確定要清除所有對獎紀錄嗎？")
            st.error("此操作無法復原！")
            if st.button("🚨 確認刪除", type="primary", use_container_width=True):
                try:
                    # ☁️ 雲端刪除需要一筆一筆刪 (或是批次刪除)
                    batch = db.batch()
                    docs_to_del = db.collection('records').where("username", "==", st.session_state.logged_in_user).stream()
                    for doc in docs_to_del:
                        batch.delete(doc.reference)
                    batch.commit()
                    st.toast("✅ 雲端歷史紀錄已全數清除！", icon="🗑️")
                    time.sleep(1.5); st.rerun() 
                except Exception as e:
                    st.error(f"❌ 雲端刪除失敗：{e}")
        
   # ☁️ 從 Firebase 抓取資料
    docs = db.collection('records').where("username", "==", st.session_state.logged_in_user).order_by("date", direction=firestore.Query.DESCENDING).stream()
    
    data_list = []
    for doc in docs:
        d = doc.to_dict()
        data_list.append({
            "開獎日期": d.get("date"),
            "總成本": d.get("cost"),
            "總獎金": d.get("prize"),
            "淨損益": d.get("profit"),
            "details": d.get("details")
        })
    df = pd.DataFrame(data_list)

    
    display_title = time_filter # 用來顯示在統計總結上的文字
    
    if not df.empty:
        df['開獎日期'] = pd.to_datetime(df['開獎日期'], format='mixed').dt.date
        
        if time_filter == "近一周":
            target_date = today - timedelta(days=7)
            df = df[df['開獎日期'] >= target_date]
        elif time_filter == "近一個月":
            target_date = today - timedelta(days=30)
            df = df[df['開獎日期'] >= target_date]
        elif time_filter == "自訂區間":
            # 💡 處理自訂區間的過濾邏輯
            if custom_date_range and len(custom_date_range) == 2:
                start_date, end_date = custom_date_range
                df = df[(df['開獎日期'] >= start_date) & (df['開獎日期'] <= end_date)]
                display_title = f"{start_date} 至 {end_date}"
            elif custom_date_range and len(custom_date_range) == 1:
                # 萬一使用者只點了一天
                start_date = custom_date_range[0]
                df = df[df['開獎日期'] == start_date]
                display_title = f"{start_date} 單日"
            else:
                display_title = "自訂區間 (請選擇完整日期)"
                
    if df.empty:
        st.info(f"🔍 目前沒有【{display_title}】的對獎紀錄喔！")
    else:
        total_cost = df['總成本'].sum()
        total_prize = df['總獎金'].sum()
        total_profit = df['淨損益'].sum()
        
        st.write(f"### 📈 【{display_title}】統計總結")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"區間總成本", f"{total_cost:,.0f} 元")
        c2.metric(f"區間總獎金", f"{total_prize:,.0f} 元")
        c3.metric(f"區間淨損益", f"{total_profit:,.0f} 元", delta=float(total_profit))
        
        st.divider()
        st.subheader("📝 詳細對獎明細 (點擊展開看下了什麼)")
        
        for idx, row in df.iterrows():
            date_str = str(row['開獎日期'])
            profit = row['淨損益']
            emoji = "🟢" if profit > 0 else "🔴" if profit < 0 else "⚪"
            
            expander_title = f"{emoji} {date_str} | 成本: {row['總成本']:,.0f} | 獎金: {row['總獎金']:,.0f} | 淨損益: {profit:,.0f} 元"
            
            with st.expander(expander_title):
                details_str = row['details']
                if pd.notna(details_str) and details_str:
                    try:
                        import json
                        bets = json.loads(details_str)
                        for b_idx, b in enumerate(bets):
                            st.markdown(f"**組合 {b_idx+1}: 【{b['type']}】**")
                            nums_str = ", ".join([f"{n:02d}" for n in b['nums']])
                            st.write(f"🎫 下注號碼: {nums_str}")
                            
                            if b['matched']:
                                matched_str = ", ".join([f"{n:02d}" for n in b['matched']])
                                st.success(f"🎯 命中號碼: {matched_str} (獲得獎金: {b['prize']:,.0f} 元)")
                            else:
                                st.write(f"❌ 未命中 (花費成本: {b['cost']} 元)")
                            
                            if b_idx < len(bets) - 1:
                                st.markdown("---")
                    except:
                        st.write("⚠️ 舊版紀錄，無法顯示詳細資料。")
                else:
                    st.write("⚠️ 舊版紀錄，未儲存下注細節。")

# ==========================================
# 🏆 兌獎區 (雙重保險，優先從快取對獎)
# ==========================================
elif st.session_state.page == "兌獎":
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("⬅️ 返回首頁"): go_to("首頁")
    with col_title:
        st.title("📅 今彩 539 專業兌獎系統")

    st.sidebar.header("⚙️ 全局參數設定")
    with st.sidebar.expander("🚗 坐車成本 (10元基準)", expanded=False):
        base_rate = 10 
        base_cost_val = st.number_input(f"坐車 {base_rate} 元 = ? (成本)", value=304, step=1, key="sb_base_cost")
        per_unit_cost = base_cost_val / base_rate

    with st.sidebar.expander("💥 連碰/立柱成本 (折扣)", expanded=False):
        combo_discount = st.number_input("連碰/立柱折扣 (預設 0.78)", value=0.78, step=0.01, format="%.2f", key="sb_combo_discount")

    st.sidebar.subheader("💰 獎金 (賠率) 設定")
    with st.sidebar.expander("🚗 坐車獎金", expanded=False):
        prize_car_base = st.number_input(f"坐車 {base_rate} 元 = ? (獎金)", value=2120, step=10, key="sb_p_car")

    with st.sidebar.expander("💥 連碰/立柱獎金 (每 10 元)", expanded=False):
        p_2star_val = st.number_input("二星獎金 (10元/碰)", value=530, step=10, key="sb_p2")
        p_3star_val = st.number_input("三星獎金 (10元/碰)", value=5700, step=100, key="sb_p3")
        p_4star_val = st.number_input("四星獎金 (10元/碰)", value=800000, step=1000, key="sb_p4")

    st.subheader("📢 設定開獎號碼")
    data_source = st.radio("請選擇開獎號碼來源：", ["網路自動抓取", "手動輸入"], horizontal=True)
    draw_numbers = []
    
    pick_date = st.date_input("請選擇開獎日期", value=datetime.now())

    if data_source == "網路自動抓取":
        def get_539_data_by_date(target_date):
            import re
            t_str = target_date.strftime("%Y/%m/%d")
            
            # 1. 先從記憶體裡的 100 筆找，瞬間完成！
            recent_draws = get_recent_100_draws()
            for dt, nums in recent_draws:
                if dt == t_str:
                    return sorted(nums)
            
            # 2. 如果選了很久以前的日期，用 X光法 去翻舊網頁
            for i in range(3, 10): 
                url = f"https://www.pilio.idv.tw/lto539/list539BIG.asp?indexpage={i}&orderby=new"
                try:
                    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                    html_text = r.content.decode('big5', errors='ignore')
                    soup = BeautifulSoup(html_text, "html.parser")
                    
                    for row in soup.find_all("tr"):
                        row_text = row.get_text(separator=' ', strip=True)
                        # 如果這行文字裡面有我們要的日期
                        if t_str in row_text: 
                            for cell in row.find_all(['td', 'span', 'div', 'font']):
                                c_text = cell.get_text(strip=True).replace(',', ' ').replace('\xa0', ' ')
                                tokens = [t for t in c_text.split() if t.isdigit() and len(t) == 2]
                                if len(tokens) >= 5:
                                    return sorted([int(t) for t in tokens[:5]])
                                if len(c_text) == 10 and c_text.isdigit():
                                    return sorted([int(c_text[k:k+2]) for k in range(0, 10, 2)])
                except: pass
            return None

        fetched_numbers = get_539_data_by_date(pick_date)

        if fetched_numbers:
            draw_numbers = fetched_numbers
            st.success(f"✅ {pick_date} 開獎：{', '.join([f'{n:02d}' for n in draw_numbers])}")
        else:
            st.warning("🔍 找不到該日期資料，請確認網站是否已更新，或切換至「手動輸入」。")
    else:
        manual_nums = st.multiselect(
            "請手動選擇 5 個開獎號碼：", 
            options=range(1, 40), 
            format_func=lambda x: f"{x:02d}",
            key="manual_draw_nums"
        )
        if len(manual_nums) > 5:
            st.error("⚠️ 不小心選太多囉！請取消勾選多餘的號碼，維持 5 個選項。")
            draw_numbers = [] 
        elif len(manual_nums) == 5:
            draw_numbers = sorted(manual_nums)
            st.success(f"✅ 已設定手動開獎號碼：{', '.join([f'{n:02d}' for n in draw_numbers])}")
        elif len(manual_nums) > 0:
            st.info(f"👉 請選滿 5 個號碼 (目前已選 {len(manual_nums)} 個)")

    st.divider()

    st.subheader("🕹️ 選擇投注玩法")
    tab1, tab2, tab3 = st.tabs(["💥 綜合碰數 (連碰/立柱)", "🚗 坐車 (單選)", "🐾 坐尾數 (多選)"])
    rid = st.session_state.reset_id

    with tab1:
        mode = st.radio("選擇模式", ["號碼連碰", "號碼立柱", "尾數連碰", "尾數立柱"], horizontal=True, key=f"mode_{rid}")
        st.write("選擇下注星等 (可複選)：")
        sc1, sc2, sc3 = st.columns(3)
        buy_p2 = sc1.checkbox("買二星", value=True, key=f"buy2_{rid}")
        buy_p3 = sc2.checkbox("買三星", key=f"buy3_{rid}")
        buy_p4 = sc3.checkbox("買四星", key=f"buy4_{rid}")
        combo_amt = st.number_input("下注金額 (每碰倍率，預設10元)", value=10, step=5, min_value=1, key=f"ni_combo_amt_{rid}")

        if "立柱" in mode:
            num_cols = st.number_input("請選擇要有幾柱？", 2, 10, 2, key=f"col_num_{rid}")
            cols_data = []
            for i in range(num_cols):
                if "號碼" in mode:
                    c_nums = st.multiselect(f"第 {i+1} 柱號碼", options=range(1, 40), format_func=lambda x: f"{x:02d}", key=f"lz_n_{i}_{rid}")
                else:
                    c_tails = st.multiselect(f"第 {i+1} 柱尾數 (0-9)", options=range(10), key=f"lz_t_{i}_{rid}")
                    c_nums = []
                    for t in c_tails: c_nums.extend(get_tail_numbers(t))
                cols_data.append(list(set(c_nums)))
            
            if st.button("➕ 加入立柱下注"):
                counts = [len(c) for c in cols_data]
                flat_nums_with_dupes = [num for col in cols_data for num in col]
                unique_nums = set(flat_nums_with_dupes)
                if any(n == 0 for n in counts): st.warning("每一柱都必須至少有 1 個號碼！")
                elif len(flat_nums_with_dupes) != len(unique_nums): st.error("⚠️ 不同柱之間不能包含「重複」的號碼！")
                elif not (buy_p2 or buy_p3 or buy_p4): st.warning("請至少勾選一種星等！")
                else:
                    p2 = calculate_lizhu_touches(counts, 2) if buy_p2 else 0
                    p3 = calculate_lizhu_touches(counts, 3) if buy_p3 else 0
                    p4 = calculate_lizhu_touches(counts, 4) if buy_p4 else 0
                    total_t = p2 + p3 + p4
                    # 💡 重點更新：從 round() 改成 math.ceil()，強迫無條件進位
                    cost = math.ceil(total_t * combo_amt * combo_discount)
                    st.session_state.my_bets.append({"type": mode, "cols": cols_data, "nums": sorted(list(unique_nums)), "bet_amount": combo_amt, "actual_cost": cost, "stars_bought": (buy_p2, buy_p3, buy_p4), "touches": (p2, p3, p4)})
                    st.toast(f"已加入{mode}，共 {total_t} 碰")

        elif "連碰" in mode:
            if "號碼" in mode: bet_nums = st.multiselect("選擇連碰號碼：", options=range(1, 40), format_func=lambda x: f"{x:02d}", key=f"ms_combo_{rid}")
            else:
                bet_tails = st.multiselect("選擇連碰尾數 (0-9)：", options=range(10), key=f"ms_tails_{rid}")
                bet_nums = []
                for t in bet_tails: bet_nums.extend(get_tail_numbers(t))
                bet_nums = list(set(bet_nums))
            if st.button("➕ 加入連碰下注"):
                n = len(bet_nums)
                if n < 2: st.warning("至少需 2 個號碼以上")
                elif not (buy_p2 or buy_p3 or buy_p4): st.warning("請至少勾選一種星等！")
                else:
                    p2 = calculate_combinations(n, 2) if buy_p2 else 0
                    p3 = calculate_combinations(n, 3) if buy_p3 else 0
                    p4 = calculate_combinations(n, 4) if buy_p4 else 0
                    total_t = p2 + p3 + p4
                    # 💡 重點更新：改用 math.ceil() 無條件進位
                    cost = math.ceil(total_t * combo_amt * combo_discount)
                    st.session_state.my_bets.append({"type": mode, "nums": sorted(bet_nums), "bet_amount": combo_amt, "actual_cost": cost, "stars_bought": (buy_p2, buy_p3, buy_p4), "touches": (p2, p3, p4)})
                    st.toast(f"已加入{mode}，共 {total_t} 碰")

    with tab2:
        bet_car = st.multiselect("選擇坐車號碼：", options=range(1, 40), format_func=lambda x: f"{x:02d}", key=f"ms_car_{rid}")
        car_amt = st.number_input("下注金額 (倍率)", value=10, step=5, key=f"ni_car_amt_{rid}")
        # 💡 同步更新坐車成本，確保全系統一致無條件進位
        c_cost = math.ceil(len(bet_car) * (car_amt * per_unit_cost))
        if st.button("➕ 加入坐車", key="btn_car"):
            if not bet_car: st.warning("請選號碼")
            else:
                st.session_state.my_bets.append({"type": "坐車", "nums": sorted(bet_car), "bet_amount": car_amt, "actual_cost": c_cost})
                st.toast("已加入坐車")

    with tab3:
        bet_tails = st.multiselect("選擇坐尾數 (0-9，可多選)：", options=list(range(10)), key=f"ms_tail_{rid}")
        tail_amt = st.number_input("尾數下注金額 (倍率)", value=10, step=5, key=f"ni_tail_amt_{rid}")
        tail_nos = []
        for t in bet_tails: tail_nos.extend(get_tail_numbers(t))
        tail_nos = sorted(list(set(tail_nos)))
        # 💡 同步更新坐尾數成本
        t_cost = math.ceil(len(tail_nos) * (tail_amt * per_unit_cost))
        if st.button("➕ 加入坐尾數", key="btn_tail"):
            if not bet_tails: st.warning("請至少選擇一個尾數")
            else:
                tail_str = ",".join([str(t) for t in sorted(bet_tails)])
                st.session_state.my_bets.append({"type": f"坐尾數({tail_str})", "nums": tail_nos, "bet_amount": tail_amt, "actual_cost": t_cost})
                st.toast(f"已加入坐尾數({tail_str})")

    if st.session_state.my_bets:
        st.write("---")
        st.subheader("📝 我的下注清單")
        col_title, col_clear = st.columns([4, 1.2])
        with col_clear:
            if st.button("🗑️ 全部清空"):
                st.session_state.my_bets = []
                st.session_state.show_result = False
                st.session_state.reset_id += 1  
                st.rerun()

        for idx, bet in enumerate(st.session_state.my_bets):
            st.markdown("<div style='margin: 10px 0;'>", unsafe_allow_html=True)
            c1, c2 = st.columns([4, 1.2])
            play_type = bet['type']
            title = f"**【{play_type}-{bet['bet_amount']}元】**"

            if "連碰" in play_type or "立柱" in play_type:
                t2, t3, t4 = bet['touches']
                touch_details = []
                if t2 > 0: touch_details.append(f"2星{t2}碰")
                if t3 > 0: touch_details.append(f"3星{t3}碰")
                if t4 > 0: touch_details.append(f"4星{t4}碰")
                detail_info = f"(成本:{bet['actual_cost']}元 / {'、'.join(touch_details)})"
                if "立柱" in play_type: nums_str = " | ".join([",".join([f"{n:02d}" for n in sorted(col)]) for col in bet['cols']])
                else: nums_str = ", ".join([f"{n:02d}" for n in bet['nums']])
            else:
                detail_info = f"(成本:{bet['actual_cost']}元)"
                nums_str = ", ".join([f"{n:02d}" for n in bet['nums']])
            
            c1.markdown(f"#### {idx+1}. {title}: :red[**{nums_str}**]  \n&nbsp;&nbsp;&nbsp;&nbsp;{detail_info}")
            if c2.button("刪除", key=f"del_{idx}"):
                st.session_state.my_bets.pop(idx)
                st.session_state.show_result = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🚀 開始全量對獎", type="primary", use_container_width=True):
        if not draw_numbers: st.error("無開獎號碼")
        elif not st.session_state.my_bets: st.warning("清單為空")
        else:
            st.session_state.show_result = True
            
    if st.session_state.show_result:
        st.header("🏆 對獎結果明細")
        g_cost, g_prize = 0, 0
        bet_details_list = [] # 👈 新增：用來收集每一組的下注與中獎細節
        
        for idx, bet in enumerate(st.session_state.my_bets):
            matched = sorted(list(set(bet['nums']) & set(draw_numbers)))
            count = len(matched)
            current_prize = 0
            g_cost += bet['actual_cost']
            with st.expander(f"組合 {idx+1}: 【{bet['type']}】 (共中 {count} 碼)", expanded=True):
                if count > 0:
                    st.success(f"🎯 對中號碼：{', '.join([f'{n:02d}' for n in matched])}")
                    mul = bet.get('bet_amount', 10) / 10
                    if "車" in bet['type'] or "坐" in bet['type']:
                        current_prize = mul * prize_car_base * count
                        st.info(f"🚗 中獎！")
                    elif "立柱" in bet['type']:
                        matched_counts_per_col = [len(set(col) & set(draw_numbers)) for col in bet['cols']]
                        h2, h3, h4 = bet['stars_bought']
                        p2_w = calculate_lizhu_touches(matched_counts_per_col, 2) if h2 else 0
                        p3_w = calculate_lizhu_touches(matched_counts_per_col, 3) if h3 else 0
                        p4_w = calculate_lizhu_touches(matched_counts_per_col, 4) if h4 else 0
                        p2_p, p3_p, p4_p = (p2_w * p_2star_val) * mul, (p3_w * p_3star_val) * mul, (p4_w * p_4star_val) * mul
                        current_prize = p2_p + p3_p + p4_p
                        if p2_w > 0: st.write(f"🥈 二星中獎：{p2_w} 碰 (獎金 {p2_p:,.0f} 元)")
                        if p3_w > 0: st.write(f"🥇 三星中獎：{p3_w} 碰 (獎金 {p3_p:,.0f} 元)")
                        if p4_w > 0: st.write(f"💎 四星中獎：{p4_w} 碰 (獎金 {p4_p:,.0f} 元)")
                    elif "連碰" in bet['type']:
                        h2, h3, h4 = bet['stars_bought']
                        p2_w = calculate_combinations(count, 2) if h2 else 0
                        p3_w = calculate_combinations(count, 3) if h3 else 0
                        p4_w = calculate_combinations(count, 4) if h4 else 0
                        p2_p, p3_p, p4_p = (p2_w * p_2star_val) * mul, (p3_w * p_3star_val) * mul, (p4_w * p_4star_val) * mul
                        current_prize = p2_p + p3_p + p4_p
                        if p2_w > 0: st.write(f"🥈 二星中獎：{p2_w} 碰 (獎金 {p2_p:,.0f} 元)")
                        if p3_w > 0: st.write(f"🥇 三星中獎：{p3_w} 碰 (獎金 {p3_p:,.0f} 元)")
                        if p4_w > 0: st.write(f"💎 四星中獎：{p4_w} 碰 (獎金 {p4_p:,.0f} 元)")
                    g_prize += current_prize
                    st.markdown(f"#### 💰 獲得獎金：{current_prize:,.0f} 元")
                else: 
                    st.write("❌ 本組未中獎 (金額: 0 元)")
            
            # 💡 收集這組的細節準備存檔
            bet_details_list.append({
                "type": bet['type'],
                "nums": bet['nums'],
                "cost": bet['actual_cost'],
                "prize": current_prize,
                "matched": matched
            })

        st.divider()
        st.header("🏁 今日總結")
        f_profit = g_prize - g_cost
        ca, cb, cc = st.columns(3)
        ca.metric("總成本", f"{g_cost:,.1f} 元")
        ca.write("(含折扣後成本)")
        cb.metric("總獎金", f"{g_prize:,.1f} 元")
        cc.metric("總最終損益", f"{f_profit:,.1f} 元", delta=float(f_profit))
        if f_profit > 0: st.balloons()
        
        st.write("---")
        st.write("---")
        # 💡 檢查看看，是不是有兩組一模一樣的 if st.button...
        # 如果有，請刪掉多出來的那一組！
        
        if st.button("💾 將本次紀錄儲存至損益表", type="primary"):
            draw_date_str = pick_date.strftime("%Y-%m-%d")
            details_json = json.dumps(bet_details_list, ensure_ascii=False)
            
            try:
                # ☁️ 這是雲端版，請確認裡面是 db.collection... 而不是 sqlite3
                db.collection('records').add({
                    "username": st.session_state.logged_in_user,
                    "date": draw_date_str,
                    "cost": g_cost,
                    "prize": g_prize,
                    "profit": f_profit,
                    "details": details_json,
                    "timestamp": firestore.SERVER_TIMESTAMP 
                })
                
                st.success("✅ 本次紀錄已成功同步至 Google 雲端資料庫！")
                time.sleep(1.5)
                st.rerun() 
            except Exception as e:

                st.error(f"❌ 雲端存檔失敗：{e}")

































