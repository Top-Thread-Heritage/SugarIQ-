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

        # Aggregate averages by Week and Day to bypass missing intra-day timestamp gaps safely
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

latest_valid_row = df.dropna(subset=['M1_Rise', 'M3_Rise', 'M4_Rise'], how='all').iloc[-1]
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

if all_active_high:
    st.error(f"🚨 **GLOBAL STATION ALERT: PROCESS DRIFT DETECTED**\\n\\nAll running centrifugals show high purity rise. Upstream issue: check C-massecuite conditioning or false grain.\\n\\n🏆 Worst Machine: **{worst_machine_name}** ({max_purity_rise:.2f} units).")
    st.markdown("---")

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric(label="Current Composite FMP", value=f"{current_fmp:.2f} %")
with kpi2:
    st.metric(label="Active Centrifugals", value=f"{len(active_on_floor)} / 4 Online")
with kpi3:
    st.metric(label="Data Log Horizon", value=f"Week {current_week} / 22")

st.markdown("### 🔮 Machine-Specific Predictive Analysis")
machine_cards = st.columns(4)

models_dict = {}

for idx, (m_name, m_code) in enumerate(config_map.items()):
    with machine_cards[idx]:
        st.subheader(m_name)
        if pd.isna(latest_valid_row[f'{m_code}_Rise']):
            st.error("❌ MACHINE OFFLINE")
            st.caption("Status: Prolonged breakdown logged.")
            continue
            
        m_rise = float(latest_valid_row[f'{m_code}_Rise'])
        m_brix_val = float(latest_valid_row[f'{m_code}_Brix']) if pd.notna(latest_valid_row[f'{m_code}_Brix']) else 0.0
        
        m_history = df.dropna(subset=[f'{m_code}_Rise']).copy()
        
        drift_velocity = 0.0
        if len(m_history) >= 3:
            X_time = m_history['Timeline_Step'].values.reshape(-1, 1)
            y_rise = m_history[f'{m_code}_Rise'].values.reshape(-1, 1)
            reg = LinearRegression().fit(X_time, y_rise)
            models_dict[m_code] = reg
            drift_velocity = float(reg.coef_[0][0]) if hasattr(reg.coef_, "ndim") and reg.coef_.ndim > 1 else float(reg.coef_[0]) if hasattr(reg.coef_, "__getitem__") else float(reg.coef_)
            
        st.metric(label="Purity Rise", value=f"{m_rise:.2f} units", delta=f"{drift_velocity:+.3f} / run" if drift_velocity != 0 else None)
        st.text(f"Molasses Density: {m_brix_val:.1f}°Bx")
        
        is_breached = m_rise > 2.0
        is_low_brix = m_brix_val < 82.0 and m_brix_val > 0
        
        if is_breached:
            st.error("🚨 Threshold Breached")
        if is_breached and is_low_brix:
            st.warning("👉 **Operator:** Over-washing melting sugar. Taper manual water valves.")
        if is_breached and not is_low_brix:
            st.warning("👉 **Foreman:** Mechanical screen bypass. Inspect screens immediately.")
        if not is_breached and drift_velocity > 0:
            runs_left = (2.0 - m_rise) / drift_velocity
            st.warning(f"⚠️ Life Remaining: {runs_left:.1f} steps.")
        if not is_breached and not drift_velocity > 0:
            st.success("✅ Performance Stable")

# --- HISTORICAL & ML GRAPH PROJECTIONS SECTION ---
st.markdown("### 📈 Machine Learning Projections & Trend Overviews (Weeks 1-22 + Forecast)")

total_historical_steps = len(df)
future_steps = list(range(total_historical_steps + 1, total_historical_steps + 6))
chart_index = list(range(1, total_historical_steps + 6))

chart_output = pd.DataFrame(index=chart_index)

for m_name, m_code in config_map.items():
    hist_series = [np.nan] * len(chart_index)
    pred_series = [np.nan] * len(chart_index)
    
    # Populate historical trends perfectly
    for idx_row, row in df.iterrows():
        step = int(row['Timeline_Step'])
        val = row[f'{m_code}_Rise']
        hist_series[step - 1] = float(val) if pd.notna(val) else np.nan
        
    # Extrapolate 3-week predictive future trend line
    if m_code in models_dict:
        pred_series[total_historical_steps - 1] = hist_series[total_historical_steps - 1]
        for fs in future_steps:
            pred_val = float(models_dict[m_code].predict(np.array([[fs]])))
            pred_series[fs - 1] = max(0.0, pred_val)
            
    chart_output[f'{m_name} (History)'] = hist_series
    chart_output[f'{m_name} (ML Projection)'] = pred_series

# Force axis keys to professional display labels
chart_output.index.name = 'Chronological Entry Step'
