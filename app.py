import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# 頁面基本設定
st.set_page_config(page_title="加油紀錄系統", layout="centered")

st.title("⛽ 車隊加油紀錄系統")

# ---------------------------------------------------------
# 請在此處貼上你部署的 Google Apps Script Web App 網址
GSHEET_WEB_APP_URL = "填入你的_APPS_SCRIPT_WEB_APP_網址"
# ---------------------------------------------------------

# 選單設定（可自由新增或修改）
DRIVERS = ["張小明", "陳大華", "李阿姨", "王司機"]
PLATES = ["ABC-1234", "DEF-5678", "GHI-9012", "JKL-3456"]

# --- 新增加油紀錄區塊 ---
st.subheader("➕ 新增加油紀錄")

with st.form("fuel_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        driver = st.selectbox("👤 選擇駕駛人", DRIVERS)
        price_per_liter = st.number_input("💵 油價單價 (元/L)", min_value=0.0, value=30.0, step=0.1)
    
    with col2:
        plate = st.selectbox("🚗 選擇車牌", PLATES)
        liters = st.number_input("⛽ 加油公升數 (L)", min_value=0.0, value=20.0, step=0.5)

    submit_button = st.form_submit_button("送出並寫入 Google 試算表")

if submit_button:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_price = round(price_per_liter * liters)

    # 準備寫入 Google 試算表的資料格式
    payload = {
        "time": now_str,
        "driver": driver,
        "plate": plate,
        "price": price_per_liter,
        "liters": liters,
        "total": total_price,
        "status": "未確認" # 預設勾選狀態
    }

    try:
        # 透過 POST 請求發送到 Google Apps Script
        response = requests.post(GSHEET_WEB_APP_URL, json=payload)
        if response.status_code == 200:
            st.success(f"✅ 成功寫入 Google 試算表！本次總金額：**{total_price}** 元")
            st.cache_data.clear()  # 清除快取以刷新資料
        else:
            st.error("寫入失敗，請檢查 Apps Script 設定。")
    except Exception as e:
        st.error(f"連線失敗：{e}")

# --- 讀取與管理 Google 試算表資料 ---
st.markdown("---")
st.subheader("📊 雲端加油紀錄管理")

@st.cache_data(ttl=5)  # 快取 5 秒，定期更新
def fetch_gsheet_data():
    try:
        res = requests.get(GSHEET_WEB_APP_URL)
        data = res.json()
        if len(data) > 1:
            # 第一列為表頭，其餘為資料
            df = pd.DataFrame(data[1:], columns=data[0])
            return df
        else:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

df = fetch_gsheet_data()

if not df.empty:
    # 新增「完成勾選」與「刪除」的動態操作列
    if "已確認" not in df.columns:
        df["已確認"] = False  # 建立可勾選的複選框欄位
    
    # 呈現可互動編輯的 Data Editor
    edited_df = st.data_editor(
        df,
        column_config={
            "已確認": st.column_config.CheckboxColumn(
                "確認核銷",
                help="勾選代表已核銷或審核完畢",
                default=False,
            )
        },
        disabled=["時間", "駕駛人", "車牌", "單價", "公升數", "總價"], # 避免誤改原始欄位
        num_rows="dynamic", # 允許在表格中手動刪除資料列 (點選行首即可按 Delete 鍵或刪除)
        use_container_width=True,
        key="gsheet_editor"
    )
    
    st.info("💡 提示：點擊表格最左側列號並按鍵盤 `Delete` 可刪除該筆顯示資料，勾選核銷可紀錄狀態。")
else:
    st.info("目前 Google 試算表中尚無資料，或正在連線中...")
