import streamlit as st
from st_supabase_connection import SupabaseConnection
from st_login_form import login_form
import extra_streamlit_components as stx
import pandas as pd
import plotly.express as px
import time

st.set_page_config(page_title="Minutes Dashboard 2026", layout="wide")

# --- 1. COOKIE & SESSION INITIALIZATION ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# This component needs a unique key to stay stable
cookie_manager = stx.CookieManager(key="myminutes_auth_manager")

# --- 2. DATABASE CONNECTION ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- 3. PERSISTENT LOGIN LOGIC ---
def check_auth():
    # Wait a split second for cookies to load from browser
    time.sleep(0.5) 
    saved_user = cookie_manager.get(cookie="minutes_user_session")
    
    if saved_user and not st.session_state["authenticated"]:
        st.session_state["authenticated"] = True
        st.session_state["username"] = saved_user
        return True
    
    if not st.session_state["authenticated"]:
        # Only show the form if we aren't already authed via cookie
        client = login_form(title="Member Access", allow_guest=False)
        if st.session_state["authenticated"]:
            cookie_manager.set("minutes_user_session", st.session_state["username"], key="save_user_on_login")
            st.rerun()
        return False
    return True

# Run the auth check
is_logged_in = check_auth()

if not is_logged_in:
    st.stop()

# --- 4. DASHBOARD CODE (Only runs if logged in) ---
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

# Load Data inside a try/except to prevent the yellow warning box
try:
    res = conn.table("member_activity").select("*").execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        # Excel Math Logic
        total_pool = 650
        df['sq_minutes'] = df['minutes'].astype(float) ** 2
        group_total_sq = df['sq_minutes'].sum()
        df['payoff'] = (df['sq_minutes'] / group_total_sq) * total_pool if group_total_sq > 0 else 0

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(df, x="display_name", y="minutes", color="period_name"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df, values="payoff", names="display_name", hole=0.3), use_container_width=True)
        
        st.dataframe(df[['display_name', 'period_name', 'minutes', 'payoff']], use_container_width=True)
    else:
        st.info("No entries found yet!")
except Exception as e:
    st.error(f"Database error: {e}")
