import streamlit as st
import pandas as pd
from datetime import datetime

# 設定頁面標題
st.set_page_config(page_title="油價紀錄 App", layout="centered")

st.title("⛽ 油價紀錄小幫手")
st.caption("簡單紀錄每次加油的時間、單價、公升數與總價")

# 使用 session_state 來儲存加油紀錄（避免頁面重新整理後資料消失）
if "fuel_logs" not in st.session_state:
    st.session_state.fuel_logs = pd.DataFrame(
        columns=["加油時間日期", "油價單價 (元/L)", "公升數 (L)", "總價 (元)"]
    )

# --- 輸入表單 ---
st.subheader("➕ 新增加油紀錄")

with st.form(key="fuel_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        # 輸入每公升油價
        price_per_liter = st.number_input("油價單價 (元/公升)", min_value=0.0, value=30.0, step=0.1)
    
    with col2:
        # 輸入加油公升數
        liters = st.number_input("加油公升數 (L)", min_value=0.0, value=20.0, step=0.5)
    
    # 送出按鈕
    submit_button = st.form_submit_button(label="新增紀錄")

# --- 資料處理邏輯 ---
if submit_button:
    # 1. 自動抓取當前日期與時間 (格式：YYYY-MM-DD HH:MM)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 2. 自動計算總價 (四捨五入至整數)
    total_price = round(price_per_liter * liters)
    
    # 3. 組成新的一筆資料
    new_data = {
        "加油時間日期": now_str,
        "油價單價 (元/L)": price_per_liter,
        "公升數 (L)": liters,
        "總價 (元)": total_price
    }
    
    # 4. 新增至 Session State 中的 DataFrame
    st.session_state.fuel_logs = pd.concat(
        [pd.DataFrame([new_data]), st.session_state.fuel_logs], 
        ignore_index=True
    )
    
    st.success(f"✅ 成功記錄！本次總金額為：**{total_price}** 元")

---

# --- 顯示歷史紀錄 ---
st.subheader("📜 歷史加油紀錄")

if not st.session_state.fuel_logs.empty:
    # 顯示表格
    st.dataframe(st.session_state.fuel_logs, use_container_width=True)
    
    # 統計數據 (選填)
    total_spent = st.session_state.fuel_logs["總價 (元)"].sum()
    total_liters = st.session_state.fuel_logs["公升數 (L)"].sum()
    
    st.metric(label="累積加油總金額", value=f"{total_spent:,} 元")
    st.metric(label="累積總公升數", value=f"{total_liters:.1f} L")
else:
    st.info("目前還沒有任何加油紀錄，請在上方輸入資料並新增。")
