import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# Page Configuration for Mobile Viewports
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
            if 'Purity Nirs' in frame.columns: frame['Purity Nirs'] = force_numeric(frame['Purity Nirs'])
            if 'Brix Nirs' in frame.columns: frame['Brix Nirs'] = force_numeric(frame['Brix Nirs'])

        # Aggregate averages by Week and Day safely
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

df = df.dropna(subset=['Week No.']).copy()
df['Timeline_Step'] = np.arange(len(df)) + 1

# Safe fallback rows extraction
v_m1 = df.dropna(subset=['M1_Rise'])
v_m3 = df.dropna(subset=['M3_Rise'])
v_m4 = df.dropna(subset=['M4_Rise'])
v_comp = df.dropna(subset=['Overall_FMP'])

current_fmp = float(v_comp.iloc[-1]['Overall_FMP']) if len(v_comp) > 0 else 37.0
current_week = int(v_comp.iloc[-1]['Week No.']) if len(v_comp) > 0 else 22

active_count = 0
if len(v_m1) > 0: active_count += 1
if len(v_m3) > 0: active_count += 1
if len(v_m4) > 0: active_count += 1

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1: st.metric(label="Current Overall FMP", value=f"{current_fmp:.2f} %")
with kpi2: st.metric(label="Active Centrifugals", value=f"{active_count} / 4 Online")
with kpi3: st.metric(label="Data Log Horizon", value=f"Week {current_week} / 22")

st.markdown("### 🔮 Machine-Specific Predictive Analysis")

chart_index_flat = list(range(1, len(df) + 6))
chart_output = pd.DataFrame(index=chart_index_flat)
reg_m1, reg_m3, reg_m4 = None, None, None

# --- C-BMA 1 ---
st.markdown("#### **C-BMA 1**")
if len(v_m1) > 0:
    row = v_m1.iloc[-1]
    m1_rise = float(row['M1_Rise'])
    m1_brix = float(row['M1_Brix']) if pd.notna(row['M1_Brix']) else 0.0
    reg_m1 = LinearRegression().fit(v_m1['Timeline_Step'].values.reshape(-1, 1), v_m1['M1_Rise'].values.reshape(-1, 1))
    drift_m1 = float(reg_m1.coef_)
    st.metric(label="C-BMA 1 Purity Rise", value=f"{m1_rise:.2f} units", delta=f"{drift_m1:+.3f} / shift" if drift_m1 != 0 else None)
    st.text(f"Molasses Density: {m1_brix:.1f}°Bx")
    if m1_rise > 2.0:
        st.error("🚨 C-BMA 1 Threshold Breached")
        st.warning("👉 **Operator Action Plan:** Over-washing melting sugar. Taper manual water valves.")
        st.info("👉 **Foreman Maintenance Plan:** Schedule physical inspection for localized basket screen bypass.")
    else: st.success("✅ C-BMA 1 Performance Stable")
else: st.error("❌ C-BMA 1 DATA OFFLINE")

# --- C-BMA 2 ---
st.markdown("---")
st.markdown("#### **C-BMA 2**")
st.error("❌ MACHINE OFFLINE")
st.caption("Status: Prolonged breakdown logged.")

# --- C-BMA 3 ---
st.markdown("---")
st.markdown("#### **C-BMA 3**")
if len(v_m3) > 0:
    row = v_m3.iloc[-1]
    m3_rise = float(row['M3_Rise'])
    m3_brix = float(row['M3_Brix']) if pd.notna(row['M3_Brix']) else 0.0
    reg_m3 = LinearRegression().fit(v_m3['Timeline_Step'].values.reshape(-1, 1), v_m3['M3_Rise'].values.reshape(-1, 1))
    drift_m3 = float(reg_m3.coef_)
    st.metric(label="C-BMA 3 Purity Rise", value=f"{m3_rise:.2f} units", delta=f"{drift_m3:+.3f} / shift" if drift_m3 != 0 else None)
    st.text(f"Molasses Density: {m3_brix:.1f}°Bx")
    if m3_rise > 2.0:
        st.error("🚨 C-BMA 3 Threshold Breached")
        st.warning("👉 **Operator Action Plan:** Over-washing melting sugar. Taper manual water valves.")
        st.info("👉 **Foreman Maintenance Plan:** Schedule physical inspection for localized basket screen bypass.")
    else: st.success("✅ C-BMA 3 Performance Stable")
else: st.error("❌ C-BMA 3 DATA OFFLINE")

# --- C-BMA 4 ---
st.markdown("---")
st.markdown("#### **C-BMA 4**")
if len(v_m4) > 0:
    row = v_m4.iloc[-1]
    m4_rise = float(row['M4_Rise'])
    m4_brix = float(row['M4_Brix']) if pd.notna(row['M4_Brix']) else 0.0
    reg_m4 = LinearRegression().fit(v_m4['Timeline_Step'].values.reshape(-1, 1), v_m4['M4_Rise'].values.reshape(-1, 1))
    drift_m4 = float(reg_m4.coef_)
    st.metric(label="C-BMA 4 Purity Rise", value=f"{m4_rise:.2f} units", delta=f"{drift_m4:+.3f} / shift" if drift_m4 != 0 else None)
    st.text(f"Molasses Density: {m4_brix:.1f}°Bx")
    if m4_rise > 2.0:
        st.error("🚨 C-BMA 4 Threshold Breached")
        st.warning("👉 **Operator Action Plan:** Over-washing melting sugar. Taper manual water valves.")
        st.info("👉 **Foreman Maintenance Plan:** Schedule physical inspection for localized basket screen bypass.")
    else: st.success("✅ C-BMA 4 Performance Stable")
else: st.error("❌ C-BMA 4 DATA OFFLINE")

# --- MASTER CHART MATRIX PREPARATION (ZERO-LOOP FORECAST EXTRAPOLATION) ---
chart_output['C-BMA 1 (History)'] = pd.Series(df['M1_Rise'].values, index=range(1, len(df)+1))
chart_output['C-BMA 3 (History)'] = pd.Series(df['M3_Rise'].values, index=range(1, len(df)+1))
chart_output['C-BMA 4 (History)'] = pd.Series(df['M4_Rise'].values, index=range(1, len(df)+1))

# Unroll Machine 1 Predictions Flatly
p1 = [np.nan] * (len(df) + 5)
if reg_m1 is not None and len(df) > 0:
    p1[len(df)-1] = float(df['M1_Rise'].dropna().values[-1])
    p1[len(df)] = max(0.0, float(reg_m1.predict([[len(df) + 1]])))
    p1[len(df)+1] = max(0.0, float(reg_m1.predict([[len(df) + 2]])))
    p1[len(df)+2] = max(0.0, float(reg_m1.predict([[len(df) + 3]])))
    p1[len(df)+3] = max(0.0, float(reg_m1.predict([[len(df) + 4]])))
    p1[len(df)+4] = max(0.0, float(reg_m1.predict([[len(df) + 5]])))
chart_output['C-BMA 1 (ML Projection)'] = pd.Series(p1, index=chart_index_flat)

# Unroll Machine 3 Predictions Flatly
p3 = [np.nan] * (len(df) + 5)
if reg_m3 is not None and len(df) > 0:
    p3[len(df)-1] = float(df['M3_Rise'].dropna().values[-1])
