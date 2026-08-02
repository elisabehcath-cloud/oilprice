import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from PIL import Image
import easyocr
import numpy as np
import re

# 頁面標題設定
st.set_page_config(page_title="加油紀錄與發票辨識系統", layout="centered")

# --- SQLite 資料庫設定 ---
DB_FILE = "fuel_log.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fuel_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            driver TEXT,
            plate TEXT,
            inv_num TEXT,
            ubn TEXT,
            price REAL,
            liters REAL,
            total INTEGER,
            status INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- 初始化 EasyOCR 辨識器 (快取載入以提升速度) ---

@st.cache_resource
def load_ocr():
    return easyocr.Reader(['ch_tra', 'en'])

reader = load_ocr()

# 下拉選單預設值
DRIVERS = ["張小明", "陳大華", "李阿姨", "王司機"]
PLATES = ["ABC-1234", "DEF-5678", "GHI-9012", "JKL-3456"]

st.title("⛽ 車隊加油與發票辨識系統")

# --- 1. 拍照與 OCR 辨識區塊 ---
st.subheader("📷 拍照辨識統一發票")
img_file = st.camera_input("請對準發票進行拍照")

# 初始化 Session State 暫存辨識出的資料
if "ocr_data" not in st.session_state:
    st.session_state.ocr_data = {
        "inv_num": "",
        "ubn": "",
        "price": 30.0,
        "liters": 20.0,
        "total": 0
    }

if img_file is not None:
    # 讀取相片
    image = Image.open(img_file)
    img_array = np.array(image)
    
    with st.spinner("🔍 正在解析發票資料中..."):
        # 進行文字辨識
        results = reader.readtext(img_array)
        extracted_text = " ".join([res[1] for res in results])
        
        # 顯示辨識出來的原始文字（可供除錯參考）
        with st.expander("檢視 OCR 提取到的原始文字"):
            st.write(extracted_text)
            
        # 1. 辨識發票號碼 (例: AB-12345678)
        inv_match = re.search(r'[A-Za-z]{2}[-_\s]?\d{8}', extracted_text)
        if inv_match:
            st.session_state.ocr_data["inv_num"] = inv_match.group(0).replace(" ", "").upper()
            
        # 2. 辨識統一編號 (8位數字)
        ubn_match = re.search(r'統編[：:\s]*(\d{8})', extracted_text)
        if ubn_match:
            st.session_state.ocr_data["ubn"] = ubn_match.group(1)

        # 3. 辨識總價 (包含關鍵字如 總計、金額、元)
        total_match = re.search(r'(?:總計|合計|金額)[：:\s]*\$?(\d+)', extracted_text)
        if total_match:
            st.session_state.ocr_data["total"] = int(total_match.group(1))

        # 4. 辨識單價與公升數
        price_match = re.search(r'單價[：:\s]*(\d+\.?\d*)', extracted_text)
        if price_match:
            st.session_state.ocr_data["price"] = float(price_match.group(1))

        liters_match = re.search(r'(?:數量|公升)[：:\s]*(\d+\.?\d*)', extracted_text)
        if liters_match:
            st.session_state.ocr_data["liters"] = float(liters_match.group(1))

    st.success("✅ 發票辨識完成！請在下方確認或微調資料後送出。")


# --- 2. 手動輸入/確認表單 ---
st.markdown("---")
st.subheader("📝 確認加油與發票內容")

with st.form("fuel_form", clear_on_submit=False):
    col1, col2 = st.columns(2)
    with col1:
        driver = st.selectbox("👤 駕駛人", DRIVERS)
        inv_num = st.text_input("📄 發票號碼", value=st.session_state.ocr_data["inv_num"])
        price_per_liter = st.number_input("💵 油價單價 (元/L)", min_value=0.0, value=st.session_state.ocr_data["price"], step=0.1)
    
    with col2:
        plate = st.selectbox("🚗 車牌號碼", PLATES)
        ubn = st.text_input("🏢 買方統一編號 (統編)", value=st.session_state.ocr_data["ubn"])
        liters = st.number_input("⛽ 加油公升數 (L)", min_value=0.0, value=st.session_state.ocr_data["liters"], step=0.5)

    # 試算總價 (若 OCR 未辨識出總價則自動計算)
    calc_total = round(price_per_liter * liters)
    default_total = st.session_state.ocr_data["total"] if st.session_state.ocr_data["total"] > 0 else calc_total
    total_price = st.number_input("💰 總價 (元)", min_value=0, value=default_total)

    submit_button = st.form_submit_button("💾 儲存資料存入 SQLite")

if submit_button:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO fuel_records (time, driver, plate, inv_num, ubn, price, liters, total, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (now_str, driver, plate, inv_num, ubn, price_per_liter, liters, total_price, 0))
    conn.commit()
    conn.close()

    st.success(f"🎉 成功寫入資料庫！本次加油總金額：**{total_price}** 元")
    
    # 清除暫存檔並重置
    st.session_state.ocr_data = {"inv_num": "", "ubn": "", "price": 30.0, "liters": 20.0, "total": 0}
    st.rerun()


# --- 3. 歷史紀錄管理 ---
st.markdown("---")
st.subheader("📜 歷史加油與發票紀錄")

conn = get_connection()
df_logs = pd.read_sql_query("SELECT * FROM fuel_records ORDER BY id DESC", conn)
conn.close()

if not df_logs.empty:
    df_logs["status"] = df_logs["status"].astype(bool)
    
    column_mapping = {
        "id": "ID",
        "time": "時間",
        "driver": "駕駛人",
        "plate": "車牌",
        "inv_num": "發票號碼",
        "ubn": "買方統編",
        "price": "單價",
        "liters": "公升數",
        "total": "總價",
        "status": "已核銷"
    }
    
    display_df = df_logs.rename(columns=column_mapping)

    edited_df = st.data_editor(
        display_df,
        column_config={
            "已核銷": st.column_config.CheckboxColumn("已核銷", default=False)
        },
        disabled=["ID", "時間", "駕駛人", "車牌", "發票號碼", "買方統編", "單價", "公升數", "總價"],
        num_rows="dynamic",
        use_container_width=True,
        key="sqlite_editor"
    )

    if st.button("💾 儲存核銷變更與刪除項目"):
        conn = get_connection()
        cursor = conn.cursor()
        
        current_ids = set(edited_df["ID"].tolist())
        original_ids = set(df_logs["id"].tolist())
        deleted_ids = original_ids - current_ids

        for del_id in deleted_ids:
            cursor.execute("DELETE FROM fuel_records WHERE id = ?", (del_id,))

        for index, row in edited_df.iterrows():
            record_id = int(row["ID"])
            status_val = 1 if row["已核銷"] else 0
            cursor.execute("UPDATE fuel_records SET status = ? WHERE id = ?", (status_val, record_id))

        conn.commit()
        conn.close()
        st.success("✅ 資料庫變更已更新！")
        st.rerun()
else:
    st.info("目前尚無資料。")
