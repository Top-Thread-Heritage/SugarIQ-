import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# Page Configuration for Mobile and Desktop
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
    """Trims trailing spaces from column names to prevent alignment errors."""
    df.columns = [str(c).strip() for c in df.columns]
    return df

def add_positional_sequence_index(df):
    """Creates a sequential order index based strictly on row positions."""
    if 'Week No.' in df.columns and 'Day No.' in df.columns:
        df['Daily_Sequence_Order'] = df.groupby(['Week No.', 'Day No.']).cumcount()
    return df

def force_numeric(series):
    """Safely converts any text dashes, spaces, or N/As into clean numbers or NaN."""
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
        m2_sheet = find_sheet_by_keyword("no 2", 0)               
        m3_sheet = find_sheet_by_keyword("no 3", 0)               
        m4_sheet = find_sheet_by_keyword("no 4", 0)               

        nutsch_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=nutsch_sheet)))
        composite_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=composite_sheet)))
        
        m1_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m1_sheet)))
        m2_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m2_sheet)))
        m3_df = add_sequence_index = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m3_sheet)))
        m4_df = add_positional_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m4_sheet)))
                
        nutsch_base = nutsch_df[['Week No.', 'Day No.', 'Daily_Sequence_Order', 'Purity Nirs']].rename(columns={'Purity Nirs': 'Nutsch_Pur'})
        comp_base = composite_df[['Week No.', 'Day No.', 'Daily_Sequence_Order', 'Purity Nirs']].rename(columns={'Purity Nirs': 'Overall_FMP'})
        
        master = pd.merge(nutsch_base, comp_base, on=['Week No.', 'Day No.', 'Daily_Sequence_Order'], how='outer')
        
        machines = {'M1': m1_df, 'M2': m2_df, 'M3': m3_df, 'M4': m4_df}
        for code, mdf in machines.items():
            m_sub = mdf[['Week No.', 'Day No.', 'Daily_Sequence_Order', 'Purity Nirs', 'Brix Nirs']].rename(
                columns={'Purity Nirs': f'{code}_Pur', 'Brix Nirs': f'{code}_Brix'}
            )
            master = pd.merge(master, m_sub, on=['Week No.', 'Day No.', 'Daily_Sequence_Order'], how='left')
            
            master[f'{code}_Pur'] = force_numeric(master[f'{code}_Pur'])
            master[f'{code}_Brix'] = force_numeric(master[f'{code}_Brix'])
            master['Nutsch_Pur'] = force_numeric(master['Nutsch_Pur'])
            master['Overall_FMP'] = force_numeric(master['Overall_FMP'])
            
            master[f'{code}_Rise'] = master[f'{code}_Pur'] - master['Nutsch_Pur']
            
        master = master.sort_values(by=['Week No.', 'Day No.', 'Daily_Sequence_Order']).reset_index(drop=True)
        return master, None
    except Exception as e:
        return None, str(e)

# --- AUTOMATED DATA LOADING LAYER ---
try:
    df, error_msg = process_sugar_iq_workbook("factory_data.xlsx")
    if error_msg:
        st.error(f"❌ Structural error reading file: {error_msg}")
        st.stop()
except FileNotFoundError:
    st.error("❌ Data Source Missing: Please ensure 'factory_data.xlsx' is in your repo.")
    st.stop()

valid_machine_rows = df.dropna(subset=['M1_Rise', 'M2_Rise', 'M3_Rise', 'M4_Rise'], how='all')
if len(valid_machine_rows) == 0:
    st.error("❌ No overlapping valid numerical records found. Please check columns.")
    st.stop()

latest_valid_row = valid_machine_rows.iloc[-1]
current_fmp = latest_valid_row['Overall_FMP'] if not pd.isna(latest_valid_row['Overall_FMP']) else df.dropna(subset=['Overall_FMP']).iloc[-1]['Overall_FMP']
current_week = int(latest_valid_row['Week No.'])

