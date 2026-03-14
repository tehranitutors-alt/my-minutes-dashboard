import streamlit as st
import pandas as pd
import plotly.express as px
from st_login_form import login_form
from st_supabase_connection import SupabaseConnection

# --- APP CONFIG ---
st.set_page_config(page_title="Minutes Tracker", layout="wide")

# --- AUTHENTICATION ---
# This creates the login/signup UI and handles the session
client = login_form()

if not st.session_state.get("authenticated"):
    st.info("Please log in to enter your minutes.")
    st.stop()

# --- DATABASE CONNECTION ---
conn = st.connection("supabase", type=SupabaseConnection)

# --- SIDEBAR: DATA ENTRY ---
with st.sidebar:
    st.header(f"Welcome, {st.session_state['username']}!")
    st.subheader("Add New Entry")
    
    with st.form("entry_form", clear_on_submit=True):
        # We use a select box for periods based on your Excel file
        period = st.selectbox("Period", ["Week 1", "Week 2", "Week 3", "Week 4", "29th + 30th"])
        minutes = st.number_input("Minutes Worked", min_value=0, step=5)
        
        if st.form_submit_button("Submit"):
            # Insert data linked to the logged-in user
            conn.table("member_activity").insert({
                "display_name": st.session_state["username"],
                "period_name": period,
                "minutes": minutes
            }).execute()
            st.success("Entry Saved!")
            st.rerun()

# --- MAIN DASHBOARD ---
st.title("🏆 Activity Leaderboard")

# Fetch all data from Supabase
response = conn.table("member_activity").select("*").execute()
df = pd.DataFrame(response.data)

if not df.empty:
    # 1. Group by Name to calculate the "Excel Style" totals
    leaderboard = df.groupby("display_name")["minutes"].sum().reset_index()
    leaderboard.columns = ["Name", "Total Minutes"]
    
    # 2. Add the "Minutes^2" column (per your Excel file)
    leaderboard["Minutes^2"] = leaderboard["Total Minutes"] ** 2
    
    # 3. Calculate Payoff (Example Logic: proportional to Minutes^2)
    total_squared = leaderboard["Minutes^2"].sum()
    total_pool = 650  # Change this to your actual entry fee total
    leaderboard["Payoff"] = (leaderboard["Minutes^2"] / total_squared) * total_pool
    
    # --- VISUALS ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Total Minutes by Member")
        fig = px.bar(leaderboard, x="Name", y="Total Minutes", color="Name", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("Statistics Table")
        # Format for currency and clean numbers
        st.dataframe(leaderboard.style.format({
            "Payoff": "${:,.2f}",
            "Minutes^2": "{:,.0f}"
        }))

    # History Section
    st.divider()
    st.subheader("Recent Activity Log")
    st.dataframe(df.sort_values("created_at", ascending=False))

else:
    st.write("No data found. Start by adding your minutes in the sidebar!")
