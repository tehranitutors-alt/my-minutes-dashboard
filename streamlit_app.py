import streamlit as st
from st_supabase_connection import SupabaseConnection
from st_login_form import login_form
import extra_streamlit_components as stx
import pandas as pd
import plotly.express as px
import time

st.set_page_config(page_title="Minutes Dashboard 2026", layout="wide")

# --- 1. INITIALIZE COOKIE MANAGER ---
# We do this first so it has time to "talk" to the browser
cookie_manager = stx.CookieManager(key="myminutes_v3")

# --- 2. DATABASE CONNECTION ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- 3. AUTHENTICATION LOGIC ---
def run_auth():
    # Give the cookie manager a moment to load
    time.sleep(0.5)
    saved_user = cookie_manager.get(cookie="minutes_user_session")
    
    # If cookie found, log them in automatically
    if saved_user and not st.session_state.get("authenticated"):
        st.session_state["authenticated"] = True
        st.session_state["username"] = saved_user
        return True

    # If not logged in, show the form
    if not st.session_state.get("authenticated"):
        # This function handles the UI for Login/Sign Up
        client = login_form(title="Member Access", allow_guest=False)
        
        if st.session_state.get("authenticated"):
            # If they just clicked login, save the cookie for next time
            cookie_manager.set("minutes_user_session", st.session_state["username"], key="set_cookie_final")
            st.rerun()
        return False
    return True

# STOP the app here if not authenticated
if not run_auth():
    st.stop()

# --- 4. DASHBOARD (Only visible if username exists) ---
# This is where your crash was happening—now it's protected by the 'if' above
st.sidebar.header(f"👋 Welcome, {st.session_state['username']}!")

with st.sidebar.form("entry_form", clear_on_submit=True):
    period = st.selectbox("Select Period", [f"Week {i}" for i in range(1, 13)])
    minutes = st.number_input("Minutes Worked", min_value=0, step=1)
    submit = st.form_submit_button("Submit Minutes")

    if submit:
        try:
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

st.title("📊 Minutes Leaderboard")

# Load and process data
try:
    res = conn.table("member_activity").select("*").execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        total_pool = 650
        df['sq_minutes'] = df['minutes'].astype(float) ** 2
        total_sq = df['sq_minutes'].sum()
        df['payoff'] = (df['sq_minutes'] / total_sq) * total_pool if total_sq > 0 else 0

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(df, x="display_name", y="minutes", color="period_name"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df, values="payoff", names="display_name"), use_container_width=True)
        
        st.dataframe(df[['display_name', 'period_name', 'minutes', 'payoff']], use_container_width=True)
    else:
        st.info("No entries found yet!")
except Exception as e:
    st.error(f"Error loading data: {e}")
