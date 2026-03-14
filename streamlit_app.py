import streamlit as st
from st_supabase_connection import SupabaseConnection
from st_login_form import login_form
import extra_streamlit_components as stx
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Minutes Dashboard 2026", layout="wide")

# --- 1. SESSION & COOKIE MANAGEMENT ---
# This keeps you logged in even after refreshing
cookie_manager = stx.CookieManager()

def handle_auth():
    # Try to get username from cookie
    saved_user = cookie_manager.get(cookie="minutes_user_session")
    
    if saved_user and not st.session_state.get("authenticated"):
        st.session_state["authenticated"] = True
        st.session_state["username"] = saved_user

    if not st.session_state.get("authenticated"):
        client = login_form(title="Member Access", allow_guest=False)
        if st.session_state.get("authenticated"):
            # Save cookie for 30 days
            cookie_manager.set("minutes_user_session", st.session_state["username"], key="set_user_cookie")
            st.rerun()
        st.stop()
    return True

# --- 2. DATABASE CONNECTION ---
conn = st.connection("supabase", type=SupabaseConnection)

# Run Auth
handle_auth()

# --- 3. SIDEBAR: ENTRY FORM ---
st.sidebar.header(f"👋 Welcome, {st.session_state['username']}!")

with st.sidebar.form("entry_form", clear_on_submit=True):
    period = st.selectbox("Select Period", [f"Week {i}" for i in range(1, 13)])
    minutes = st.number_input("Minutes Worked", min_value=0, step=1)
    submit = st.form_submit_button("Submit Minutes")

    if submit:
        try:
            # We use 'period_name' to match our SQL fix
            conn.table("member_activity").insert({
                "display_name": st.session_state["username"],
                "period_name": period,
                "minutes": minutes
            }).execute()
            st.success("Entry Saved!")
            st.rerun()
        except Exception as e:
            st.error(f"Save Failed: {e}")

if st.sidebar.button("Logout"):
    cookie_manager.delete("minutes_user_session")
    st.session_state["authenticated"] = False
    st.rerun()

# --- 4. MAIN DASHBOARD: VISUALS ---
st.title("📊 Minutes Leaderboard & Payoff")

try:
    # Fetch data
    res = conn.table("member_activity").select("*").execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        # --- EXCEL MATH LOGIC ---
        total_pool = 650
        df['sq_minutes'] = df['minutes'] ** 2
        group_total_sq = df['sq_minutes'].sum()
        
        if group_total_sq > 0:
            df['payoff'] = (df['sq_minutes'] / group_total_sq) * total_pool
        else:
            df['payoff'] = 0

        # Visuals
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Total Minutes by Member")
            fig_min = px.bar(df, x="display_name", y="minutes", color="period_name", barmark="group")
            st.plotly_chart(fig_min, use_container_width=True)

        with col2:
            st.subheader("Estimated Payoff Share")
            fig_pay = px.pie(df, values="payoff", names="display_name", hole=0.3)
            st.plotly_chart(fig_pay, use_container_width=True)
            
        st.subheader("Raw Data")
        st.dataframe(df[['display_name', 'period_name', 'minutes', 'payoff']].sort_values('minutes', ascending=False), use_container_width=True)
    else:
        st.info("No data yet. Use the sidebar to submit your first entry!")

except Exception as e:
    st.warning("Connect to database to see chart...")
