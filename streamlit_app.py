import streamlit as st
from st_supabase_connection import SupabaseConnection
from st_login_form import login_form
import extra_streamlit_components as stx
import pandas as pd
import plotly.express as px
import time

st.set_page_config(page_title="Minutes Dashboard 2026", layout="wide")

# --- 1. INITIALIZE COMPONENTS ---
cookie_manager = stx.CookieManager(key="myminutes_v12_final")
conn = st.connection("supabase", type=SupabaseConnection)

# --- 2. PERSISTENT AUTH LOGIC ---
def run_auth():
    if st.session_state.get("authenticated"):
        return True

    time.sleep(0.7)
    cookie_val = cookie_manager.get(cookie="minutes_user_session")
    
    if cookie_val:
        st.session_state["authenticated"] = True
        st.session_state["username"] = cookie_val
        return True

    login_form(title="Member Access", allow_guest=False)
    
    if st.session_state.get("authenticated"):
        cookie_manager.set(
            "minutes_user_session", 
            st.session_state["username"], 
            key="save_cookie_v12",
            expires_at=time.time() + (30 * 24 * 60 * 60)
        )
        st.rerun()
    return False

if not run_auth():
    st.stop()

# --- 3. SIDEBAR: ENTRY FORM ---
user_name = st.session_state.get("username", "Member")
st.sidebar.header(f"👋 Welcome, {user_name}!")

with st.sidebar.form("entry_form", clear_on_submit=True):
    period = st.selectbox("Select Period", [f"Period {i}" for i in range(1, 6)])
    minutes = st.number_input("Minutes Worked", min_value=0, step=1)
    if st.form_submit_button("Submit Minutes"):
        try:
            conn.table("member_activity").insert({
                "display_name": user_name,
                "period_name": period,
                "minutes": minutes
            }).execute()
            st.success(f"{period} saved!")
            time.sleep(1)
            st.rerun()
        except Exception:
            st.error(f"⚠️ Limit Reached: You already have an entry for {period}.")

# --- 4. SIDEBAR: DELETE FUNCTION ---
st.sidebar.markdown("---")
st.sidebar.subheader("🗑️ Manage My Entries")
try:
    user_data = conn.table("member_activity").select("*").eq("display_name", user_name).execute()
    if user_data.data:
        periods_to_delete = sorted([row['period_name'] for row in user_data.data])
        target = st.sidebar.selectbox("Delete which one?", periods_to_delete)
        if st.sidebar.button(f"Confirm Delete {target}"):
            conn.table("member_activity").delete().eq("display_name", user_name).eq("period_name", target).execute()
            st.sidebar.warning(f"Deleted {target}")
            time.sleep(1)
            st.rerun()
except:
    pass

if st.sidebar.button("Logout"):
    cookie_manager.delete("minutes_user_session")
    st.session_state.clear()
    st.rerun()

# --- 5. MAIN DASHBOARD ---
st.title("📊 Minutes Dashboard")

try:
    res = conn.table("member_activity").select("*").execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        total_pool = 600
        df['minutes'] = df['minutes'].astype(float)
        
        # Calculation Logic
        totals = df.groupby('display_name')['minutes'].sum().reset_index()
        totals['sq_minutes'] = totals['minutes'] ** 2
        total_sq = totals['sq_minutes'].sum()
        totals['payoff'] = (totals['sq_minutes'] / total_sq) * total_pool if total_sq > 0 else 0
        
        # Charts
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(df, x="display_name", y="minutes", color="period_name", title="Minutes Breakdown"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(totals, values="payoff", names="display_name", title=f"Payoff Share of ${total_pool}"), use_container_width=True)
        
        # LEADERBOARD
        st.header("🏆 Season Rankings")
        rank_df = totals[['display_name', 'minutes', 'payoff']].sort_values('minutes', ascending=False).reset_index(drop=True)
        rank_df.index += 1
        st.table(rank_df.style.format({"payoff": "${:.2f}", "minutes": "{:.0f}"}))

        # SPECIFIC ENTRIES (Restored)
        st.markdown("---")
        st.subheader("📝 All Specific Entries")
        st.dataframe(df[['display_name', 'period_name', 'minutes']].sort_values(['period_name', 'display_name']), use_container_width=True)

    else:
        st.info("No entries yet. Log your minutes in the sidebar!")
except Exception as e:
    st.error(f"Error: {e}")
