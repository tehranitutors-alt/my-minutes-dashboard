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
st.title("June Hurty Intensity Minutes Dashboard 💪📊 ")
st.markdown("#### 100 AUD/ entry per person = $600 Total Pot • Periods 1-5 • June 2026")

with st.expander("ℹ️ View Dashboard Instructions & June Schedule"):
    st.write("""
    **How to Log:** Members log in via the sidebar to submit Garmin Intensity Minutes.
    
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
        total_pool = 600
        df['minutes'] = df['minutes'].astype(float)
        
        # Math
        totals = df.groupby('display_name')['minutes'].sum().reset_index()
        totals['sq_minutes'] = totals['minutes'] ** 2
        total_sq = totals['sq_minutes'].sum()
        totals['payoff'] = (totals['sq_minutes'] / total_sq) * total_pool if total_sq > 0 else 0
        
        # Charts
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(df, x="display_name", y="minutes", color="period_name", title="Entry Breakdown"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(totals, values="payoff", names="display_name", title=f"Payoff Share (${total_pool})"), use_container_width=True)
        
        # Rankings
        st.header("🏆 Season Rankings")
        rank_df = totals[['display_name', 'minutes', 'payoff']].sort_values('minutes', ascending=False).reset_index(drop=True)
        rank_df.index += 1
        st.table(rank_df.style.format({"payoff": "${:.2f}", "minutes": "{:.0f}"}))

        # Entries
        with st.expander("View All Specific Entries"):
            st.dataframe(df[['display_name', 'period_name', 'minutes']].sort_values(['period_name', 'display_name']), use_container_width=True)
    else:
        st.info("The dashboard is currently empty. Members can log in via the sidebar to contribute.")

except Exception as e:
    st.error(f"Error: {e}")
    
