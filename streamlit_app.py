import streamlit as st
from st_supabase_connection import SupabaseConnection
from st_login_form import login_form
import extra_streamlit_components as stx
import pandas as pd
import plotly.express as px
import time

st.set_page_config(page_title="Minutes Dashboard 2026", layout="wide")

# --- 1. INITIALIZE ---
cookie_manager = stx.CookieManager(key="myminutes_guest_v1")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. AUTH CHECK (Runs silently) ---
def check_auth_status():
    # If already in session, stay in
    if st.session_state.get("authenticated"):
        return True
    
    # Try cookie backup
    time.sleep(0.5)
    cookie_val = cookie_manager.get(cookie="minutes_user_session")
    if cookie_val:
        st.session_state["authenticated"] = True
        st.session_state["username"] = cookie_val
        return True
    return False

is_logged_in = check_auth_status()

# --- 3. SIDEBAR: LOGIN & ACTIONS ---
st.sidebar.title("🔐 Member Portal")

if not is_logged_in:
    st.sidebar.info("Logged in as: **Guest** (View Only)")
    with st.sidebar.expander("Click here to Log In/Sign Up"):
        login_form(title="Member Access", allow_guest=False)
        if st.session_state.get("authenticated"):
            cookie_manager.set("minutes_user_session", st.session_state["username"], key="set_user")
            st.rerun()
else:
    user_name = st.session_state.get("username", "Member")
    st.sidebar.success(f"Logged in as: **{user_name}**")
    
    # MEMBER ONLY: ENTRY FORM
    with st.sidebar.form("entry_form", clear_on_submit=True):
        st.subheader("Submit Minutes")
        period = st.selectbox("Select Period", [f"Period {i}" for i in range(1, 6)])
        minutes = st.number_input("Minutes Worked", min_value=0, step=1)
        if st.form_submit_button("Submit Minutes"):
            try:
                conn.table("member_activity").insert({
                    "display_name": user_name,
                    "period_name": period,
                    "minutes": minutes
                }).execute()
                st.sidebar.success(f"{period} saved!")
                time.sleep(1)
                st.rerun()
            except Exception:
                st.sidebar.error(f"⚠️ Limit Reached for {period}.")

    # MEMBER ONLY: DELETE FUNCTION
    st.sidebar.markdown("---")
    try:
        user_data = conn.table("member_activity").select("*").eq("display_name", user_name).execute()
        if user_data.data:
            periods = sorted([row['period_name'] for row in user_data.data])
            target = st.sidebar.selectbox("Delete Entry", periods)
            if st.sidebar.button(f"Confirm Delete"):
                conn.table("member_activity").delete().eq("display_name", user_name).eq("period_name", target).execute()
                st.rerun()
    except:
        pass

    if st.sidebar.button("Logout"):
        cookie_manager.delete("minutes_user_session")
        st.session_state.clear()
        st.rerun()

# --- 4. MAIN DASHBOARD (Visible to Everyone) ---
st.title("📊 Minutes Dashboard")
st.markdown("#### $600 Total Pot • June 2026 Competition")

# [The Expanders and instructions stay here...]

try:
    res = conn.table("member_activity").select("*").execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        total_pool = 600
        df['minutes'] = df['minutes'].astype(float)
        
        # 1. Calculate Totals and Payoffs
        totals = df.groupby('display_name')['minutes'].sum().reset_index()
        totals['sq_minutes'] = totals['minutes'] ** 2
        total_sq = totals['sq_minutes'].sum()
        totals['payoff'] = (totals['sq_minutes'] / total_sq) * total_pool if total_sq > 0 else 0
        
        # 2. NEW: Create the "Period Tracker" (The 5 Circles)
        # This creates a map of who has entered what
        entry_map = df.pivot_table(index='display_name', columns='period_name', values='minutes', aggfunc='count').fillna(0)
        
        def get_streak_icons(user):
            icons = []
            for i in range(1, 6):
                p_name = f"Period {i}"
                if p_name in entry_map.columns and entry_map.loc[user, p_name] > 0:
                    icons.append("✅") # Entry exists
                else:
                    icons.append("⚪") # Missing entry
            return " ".join(icons)

        totals['Status'] = totals['display_name'].apply(get_streak_icons)

        # Charts
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(df, x="display_name", y="minutes", color="period_name", title="Minutes by Period"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(totals, values="payoff", names="display_name", title="Estimated Payoff Share"), use_container_width=True)
        
        # 3. UPDATED LEADERBOARD: Now with Status Icons
        st.header("🏆 Season Rankings")
        # Reordering columns to put Status next to the name
        rank_df = totals[['display_name', 'Status', 'minutes', 'payoff']].sort_values('minutes', ascending=False).reset_index(drop=True)
        rank_df.index += 1
        
        # Rename columns for a cleaner look
        rank_df.columns = ["Member", "Activity Tracker (P1-P5)", "Total Minutes", "Est. Payoff"]
        
        st.table(rank_df.style.format({"Est. Payoff": "${:.2f}", "Total Minutes": "{:.0f}"}))

        with st.expander("View Specific Entry History"):
            st.dataframe(df[['display_name', 'period_name', 'minutes']].sort_values(['period_name', 'display_name']), use_container_width=True)
    
