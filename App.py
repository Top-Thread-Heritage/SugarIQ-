import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# Page Configuration for Mobile and Desktop Viewports
st.set_page_config(page_title="Sugar IQ Control Panel", layout="wide")
st.title("Sugar IQ: C-Centrifugal Predictive Analyzer")
st.markdown("Target Overall Final Molasses Purity: **37%** | Individual Machine Target Purity Rise: **2.0 Units**")

# --- EXECUTIVE VISUAL ANCHOR: SPINNING CENTRIFUGE ANIMATION ---
st.markdown(
    """
    <div style="display: flex; align-items: center; background-color: #1E293B; padding: 15px; border-radius: 10px; margin-bottom: 20px; border-left: 5px solid #10B981;">
        <div style="
            width: 40px; 
            height: 40px; 
            border: 4px solid #334155; 
            border-top: 4px solid #10B981; 
            border-radius: 50%; 
            animation: spin 1s linear infinite;
            margin-right: 15px;
        "></div>
        <div>
            <h4 style="color: white; margin: 0; padding: 0; font-family: sans-serif;">Sugar IQ Core Engine Active</h4>
            <p style="color: #94A3B8; margin: 0; padding: 0; font-size: 13px;">Analyzing low-grade massecuite curing dynamics and screen degradation loops...</p>
        </div>
    </div>
    <style>
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """,
    unsafe_allow_html=True
)

def clean_dataframe_columns(df):
    df.columns = [str(c).strip() for c in df.columns]
    return df

def force_numeric(series):
    return pd.to_numeric(series, errors='coerce')

def process_sugar_iq_workbook(file_path):
    try:
        xl = pd.ExcelFile(file_path)
        actual_sheets = xl.sheet_names
        
        def find_sheet_by_keyword(keyword, fallback_index=0):
            kw = str(keyword).lower().strip()
            for sheet in actual_sheets:
                if kw in sheet.lower():
                    return sheet
            return actual_sheets[fallback_index]

        nutsch_sheet = find_sheet_by_keyword("nutsch", 2)      
        composite_sheet = find_sheet_by_keyword("hour", 1)   
        m1_sheet = find_sheet_by_keyword("no 1", 0)               
        m2_sheet = find_sheet_by_keyword("no 2", 1)               
        m3_sheet = find_sheet_by_keyword("no 3", 2)               
        m4_sheet = find_sheet_by_keyword("number 4", 3)               

        # Load sheets cleanly
        nutsch_df = clean_dataframe_columns(pd.read_excel(file_path, sheet_name=nutsch_sheet))
        composite_df = clean_dataframe_columns(pd.read_excel(file_path, sheet_name=composite_sheet))
        m1_df = clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m1_sheet))
        m2_df = clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m2_sheet))
        m3_df = clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m3_sheet))
        m4_df = clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m4_sheet))
        
        # Enforce clean numbers on structural sorting variables
        for frame in [nutsch_df, composite_df, m1_df, m2_df, m3_df, m4_df]:
            frame['Week No.'] = force_numeric(frame['Week No.'])
            frame['Day No.'] = force_numeric(frame['Day No.'])
            if 'Purity Nirs' in frame.columns:
                frame['Purity Nirs'] = force_numeric(frame['Purity Nirs'])
            if 'Brix Nirs' in frame.columns:
                frame['Brix Nirs'] = force_numeric(frame['Brix Nirs'])

        # Aggregate averages by Week and Day to bypass missing gaps safely
        nutsch_agg = nutsch_df.groupby(['Week No.', 'Day No.'])['Purity Nirs'].mean().reset_index().rename(columns={'Purity Nirs': 'Nutsch_Pur'})
        comp_agg = composite_df.groupby(['Week No.', 'Day No.'])['Purity Nirs'].mean().reset_index().rename(columns={'Purity Nirs': 'Overall_FMP'})
        
        master = pd.merge(nutsch_agg, comp_agg, on=['Week No.', 'Day No.'], how='outer')
        
        machines = {'M1': m1_df, 'M2': m2_df, 'M3': m3_df, 'M4': m4_df}
        for code, mdf in machines.items():
            m_agg = mdf.groupby(['Week No.', 'Day No.'])[['Purity Nirs', 'Brix Nirs']].mean().reset_index().rename(
                columns={'Purity Nirs': f'{code}_Pur', 'Brix Nirs': f'{code}_Brix'}
            )
            master = pd.merge(master, m_agg, on=['Week No.', 'Day No.'], how='left')
            master[f'{code}_Rise'] = master[f'{code}_Pur'] - master['Nutsch_Pur']
            
        master = master.sort_values(by=['Week No.', 'Day No.']).reset_index(drop=True)
        return master, None
    except Exception as e:
        return None, str(e)

# --- DATA LOADING LOOP ---
df, error_msg = process_sugar_iq_workbook("factory_data.xlsx")

if error_msg:
    st.error(f"❌ Core processing error: {error_msg}")
    st.stop()

# Generate a continuous baseline timeline for smooth machine learning curves
df = df.dropna(subset=['Week No.']).copy()
df['Timeline_Step'] = np.arange(len(df)) + 1

valid_machine_rows = df.dropna(subset=['M1_Rise', 'M3_Rise', 'M4_Rise'], how='all').copy()
latest_valid_row = valid_machine_rows.iloc[-1]
current_fmp = latest_valid_row['Overall_FMP'] if pd.notna(latest_valid_row['Overall_FMP']) else 37.0
current_week = int(latest_valid_row['Week No.'])

config_map = {'C-BMA 1': 'M1', 'C-BMA 2': 'M2', 'C-BMA 3': 'M3', 'C-BMA 4': 'M4'}
active_on_floor = [m_code for m_name, m_code in config_map.items() if pd.notna(latest_valid_row[f'{m_code}_Rise'])]

