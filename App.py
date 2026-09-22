import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# Page Configuration for Mobile and Desktop
st.set_page_config(page_title="Sugar IQ Control Panel", layout="wide")
st.title("Sugar IQ: C-Centrifugal Predictive Analyzer")
st.markdown("Target Overall Final Molasses Purity: **37%** | Individual Machine Target Purity Rise: **2.0 Units**")

def clean_dataframe_columns(df):
    """Trims trailing spaces from column names to prevent alignment errors."""
    df.columns = [str(c).strip() for c in df.columns]
    return df

def add_sequence_index(df):
    """
    Groups data by Date/Day and creates a sequential order index (0, 1, 2...)
    based on your exact columns: 'Week No.', 'Day No.', and 'Test Time'.
    """
    if 'Test Time' in df.columns and 'Week No.' in df.columns and 'Day No.' in df.columns:
        df['Daily_Sequence_Order'] = df.groupby(['Week No.', 'Day No.', 'Test Time']).cumcount()
    return df

def process_sugar_iq_workbook(file_path):
    try:
        # Read the actual sheets that exist inside the uploaded workbook
        xl = pd.ExcelFile(file_path)
        actual_sheets = xl.sheet_names
        
        def find_sheet_by_keyword(keyword, fallback_index=0):
            """Scans all sheet names in the Excel file and matches based on a keyword search."""
            kw = str(keyword).lower().strip()
            for sheet in actual_sheets:
                if kw in sheet.lower():
                    return sheet
            return actual_sheets[fallback_index]

        # Smart keyword matching to locate your tabs flexibly
        nutsch_sheet = find_sheet_by_keyword("nutsch", 2)      
        composite_sheet = find_sheet_by_keyword("hour", 1)   
        m1_sheet = find_sheet_by_keyword("no 1", 0)               
        m2_sheet = find_sheet_by_keyword("no 2", 0)               
        m3_sheet = find_sheet_by_keyword("no 3", 0)               
        m4_sheet = find_sheet_by_keyword("no 4", 0)               

        # Load and index data sheets matching your exact column names
        nutsch_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=nutsch_sheet)))
        composite_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=composite_sheet)))
        
        m1_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m1_sheet)))
        m2_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m2_sheet)))
        m3_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m3_sheet)))
        m4_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file_path, sheet_name=m4_sheet)))
                
        # Isolate baseline parameters matching your precise casing
        nutsch_base = nutsch_df[['Week No.', 'Day No.', 'Test Time', 'Daily_Sequence_Order', 'Purity Nirs']].rename(columns={'Purity Nirs': 'Nutsch_Pur'})
        comp_base = composite_df[['Week No.', 'Day No.', 'Test Time', 'Daily_Sequence_Order', 'Purity Nirs']].rename(columns={'Purity Nirs': 'Overall_FMP'})
        
        # Merge key columns frame
        master = pd.merge(nutsch_base, comp_base, on=['Week No.', 'Day No.', 'Test Time', 'Daily_Sequence_Order'], how='outer')
        
        # Loop through machines using multi-index tracking
        machines = {'M1': m1_df, 'M2': m2_df, 'M3': m3_df, 'M4': m4_df}
        for code, mdf in machines.items():
            m_sub = mdf[['Week No.', 'Day No.', 'Test Time', 'Daily_Sequence_Order', 'Purity Nirs', 'Brix Nirs']].rename(
                columns={'Purity Nirs': f'{code}_Pur', 'Brix Nirs': f'{code}_Brix'}
            )
            master = pd.merge(master, m_sub, on=['Week No.', 'Day No.', 'Test Time', 'Daily_Sequence_Order'], how='left')
            
            # Dynamic calculation matching your process logic
            master[f'{code}_Rise'] = master[f'{code}_Pur'] - master['Nutsch_Pur']
            
        master = master.sort_values(by=['Week No.', 'Day No.', 'Test Time', 'Daily_Sequence_Order']).reset_index(drop=True)
        return master, None
    except Exception as e:
        return None, str(e)

# --- AUTOMATED DATA LOADING LAYER ---
try:
    df, error_msg = process_sugar_iq_workbook("factory_data.xlsx")
    if error_msg:
        st.error(f"❌ Structural error reading repo file. Details: {error_msg}")
        st.stop()
except FileNotFoundError:
    st.error("❌ Data Source Missing: Please ensure 'factory_data.xlsx' is uploaded directly to your GitHub repository root.")
    st.stop()

