import streamlit as st
from st_supabase_connection import SupabaseConnection
from st_login_form import login_form
import extra_streamlit_components as stx
import pandas as pd
import plotly.express as px
import time

st.set_page_config(page_title="Minutes Dashboard 2026", layout="wide")

cookie_manager = stx.CookieManager(key="myminutes_v6")
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
    period = st.selectbox("Select Period", [f"Period {i}" for i in range(1, 6)])
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
        except Exception:
            st.error(f"⚠️ Limit Reached: You already have an entry for {period}.")

# DELETE FUNCTIONALITY
st.sidebar.markdown("---")
st.sidebar.subheader("🗑️ Manage My Entries")
try:
    user_data = conn.table("member_activity").select("*").eq("display_name", st.session_state["username"]).execute()
    if user_data.data:
        periods_to_delete = sorted([row['period_name'] for row in user_data.data])
        target_period = st.sidebar.selectbox("Delete which entry?", periods_to_delete)
        if st.sidebar.button(f"Delete {target_period}"):
            conn.table("member_activity").delete().eq("display_name", st.session_state["username"]).eq("period_name", target_period).execute()
            st.sidebar.warning(f"{target_period} deleted.")
            time.sleep(1)
            st.rerun()
except:
    pass

if st.sidebar.button("Logout"):
    cookie_manager.delete("minutes_user_session")
    st.session_state["authenticated"] = False
    st.rerun()

# --- MAIN DASHBOARD ---
st.title("📊 Minutes Dashboard")

try:
    res = conn.table("member_activity").select("*").execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        total_pool = 600
        df['minutes'] = df['minutes'].astype(float)
        
        # 1. Calculate Individual Payoffs (based on all-time totals)
        # We group by name to get the total minutes squared per person
        totals = df.groupby('display_name')['minutes'].sum().reset_index()
        totals['sq_minutes'] = totals['minutes'] ** 2
        grand_total_sq = totals['sq_minutes'].sum()
        totals['payoff'] = (totals['sq_minutes'] / grand_total_sq) * total_pool if grand_total_sq > 0 else 0
        
        # 2. Top Visuals (Period Breakdown)
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(df, x="display_name", y="minutes", color="period_name", title="Minutes by Period"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(totals, values="payoff", names="display_name", title=f"Total Payoff Share of ${total_pool}"), use_container_width=True)
        
        # 3. GLOBAL LEADERBOARD SECTION
        st.markdown("---")
        st.header("🏆 Season Rankings (All Periods)")
        
        # Sort totals for the leaderboard
        leaderboard_df = totals[['display_name', 'minutes', 'payoff']].sort_values('minutes', ascending=False).reset_index(drop=True)
        leaderboard_df.index += 1  # Start rank at 1
        
        # Style the leaderboard
        st.table(leaderboard_df.style.format({"minutes": "{:.0f}", "payoff": "${:.2f}"}))

        # 4. Raw History
        with st.expander("See Detailed Entry History"):
            st.dataframe(df[['display_name', 'period_name', 'minutes']].sort_values(['display_name', 'period_name']), use_container_width=True)
            
    else:
        st.info("The leaderboard is currently empty. Start by logging Period 1!")
except Exception as e:
    st.error(f"Error loading dashboard: {e}")
