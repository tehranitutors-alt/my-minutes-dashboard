import streamlit as st
from st_supabase_connection import SupabaseConnection
from st_login_form import login_form
import extra_streamlit_components as stx
import pandas as pd
import plotly.express as px
import time

st.set_page_config(page_title="Minutes Dashboard 2026", layout="wide")

cookie_manager = stx.CookieManager(key="myminutes_v4")
conn = st.connection("supabase", type=SupabaseConnection)

def run_auth():
    time.sleep(0.5)
    saved_user = cookie_manager.get(cookie="minutes_user_session")
    if saved_user and not st.session_state.get("authenticated"):
        st.session_state["authenticated"] = True
        st.session_state["username"] = saved_user
        return True
    if not st.session_state.get("authenticated"):
        login_form(title="Member Access", allow_guest=False)
        if st.session_state.get("authenticated"):
            cookie_manager.set("minutes_user_session", st.session_state["username"], key="set_cookie")
            st.rerun()
        return False
    return True

if not run_auth():
    st.stop()

# --- SIDEBAR: ENTRY & DELETE ---
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
            st.success(f"Success! {period} logged.")
            st.rerun()
        except Exception as e:
            st.error("⚠️ Limit Reached: You already have an entry for this period. Delete it below to make a new one.")

# DELETE FUNCTIONALITY
st.sidebar.markdown("---")
st.sidebar.subheader("🗑️ Manage My Entries")
try:
    user_data = conn.table("member_activity").select("*").eq("display_name", st.session_state["username"]).execute()
    if user_data.data:
        periods_to_delete = [row['period_name'] for row in user_data.data]
        target_period = st.sidebar.selectbox("Delete which entry?", periods_to_delete)
        if st.sidebar.button(f"Delete {target_period}"):
            conn.table("member_activity").delete().eq("display_name", st.session_state["username"]).eq("period_name", target_period).execute()
            st.sidebar.warning(f"{target_period} deleted.")
            time.sleep(1)
            st.rerun()
    else:
        st.sidebar.info("No entries to delete yet.")
except:
    pass

if st.sidebar.button("Logout"):
    cookie_manager.delete("minutes_user_session")
    st.session_state["authenticated"] = False
    st.rerun()

# --- MAIN DASHBOARD ---
st.title("📊 Minutes Leaderboard")

try:
    res = conn.table("member_activity").select("*").execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        # UPDATED POT: $600
        total_pool = 600
        df['sq_minutes'] = df['minutes'].astype(float) ** 2
        total_sq = df['sq_minutes'].sum()
        df['payoff'] = (df['sq_minutes'] / total_sq) * total_pool if total_sq > 0 else 0

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(df, x="display_name", y="minutes", color="period_name", title="Total Minutes"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df, values="payoff", names="display_name", title=f"Payoff Share of ${total_pool}"), use_container_width=True)
        
        st.dataframe(df[['display_name', 'period_name', 'minutes', 'payoff']].sort_values(['display_name', 'period_name']), use_container_width=True)
    else:
        st.info("The leaderboard is currently empty.")
except Exception as e:
    st.error(f"Error: {e}")
