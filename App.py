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

def add_positional_sequence_index(df):
    if 'Week No.' in df.columns and 'Day No.' in df.columns:
        df['Daily_Sequence_Order'] = df.groupby(['Week No.', 'Day No.']).cumcount()
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

        nutsch_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=nutsch_sheet)))
        composite_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=composite_sheet)))
        
        m1_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m1_sheet)))
        m2_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m2_sheet)))
        m3_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m3_sheet)))
        m4_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m4_sheet)))
                
        nutsch_base = nutsch_df[['Week No.', 'Day No.', 'Daily_Sequence_Order', 'Purity Nirs']].rename(columns={'Purity Nirs': 'Nutsch_Pur'})
        comp_base = composite_df[['Week No.', 'Day No.', 'Daily_Sequence_Order', 'Purity Nirs']].rename(columns={'Purity Nirs': 'Overall_FMP'})
        
        master = pd.merge(nutsch_base, comp_base, on=['Week No.', 'Day No.', 'Daily_Sequence_Order'], how='outer')
        
        machines = {'M1': m1_df, 'M2': m2_df, 'M3': m3_df, 'M4': m4_df}
        for code, mdf in machines.items():
            master = pd.merge(master, mdf[['Week No.', 'Day No.', 'Daily_Sequence_Order', 'Purity Nirs', 'Brix Nirs']].rename(columns={'Purity Nirs': f'{code}_Pur', 'Brix Nirs': f'{code}_Brix'}), on=['Week No.', 'Day No.', 'Daily_Sequence_Order'], how='left')
            master[f'{code}_Pur'] = force_numeric(master[f'{code}_Pur'])
            master[f'{code}_Brix'] = force_numeric(master[f'{code}_Brix'])
            master[f'{code}_Rise'] = master[f'{code}_Pur'] - force_numeric(master['Nutsch_Pur'])
            
        master['Nutsch_Pur'] = force_numeric(master['Nutsch_Pur'])
        master['Overall_FMP'] = force_numeric(master['Overall_FMP'])
        master = master.sort_values(by=['Week No.', 'Day No.', 'Daily_Sequence_Order']).reset_index(drop=True)
        return master, None
    except Exception as e:
        return None, str(e)

# --- DATA LOADING ---
df, error_msg = process_sugar_iq_workbook("factory_data.xlsx")

valid_machine_rows = df.dropna(subset=['M1_Rise', 'M2_Rise', 'M3_Rise', 'M4_Rise'], how='all').copy()
# Create an automatic, guaranteed numerical index for smooth mathematical graphing
valid_machine_rows['Timeline_Step'] = np.arange(len(valid_machine_rows)) + 1

latest_valid_row = valid_machine_rows.iloc[-1]
current_fmp = latest_valid_row['Overall_FMP'] if pd.notna(latest_valid_row['Overall_FMP']) else 37.0
current_week = int(latest_valid_row['Week No.']) if pd.notna(latest_valid_row['Week No.']) else 22

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
    st.error(f"🚨 **GLOBAL STATION ALERT: PROCESS DRIFT**\\n\\nAll running centrifugals show high purity rise. Upstream issue: check C-massecuite conditioning or false grain.\\n\\n🏆 Worst Machine: **{worst_machine_name}** ({max_purity_rise:.2f} units).")
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

# Dictionary to hold models built on our automatic timeline step counter
models_dict = {}

for idx, (m_name, m_code) in enumerate(config_map.items()):
    with machine_cards[idx]:
        st.subheader(m_name)
        if pd.isna(latest_valid_row[f'{m_code}_Rise']):
            st.error("❌ MACHINE OFFLINE")
            continue
            
        m_rise = float(latest_valid_row[f'{m_code}_Rise'])
        m_brix_val = float(latest_valid_row[f'{m_code}_Brix']) if pd.notna(latest_valid_row[f'{m_code}_Brix']) else 0.0
        
        # Build clean history arrays
        m_history = valid_machine_rows.dropna(subset=[f'{m_code}_Rise']).copy()
        
        drift_velocity = 0.0
        if len(m_history) >= 4:
            X_time = m_history['Timeline_Step'].values.reshape(-1, 1)
            y_rise = m_history[f'{m_code}_Rise'].values.reshape(-1, 1)
            reg = LinearRegression().fit(X_time, y_rise)
            models_dict[m_code] = reg
            drift_velocity = float(reg.coef_[0][0]) if hasattr(reg.coef_, "__getitem__") and hasattr(reg.coef_[0], "__getitem__") else float(reg.coef_[0]) if hasattr(reg.coef_, "__getitem__") else float(reg.coef_)
            
        st.metric(label="Purity Rise", value=f"{m_rise:.2f} units", delta=f"{drift_velocity:+.3f} / shift" if drift_velocity != 0 else None)
        st.text(f"Molasses Density: {m_brix_val:.1f}°Bx")
        
        if m_rise > 2.0:
            st.error("🚨 Threshold Breached")
            if m_brix_val < 82.0 and m_brix_val > 0:
                st.warning("👉 **Operator:** Over-washing melting sugar. Taper water valves.")
            else:
                st.warning("👉 **Foreman:** Mechanical screen bypass. Inspect screens.")
        else:
            if drift_velocity > 0:
                runs_left = (2.0 - m_rise) / drift_velocity
                st.warning(f"⚠️ Life: {runs_left:.1f} shifts.")
            else:
                st.success("✅ Stable")

# --- HISTORICAL & ML PROJECTION CHART SECTION ---
st.markdown("### 📈 Machine Learning Projections & Trend Overviews")

total_historical_steps = len(valid_machine_rows)
future_steps = [total_historical_steps + 1, total_historical_steps + 2, total_historical_steps + 3, total_historical_steps + 4, total_historical_steps + 5]

# Build clean mapping summary arrays
chart_index = list(range(1, total_historical_steps + 6))
chart_output = pd.DataFrame(index=chart_index)

for m_name, m_code in config_map.items():
    hist_series = [np.nan] * len(chart_index)
    pred_series = [np.nan] * len(chart_index)
    
    # Fill actual history data
    for i, row in valid_machine_rows.iterrows():
        step = int(row['Timeline_Step'])
        hist_series[step - 1] = float(row[f'{m_code}_Rise'])
        
    # Fill prediction trend extrapolation line points
    if m_code in models_dict:
        # Snap the connection point to avoid graph gaps
        pred_series[total_historical_steps - 1] = hist_series[total_historical_steps - 1]
        for idx_fs, fs in enumerate(future_steps):
            pred_val = float(models_dict[m_code].predict(np.array([[fs]])))
            pred_series[fs - 1] = max(0.0, pred_val)
            
    chart_output[f'{m_name} (History)'] = hist_series