# Isolate latest recorded laboratory entries
latest_valid_row = df.dropna(subset=['Overall_FMP']).iloc[-1]
current_fmp = latest_valid_row['Overall_FMP']
current_week = int(latest_valid_row['Week No.'])

# --- 2. STATION-WIDE GLOBAL ANALYSIS LAYER (UPSTREAM INSPECTION) ---
possible_machines = ['M1', 'M2', 'M3', 'M4']
active_on_floor = [m for m in possible_machines if not pd.isna(latest_valid_row[f'{m}_Rise'])]
all_active_high = all(latest_valid_row[f'{m}_Rise'] > 2.0 for m in active_on_floor) if len(active_on_floor) > 0 else False

if all_active_high:
    st.error(
        f"🚨 **GLOBAL STATION CRITICAL ALERT: PROCESS DRIFT DETECTED**\n\n"
        f"**Diagnosis:** All currently running centrifugals are showing an excessive purity rise simultaneously. "
        f"This isolates the fault away from individual screens or localized water leakage.\n\n"
        f"👉 **Immediate Action Plan:** Notify the Boiling House Foreman to check **C-massecuite quality**. "
        f"Inspect the C-crystallizer reheater performance or pan logs for active **false grain presence**."
    )
    st.markdown("---")

# --- 3. EXECUTIVE CORE VISUALIZATION LAYER ---
kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric(label="Current Composite FMP", value=f"{current_fmp:.2f} %", delta=f"{current_fmp - 37.0:+.2f} % vs Target 37%")
with kpi2:
    st.metric(label="Active Centrifugals", value=f"{len(active_on_floor)} / 4 Online", 
              delta="C-BMA 2 Prolonged Breakdown Active" if 'M2' not in active_on_floor else "All Units Synchronized")
with kpi3:
    st.metric(label="Data Log Horizon", value=f"Week {current_week} / 22", delta="Automated Keyphrase Mapping Active")

# --- 4. PROGNOSTIC & PRESCRIPTIVE ENGINE ---
st.markdown("### 🔮 Predictive Performance & Prescriptive Actions")
machine_cards = st.columns(4)
config_map = {'C-BMA 1': 'M1', 'C-BMA 2': 'M2', 'C-BMA 3': 'M3', 'C-BMA 4': 'M4'}

for idx, (m_name, m_code) in enumerate(config_map.items()):
    with machine_cards[idx]:
        st.subheader(m_name)
        if pd.isna(latest_valid_row[f'{m_code}_Rise']):
            st.error("❌ MACHINE OFFLINE\n\nStatus: Prolonged breakdown logged. Station data loop automatically bypassed.")
            continue
            
        m_rise = latest_valid_row[f'{m_code}_Rise']
        m_brix = latest_valid_row[f'{m_code}_Brix']
        
        m_history = df.dropna(subset=[f'{m_code}_Rise'])
        if len(m_history) >= 4:
            X_time = np.array(range(len(m_history))).reshape(-1, 1)
            y_rise = m_history[f'{m_code}_Rise'].values
            reg = LinearRegression().fit(X_time, y_rise)
            drift_velocity = reg.coef_
        else:
            drift_velocity = 0.0
            
        st.metric(label="Calculated Purity Rise", value=f"{m_rise:.2f} units", delta=f"{drift_velocity:+.3f} units/analysis")
        st.text(f"Molasses Density: {m_brix:.1f}°Bx")
        
        if m_rise > 2.0:
            st.error("🚨 Threshold Breached (>2.0 Target)")
            if all_active_high:
                st.caption("⚠️ See Global Upstream Massecuite Warning Above.")
            elif m_brix < 82.0:
                st.warning(f"👉 **Operator Insight:** Density too low ({m_brix}°Bx). Over-washing melting sugar. Restrict manual valve timer.")
            else:
                st.warning(f"👉 **Foreman Insight:** Density optimal ({m_brix}°Bx) but purity rise is high. Mechanical screen bypass. Inspect screens immediately.")
        else:
            if drift_velocity > 0:
                runs_until_breach = (2.0 - m_rise) / drift_velocity
                if runs_until_breach < 6:
                    st.warning(f"⚠️ Predictive Alert\nScreen failure projected within {runs_until_breach:.1f} operational analyses.")
                else:
                    st.success(f"✅ Performance Stable\nEst. screen life remaining: {runs_until_breach:.1f} analyses.")
            else:
                st.success("✅ Performance Stable\nNo upward degradation drift detected.")