possible_machines = ['M1', 'M2', 'M3', 'M4']
config_labels = {'M1': 'C-BMA 1', 'M2': 'C-BMA 2', 'M3': 'C-BMA 3', 'M4': 'C-BMA 4'}
active_on_floor = [m for m in possible_machines if not pd.isna(latest_valid_row[f'{m}_Rise'])]

worst_machine_code = None
max_purity_rise = -999.0
for m in active_on_floor:
    val = float(latest_valid_row[f'{m}_Rise'])
    if val > max_purity_rise:
        max_purity_rise = val
        worst_machine_code = m

all_active_high = all(latest_valid_row[f'{m}_Rise'] > 2.0 for m in active_on_floor) if len(active_on_floor) > 0 else False

if all_active_high:
    st.error(
        f"🚨 **GLOBAL STATION ALERT: PROCESS DRIFT DETECTED**\n\n"
        f"**Diagnosis:** All running centrifugals show excessive purity rise simultaneously. Fault isolated upstream to **C-massecuite quality** or reheater settings.\n\n"
        f"🏆 **Worst Performing Unit:** **{config_labels[worst_machine_code]}** is struggling the most with an extreme purity rise of **{max_purity_rise:.2f} units**."
    )
    st.markdown("---")

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric(label="Current Composite FMP", value=f"{current_fmp:.2f} %" if not pd.isna(current_fmp) else "N/A")
with kpi2:
    st.metric(label="Active Centrifugals", value=f"{len(active_on_floor)} / 4 Online")
with kpi3:
    st.metric(label="Data Log Horizon", value=f"Week {current_week} / 22")

st.markdown("### 🔮 Machine-Specific Predictive Analysis")
machine_cards = st.columns(4)

for idx, (m_name, m_code) in enumerate(config_labels.items()):
    with machine_cards[idx]:
        st.subheader(m_name)
        if pd.isna(latest_valid_row[f'{m_code}_Rise']):
            st.error("❌ MACHINE OFFLINE\n\nStatus: Prolonged breakdown logged.")
            continue
            
        m_rise = float(latest_valid_row[f'{m_code}_Rise'])
        m_brix = latest_valid_row[f'{m_code}_Brix']
        m_brix_val = float(m_brix) if not pd.isna(m_brix) else 0.0
        
        m_history = df.dropna(subset=[f'{m_code}_Rise'])
        if len(m_history) >= 4:
            X_time = np.array(range(len(m_history))).reshape(-1, 1)
            y_rise = m_history[f'{m_code}_Rise'].values.astype(float)
            reg = LinearRegression().fit(X_time, y_rise)
            drift_velocity = float(reg.coef_)
        else:
            drift_velocity = 0.0
            
        st.metric(label="Purity Rise", value=f"{m_rise:.2f} units", delta=f"{drift_velocity:+.3f} / run" if drift_velocity != 0 else None)
        st.text(f"Molasses Density: {m_brix_val:.1f}°Bx" if m_brix_val > 0 else "Density: N/A")
        
        if m_rise > 2.0:
            st.error("🚨 Threshold Breached")
            if m_brix_val < 82.0 and m_brix_val > 0:
                st.warning("👉 **Operator:** Over-washing melting sugar. Taper manual water valves.")
            else:
                st.warning("👉 **Foreman:** Mechanical screen bypass. Inspect for tears immediately.")
        else:
            if drift_velocity > 0:
                runs_left = (2.0 - m_rise) / drift_velocity
                if runs_left < 6:
                    st.warning(f"⚠️ Warning\nScreen breach projected in {runs_left:.1f} runs.")
                else:
                    st.success(f"✅ Stable\nLife: {runs_left:.1f} runs.")
            else:
                st.success("✅ Stable\nNo degradation drift.")

st.markdown("### 📈 Long-Term Historical Performance Trends (Weeks 1-22)")
trend_data = df.dropna(subset=['Week No.']).copy()
trend_data = trend_data.groupby(['Week No.'])[['M1_Rise', 'M2_Rise', 'M3_Rise', 'M4_Rise']].mean()
st.line_chart(trend_data)