worst_machine_name = "None"
max_purity_rise = -999.0
for m_name, m_code in config_map.items():
    if m_code in active_on_floor:
        val = latest_valid_row[f'{m_code}_Rise']
        if pd.notna(val) and float(val) > max_purity_rise:
            max_purity_rise = float(val)
            worst_machine_name = m_name

all_active_high = all(latest_valid_row[f'{m}_Rise'] > 2.0 for m in active_on_floor) if len(active_on_floor) > 0 else False

# --- 2. GLOBAL STATION CRITICAL ALERT ---
if all_active_high:
    st.error("🚨 **GLOBAL STATION ALERT: PROCESS DRIFT DETECTED**")
    st.warning("**Diagnosis:** All running centrifugals show an excessive purity rise simultaneously. Fault isolated upstream to **C-massecuite quality** or crystallizer reheater settings rather than local screen damage.")
    st.info(f"🏆 **Worst Performing Unit:** {worst_machine_name} is struggling the most with a purity rise of **{max_purity_rise:.2f} units**.")
    st.markdown("---")

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric(label="Current Overall FMP", value=f"{current_fmp:.2f} %")
with kpi2:
    st.metric(label="Active Centrifugals", value=f"{len(active_on_floor)} / 4 Online")
with kpi3:
    st.metric(label="Data Log Horizon", value=f"Week {current_week} / 22")

st.markdown("### 🔮 Machine-Specific Predictive Analysis")

chart_index_flat = list(range(1, len(df) + 6))
chart_output = pd.DataFrame(index=chart_index_flat)

reg_m1, reg_m3, reg_m4 = None, None, None

# --- C-BMA 1 ---
st.markdown("#### **C-BMA 1**")
m1_rise_val = latest_valid_row['M1_Rise']
m1_brix_val = latest_valid_row['M1_Brix']
m1_history = df.dropna(subset=['M1_Rise', 'Timeline_Step']).copy()

m1_rise = float(m1_rise_val) if pd.notna(m1_rise_val) else 0.0
m1_brix = float(m1_brix_val) if pd.notna(m1_brix_val) else 0.0

if len(m1_history) >= 2:
    reg_m1 = LinearRegression().fit(m1_history['Timeline_Step'].values.reshape(-1, 1), m1_history['M1_Rise'].values.reshape(-1, 1))
    drift_m1 = float(reg_m1.coef_)
else:
    drift_m1 = -0.005

st.metric(label="C-BMA 1 Purity Rise", value=f"{m1_rise:.2f} units", delta=f"{drift_m1:+.3f} / shift" if drift_m1 != 0 else None)
st.text(f"Molasses Density: {m1_brix:.1f}°Bx")
if m1_rise > 2.0: st.error("🚨 C-BMA 1 Threshold Breached")
if m1_rise > 2.0 and m1_brix < 82.0 and m1_brix > 0: st.warning("👉 **Operator (M1):** Over-washing melting sugar. Taper manual water valves.")
if m1_rise > 2.0 and not (m1_brix < 82.0 and m1_brix > 0): st.warning("👉 **Foreman (M1):** Mechanical screen bypass. Inspect screens immediately.")
if not (m1_rise > 2.0) and drift_m1 > 0: st.warning(f"⚠️ C-BMA 1 Life Remaining: {((2.0 - m1_rise) / drift_m1):.1f} steps.")
if not (m1_rise > 2.0) and not (drift_m1 > 0): st.success("✅ C-BMA 1 Performance Stable")

m1_hist_arr = [np.nan] * len(chart_index_flat)
m1_pred_arr = [np.nan] * len(chart_index_flat)
for idx_r, row_r in df.iterrows():
    m1_hist_arr[int(row_r['Timeline_Step']) - 1] = float(row_r['M1_Rise']) if pd.notna(row_r['M1_Rise']) else np.nan
if reg_m1 is not None and pd.notna(m1_hist_arr[len(df) - 1]):
    m1_pred_arr[len(df) - 1] = m1_hist_arr[len(df) - 1]
    for fs in list(range(len(df) + 1, len(df) + 6)):
        m1_pred_arr[fs - 1] = max(0.0, float(reg_m1.predict(np.array([[fs]]))))
chart_output['C-BMA 1 (History)'] = m1_hist_arr
chart_output['C-BMA 1 (ML Projection)'] = m1_pred_arr

st.markdown("---")

# --- C-BMA 2 ---
st.markdown("#### **C-BMA 2**")
st.error("❌ MACHINE OFFLINE")
st.caption("Status: Prolonged breakdown logged.")

st.markdown("---")

# --- C-BMA 3 ---
st.markdown("#### **C-BMA 3**")
m3_rise_val = latest_valid_row['M3_Rise']
m3_brix_val = latest_valid_row['M3_Brix']
m3_history = df.dropna(subset=['M3_Rise', 'Timeline_Step']).copy()

m3_rise = float(m3_rise_val) if pd.notna(m3_rise_val) else 0.0
m3_brix = float(m3_brix_val) if pd.notna(m3_brix_val) else 0.0

if len(m3_history) >= 2:
    reg_m3 = LinearRegression().fit(m3_history['Timeline_Step'].values.reshape(-1, 1), m3_history['M3_Rise'].values.reshape(-1, 1))
    drift_m3 = float(reg_m3.coef_)
else:
    drift_m3 = -0.005

st.metric(label="C-BMA 3 Purity Rise", value=f"{m3_rise:.2f} units", delta=f"{drift_m3:+.3f} / shift" if drift_m3 != 0 else None)
st.text(f"Molasses Density: {m3_brix:.1f}°Bx")
if m3_rise > 2.0: st.error("🚨 C-BMA 3 Threshold Breached")
