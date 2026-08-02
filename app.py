import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# 頁面基本設定
st.set_page_config(page_title="加油紀錄系統 (SQLite)", layout="centered")

# --- 資料庫初始化與處理函式 ---
DB_FILE = "fuel_log.db"

def get_connection():
    """建立 SQLite 資料庫連線"""
    conn = sqlite3.connect(DB_FILE)
    return conn

def init_db():
    """初始化資料庫表單"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fuel_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time TEXT,
            driver TEXT,
            plate TEXT,
            price REAL,
            liters REAL,
            total INTEGER,
            status INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def load_data():
    """讀取 SQLite 中的所有資料"""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM fuel_records ORDER BY id DESC", conn)
    conn.close()
    if not df.empty:
        # 將 status (0/1) 轉為布林值 (False/True) 方便 Streamlit 核取方塊顯示
        df["status"] = df["status"].astype(bool)
    return df

# 啟動時自動初始化資料庫
init_db()

# --- 介面元件選單 ---
DRIVERS = ["張小明", "陳大華", "李阿姨", "王司機"]
PLATES = ["ABC-1234", "DEF-5678", "GHI-9012", "JKL-3456"]

st.title("⛽ 車隊加油紀錄系統 (SQLite 版)")

# --- 側邊欄：資料備份與匯入/匯出 ---
st.sidebar.header("📥 🗄️ 資料備份與管理")

# 1. 匯出資料
st.sidebar.subheader("匯出資料")
df_current = load_data()

if not df_current.empty:
    # 匯出 CSV
    csv_data = df_current.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button(
        label="📄 匯出成 CSV 檔案",
        data=csv_data,
        file_name=f"fuel_records_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    # 匯出 Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_current.to_excel(writer, index=False, sheet_name='加油紀錄')
    st.sidebar.download_button(
        label="📊 匯出成 Excel 檔案",
        data=buffer.getvalue(),
        file_name=f"fuel_records_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.sidebar.info("目前無資料可匯出")

st.sidebar.markdown("---")

# 2. 匯入資料
st.sidebar.subheader("匯入資料 (CSV)")
uploaded_file = st.sidebar.file_uploader("選擇備份的 CSV 檔", type=["csv"])

if uploaded_file is not None:
    if st.sidebar.button("確認匯入"):
        try:
            import_df = pd.read_csv(uploaded_file)
            # 檢查必要的欄位
            required_cols = {"time", "driver", "plate", "price", "liters", "total", "status"}
            if required_cols.issubset(set(import_df.columns)):
                conn = get_connection()
                # 排除 id 欄位，讓資料庫自動遞增生成
                cols_to_import = ["time", "driver", "plate", "price", "liters", "total", "status"]
                import_df[cols_to_import].to_sql("fuel_records", conn, if_exists="append", index=False)
                conn.close()
                st.sidebar.success("🎉 資料成功匯入資料庫！")
                st.rerun()
            else:
                st.sidebar.error("匯入失敗：CSV 格式無效，欄位不符合標準。")
        except Exception as e:
            st.sidebar.error(f"匯入錯誤：{e}")


# --- 主畫面：新增加油紀錄 ---
st.subheader("➕ 新增加油紀錄")

with st.form("fuel_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        driver = st.selectbox("👤 選擇駕駛人", DRIVERS)
        price_per_liter = st.number_input("💵 油價單價 (元/L)", min_value=0.0, value=30.0, step=0.1)
    
    with col2:
        plate = st.selectbox("🚗 選擇車牌", PLATES)
        liters = st.number_input("⛽ 加油公升數 (L)", min_value=0.0, value=20.0, step=0.5)

    submit_button = st.form_submit_button("新增紀錄並存入 SQLite")

if submit_button:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_price = round(price_per_liter * liters)

    # 存入 SQLite 資料庫
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO fuel_records (time, driver, plate, price, liters, total, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (now_str, driver, plate, price_per_liter, liters, total_price, 0))
    conn.commit()
    conn.close()

    st.success(f"✅ 已存入 SQLite！總金額為：**{total_price}** 元")
    st.rerun()

# --- 主畫面：歷史紀錄與編輯 ---
st.markdown("---")
st.subheader("📜 歷史加油紀錄管理")

df_logs = load_data()

if not df_logs.empty:
    # 重命名欄位以提升介面可讀性
    column_mapping = {
        "id": "ID",
        "time": "加油時間",
        "driver": "駕駛人",
        "plate": "車牌",
        "price": "單價 (元/L)",
        "liters": "公升數 (L)",
        "total": "總價 (元)",
        "status": "已核銷"
    }
    
    display_df = df_logs.rename(columns=column_mapping)

    # 資料編輯表格
    edited_df = st.data_editor(
        display_df,
        column_config={
            "已核銷": st.column_config.CheckboxColumn(
                "已核銷",
                help="勾選代表審核/核銷完成",
                default=False,
            )
        },
        disabled=["ID", "加油時間", "駕駛人", "車牌", "單價 (元/L)", "公升數 (L)", "總價 (元)"],
        num_rows="dynamic", # 允許刪除列
        use_container_width=True,
        key="sqlite_editor"
    )

    # 按鈕儲存變更 (包含勾選狀態與刪除項目)
    if st.button("💾 儲存表格變更 (核銷狀態 / 刪除列)"):
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. 處理刪除：找出被刪除的 ID 並從資料庫移除
        current_ids = set(edited_df["ID"].tolist())
        original_ids = set(df_logs["id"].tolist())
        deleted_ids = original_ids - current_ids

        for del_id in deleted_ids:
            cursor.execute("DELETE FROM fuel_records WHERE id = ?", (del_id,))

        # 2. 處理勾選狀態更新
        for index, row in edited_df.iterrows():
            record_id = int(row["ID"])
            status_val = 1 if row["已核銷"] else 0
            cursor.execute("UPDATE fuel_records SET status = ? WHERE id = ?", (status_val, record_id))

        conn.commit()
        conn.close()
        st.success("✅ 資料庫變更已成功儲存！")
        st.rerun()

    # 累積數據統計
    st.markdown("### 📈 累積統計")
    col_stat1, col_stat2 = st.columns(2)
    col_stat1.metric("累積總支出", f"{df_logs['total'].sum():,} 元")
    col_stat2.metric("累積總加油量", f"{df_logs['liters'].sum():.1f} L")

else:
    st.info("目前 SQLite 資料庫中沒有紀錄。")
