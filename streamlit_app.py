import streamlit as st
from st_supabase_connection import SupabaseConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Minutes Dashboard 2026", layout="wide")

# --- 1. CONFIGURATION & INITIALIZE ---
ADMIN_PASSWORD = "your_secret_password"  # 👈 Set your chosen admin password here
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. SIDEBAR: MASTER CONTROLS ---
st.sidebar.title("🔐 Member Portal")

input_password = st.sidebar.text_input("Enter Master Password", type="password")

if input_password != ADMIN_PASSWORD:
    st.sidebar.info("Logged in as: **Guest** (View Only)")
    if input_password:
        st.sidebar.error("❌ Incorrect Password")
else:
    st.sidebar.success("🔓 Access Granted (Master Account)")
    
    # MASTER ENTRY FORM
    with st.sidebar.form("entry_form", clear_on_submit=True):
        st.subheader("Submit Minutes")
        
        target_user = st.text_input("Member Name (Case Sensitive)").strip()
        period = st.selectbox("Select Period", [f"Period {i}" for i in range(1, 6)])
        minutes = st.number_input("Intensity Minutes", min_value=0, step=1)
        
        if st.form_submit_button("Submit Minutes"):
            if not target_user:
                st.sidebar.error("⚠️ Please enter a member name.")
            else:
                try:
                    conn.table("member_activity").insert({
                        "display_name": target_user,
                        "period_name": period,
                        "minutes": minutes
                    }).execute()
                    st.sidebar.success(f"{period} saved for {target_user}!")
                    st.rerun()
                except Exception:
                    st.sidebar.error(f"⚠️ Limit Reached for {period}.")

    # MASTER DELETE FUNCTION
    st.sidebar.markdown("---")
    try:
        all_data = conn.table("member_activity").select("*").execute()
        if all_data.data:
            df_del = pd.DataFrame(all_data.data)
            df_del['label'] = df_del['display_name'] + " (" + df_del['period_name'] + ")"
            
            target = st.sidebar.selectbox("Delete Entry", df_del['label'].tolist())
            target_row = df_del[df_del['label'] == target].iloc[0]
            
            if st.sidebar.button("Confirm Delete"):
                conn.table("member_activity").delete()\
                    .eq("display_name", target_row['display_name'])\
                    .eq("period_name", target_row['period_name']).execute()
                st.rerun()
    except:
        pass

# --- 3. MAIN DASHBOARD ---
st.title("June Hurty Intensity Minutes Dashboard 💪📊")
st.markdown("#### $100 AUD entry per person = $500 Total Pot • Periods 1-5 • June 2026")

with st.expander("ℹ️ View Dashboard Instructions & June Schedule"):
    st.write("""
    
    **June Schedule:**
    - **Period 1:** June 1–7 
    - **Period 2:** June 8–14 
    - **Period 3:** June 15–21 
    - **Period 4:** June 22–28 
    - **Period 5:** June 29–30
    
    **What are Intensity Minutes?**
    Garmin tracks your heart rate. Moderate activity earns 1 min, but **Vigorous** activity earns **2 mins**. 
    The payoff math uses these totals squared ($min^2$), rewarding consistent high-intensity effort!
    """)

try:
    res = conn.table("member_activity").select("*").execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        total_pool = 500  # 👈 Kept exactly at $500 as you requested
        df['minutes'] = df['minutes'].astype(float)
        
        # Math
        totals = df.groupby('display_name')['minutes'].sum().reset_index()
        totals['sq_minutes'] = totals['minutes'] ** 2
        total_sq = totals['sq_minutes'].sum()
        totals['payoff'] = (totals['sq_minutes'] / total_sq) * total_pool if total_sq > 0 else 0
        
        # Activity Tracker Grid Mapping (The 5 Weekly Circles)
        pivot = df.pivot_table(index='display_name', columns='period_name', values='minutes', aggfunc='count').fillna(0)
        
        def make_streak(name):
            icons = []
            for i in range(1, 6):
                p = f"Period {i}"
                if p in pivot.columns and pivot.loc[name, p] > 0:
                    icons.append("✅")
                else:
                    icons.append("⚪")
            return " ".join(icons)
        
        totals['Activity Tracker'] = totals['display_name'].apply(make_streak)
        
        # Charts
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(df, x="display_name", y="minutes", color="period_name", title="Entry Breakdown"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(totals, values="payoff", names="display_name", title=f"Payoff Share (${total_pool})"), use_container_width=True)
        
        # Rankings
        st.header("🏆 Season Rankings")
        rank_df = totals[['display_name', 'Activity Tracker', 'minutes', 'payoff']].sort_values('minutes', ascending=False).reset_index(drop=True)
        rank_df.index += 1
        rank_df.columns = ["Member", "Weekly Status (P1-P5)", "Total Minutes", "Est. Payoff"]
        
        st.table(rank_df.style.format({"Est. Payoff": "${:.2f}", "Total Minutes": "{:.0f}"}))

        # Entries
        with st.expander("View All Specific Entries"):
            st.dataframe(df[['display_name', 'period_name', 'minutes']].sort_values(['period_name', 'display_name']), use_container_width=True)
    else:
        st.info("The dashboard is currently empty. Members can log in via the sidebar to contribute.")

except Exception as e:
    st.error(f"Error: {e}")
