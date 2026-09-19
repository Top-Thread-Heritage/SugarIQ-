import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

# Page Configuration for Mobile and Desktop
st.set_page_config(page_title="Sugar IQ Control Panel", layout="wide")
st.title("Sugar IQ: C-Centrifugal Predictive Analyzer")
st.markdown("Target Overall Final Molasses Purity: **37%** | Individual Machine Target Purity Rise: **2.0 Units**")

# 1. SIDEBAR: Excel File Provisioning
st.sidebar.header("📁 Data Provisioning Panel")
uploaded_file = st.sidebar.file_uploader("Upload Multi-Sheet Factory Excel Log (.xlsx)", type=["xlsx"])

def clean_dataframe_columns(df):
    """Trims trailing spaces from column names to prevent alignment errors."""
    df.columns = [str(c).strip() for c in df.columns]
    return df

def add_sequence_index(df):
    """
    Groups data by Date/Day and creates a sequential order index (0, 1, 2...)
    for multiple daily analyses to ensure perfect row-by-row chronological matching.
    """
    # Use 'Test time (date)' if present, otherwise fallback to 'Test time'
    date_col = 'Test time (date)' if 'Test time (date)' in df.columns else 'Test time'
    if date_col in df.columns:
        # Create an order index based on the sequence of information for that specific date
        df['Daily_Sequence_Order'] = df.groupby(['week No.', 'Day No.', date_col]).cumcount()
        df.rename(columns={date_col: 'Test_Time'}, inplace=True)
    return df

def process_sugar_iq_workbook(file):
    try:
        # Load sheets exactly matching your real sheet names
        nutsch_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file, sheet_name="C massecuite curing Nutsch")))
        composite_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file, sheet_name="final molasses 2 hours composite")))
        
        m1_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file, sheet_name="C molasses machine no 1")))
        m2_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file, sheet_name="C molasses machine No 2")))
        m3_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file, sheet_name="C molasses machine No 3")))
        m4_df = add_sequence_index(clean_dataframe_columns(pd.read_excel(file, sheet_name="C molasses machine number 4")))
                
        # Isolate the essential baseline values
        nutsch_base = nutsch_df[['week No.', 'Day No.', 'Test_Time', 'Daily_Sequence_Order', 'Purity Nirs']].rename(columns={'Purity Nirs': 'Nutsch_Pur'})
        comp_base = composite_df[['week No.', 'Day No.', 'Test_Time', 'Daily_Sequence_Order', 'Purity Nirs']].rename(columns={'Purity Nirs': 'Overall_FMP'})
        
        # Build master base frame linking time blocks and test sequences together
        master = pd.merge(nutsch_base, comp_base, on=['week No.', 'Day No.', 'Test_Time', 'Daily_Sequence_Order'], how='outer')
        
        # Loop through each machine using both Date AND Sequence Order for alignment
        machines = {'M1': m1_df, 'M2': m2_df, 'M3': m3_df, 'M4': m4_df}
        for code, mdf in machines.items():
            m_sub = mdf[['week No.', 'Day No.', 'Test_Time', 'Daily_Sequence_Order', 'Purity Nirs', 'Brix Nirs']].rename(
                columns={'Purity Nirs': f'{code}_Pur', 'Brix Nirs': f'{code}_Brix'}
            )
            master = pd.merge(master, m_sub, on=['week No.', 'Day No.', 'Test_Time', 'Daily_Sequence_Order'], how='left')
            
            # THE CORE CALCULATION: Machine Purity Nirs minus Nutsch Baseline Purity Nirs
            master[f'{code}_Rise'] = master[f'{code}_Pur'] - master['Nutsch_Pur']
            
        master = master.sort_values(by=['week No.', 'Day No.', 'Test_Time', 'Daily_Sequence_Order']).reset_index(drop=True)
        return master, None
    except Exception as e:
        return None, str(e)

# Check deployment state
if uploaded_file is not None:
    df, error_msg = process_sugar_iq_workbook(uploaded_file)
    if error_msg:
        st.error(f"❌ Structural error reading sheets. Please check names. Details: {error_msg}")
        st.stop()
    st.sidebar.success("✅ Factory dataset successfully compiled and synced!")
else:
    st.sidebar.warning("Awaiting Excel log upload via sidebar to initialize calculations.")
    st.info("💡 **Presentation Tip:** Upload your real 22-week workbook during the meeting to show live processing.")
    st.stop()

# --- 2. EXECUTIVE CORE VISUALIZATION LAYER ---
# Isolate latest recorded laboratory entries
latest_valid_row = df.dropna(subset=['Overall_FMP']).iloc[-1]
current_fmp = latest_valid_row['Overall_FMP']
current_week = int(latest_valid_row['week No.'])

# Top KPI Summary Cards
kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric(label="Current Composite FMP", value=f"{current_fmp:.2f} %", delta=f"{current_fmp - 37.0:+.2f} % vs Target 37%")
with kpi2:
    active_units = [m for m in ['M1', 'M2', 'M3', 'M4'] if not pd.isna(latest_valid_row[f'{m}_Rise'])]
    st.metric(label="Active Centrifugals", value=f"{len(active_units)} / 4 Online", 
              delta="C-BMA 2 Breakdown Active" if 'M2' not in active_units else "All Units Synchronized")
with kpi3:
    st.metric(label="Data Log Horizon", value=f"Week {current_week} / 22", delta="Historical Sequence Tracking Active")

# --- 3. PROGNOSTIC & PRESCRIPTIVE ENGINE ---
st.markdown("### 🔮 Predictive Performance & Prescriptive Actions")
machine_cards = st.columns(4)
config_map = {'C-BMA 1': 'M1', 'C-BMA 2': 'M2', 'C-BMA 3': 'M3', 'C-BMA 4': 'M4'}

for idx, (m_name, m_code) in enumerate(config_map.items()):
    with machine_cards[idx]:
        st.subheader(m_name)
        
        # Dynamic breakdown resilience check for C-BMA 2 stopping at Week 10
        if pd.isna(latest_valid_row[f'{m_code}_Rise']):
            st.error("❌ MACHINE OFFLINE\n\nStatus: Prolonged breakdown logged. Station data loop automatically bypassed to prevent skewing averages.")
            continue
            
        m_rise = latest_valid_row[f'{m_code}_Rise']
        m_brix = latest_valid_row[f'{m_code}_Brix']
        
        # Calculate time-series linear regression drift over historical data rows
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
        
        # Sugar Engineering Rule-Based Insights
        if m_rise > 2.0:
            st.error("🚨 Threshold Breached (>2.0 Target)")
            if m_brix < 82.0:
                st.warning(f"👉 **Operator Insight:** Density is too low ({m_brix}°Bx). Hot wash water is melting sugar. Restrict manual valve timers immediately.")
            else:
                st.warning(f"👉 **Foreman Insight:** Density is optimal ({m_brix}°Bx) but purity rise is high. Sugar is bypassing. Schedule immediate screen replacement.")
        else:
            if drift_velocity > 0:
                runs_until_breach = (2.0 - m_rise) / drift_velocity
                if runs_until_breach < 6:
                    st.warning(f"⚠️ Predictive Alert\nScreen failure projected within {runs_until_breach:.1f} operational analyses.")
                else:
                    st.success(f"✅ Performance Stable\nEst. screen life remaining: {runs_until_breach:.1f} analyses.")
            else:
                st.success("✅ Performance Stable\nNo upward degradation drift detected.")
