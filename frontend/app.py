import streamlit as st
import pandas as pd
from datetime import datetime, time, date, timedelta
import textwrap
import json
import os
from api_client import api_client

SESSION_FILE = os.path.expanduser("~/.after_work_agent_session.json")

def _save_session(user_id: int, is_onboarded: bool, token: str) -> None:
    with open(SESSION_FILE, "w") as f:
        json.dump({"user_id": user_id, "is_onboarded": is_onboarded, "token": token}, f)

def _load_session() -> dict | None:
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE) as f:
            return json.load(f)
    except Exception:
        return None

def _clear_session() -> None:
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

def render_html(html_str):
    cleaned = "\n".join(line.strip() for line in html_str.split("\n"))
    st.markdown(cleaned, unsafe_allow_html=True)

# Page Config
st.set_page_config(
    page_title="After Work Agent - Discover Activities & Communities",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

/* Apply modern font */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif;
}

/* Glassmorphism card */
.activity-card {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    transition: transform 0.2s, border-color 0.2s;
}

.activity-card:hover {
    transform: translateY(-2px);
    border-color: rgba(59, 130, 246, 0.5);
    background: rgba(255, 255, 255, 0.05);
}

.activity-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.activity-title {
    font-size: 1.25rem;
    font-weight: 600;
    color: #f8fafc;
}

/* Custom Badges */
.custom-badge {
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 9999px;
    margin-right: 6px;
    display: inline-block;
}

.badge-type { background-color: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }
.badge-location { background-color: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.badge-creator { background-color: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.badge-squad { background-color: rgba(139, 92, 246, 0.2); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); }
.badge-dept { background-color: rgba(236, 72, 153, 0.2); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.3); }
.badge-uncomfort { background-color: rgba(239, 68, 68, 0.25); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); animation: pulse 2s infinite; }
@keyframes pulse {
    0% { opacity: 0.8; }
    50% { opacity: 1; }
    100% { opacity: 0.8; }
}

/* Quick Action Suggestion buttons layout */
div[data-testid="stHorizontalBlock"] button {
    background-color: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: #e2e8f0 !important;
    border-radius: 8px !important;
}

div[data-testid="stHorizontalBlock"] button:hover {
    border-color: #3b82f6 !important;
    color: #3b82f6 !important;
}
</style>
""")

# App Title
st.title("🤖 After Work Agent")
st.markdown("*Your AI-powered assistant for discovering company activities, breaking routines, and connecting with peers.*")

# Initialize Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "interests_input" not in st.session_state:
    st.session_state.interests_input = ""
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

# --- AUTO-RESTORE SESSION ---
if "logged_in_user_id" not in st.session_state:
    saved = _load_session()
    if saved and saved.get("token"):
        res = api_client.me(saved["token"])
        if res.get("success"):
            st.session_state.logged_in_user_id = res["user_id"]
            st.session_state.is_onboarded = res["is_onboarded"]
            st.session_state.session_token = saved["token"]
        else:
            _clear_session()

# --- LOGIN / AUTHENTICATION GATE ---
if "logged_in_user_id" not in st.session_state:
    render_html("""
    <div style="text-align: center; margin-top: 50px; margin-bottom: 30px;">
        <h1 style="font-size: 2.8rem; font-weight: 700; color: #f8fafc; margin-bottom: 10px;">🤖 After Work Agent</h1>
        <p style="color: #94a3b8; font-size: 1.1rem;">Discover activities, connect with colleagues, and find your community</p>
    </div>
    """)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if "auth_mode" not in st.session_state:
            st.session_state.auth_mode = "login"

        tab_login, tab_register = st.tabs(["Sign In", "Register"])

        with tab_login:
            with st.form("login_details"):
                domain = st.text_input("Domain", placeholder="e.g. annt7", key="login_domain")
                password = st.text_input("Password", type="password", placeholder="e.g. abc", key="login_password")
                submit = st.form_submit_button("Sign In", use_container_width=True, type="primary")

                if submit:
                    if not domain or not password:
                        st.error("Please fill in both fields.")
                    else:
                        res = api_client.login(domain, password)
                        if res.get("success"):
                            st.session_state.logged_in_user_id = res["user_id"]
                            st.session_state.is_onboarded = res["is_onboarded"]
                            st.session_state.session_token = res.get("token")
                            _save_session(res["user_id"], res["is_onboarded"], res["token"])
                            st.success("Signed in!")
                            st.rerun()
                        else:
                            st.error(res.get("message", "Error signing in"))

        with tab_register:
            with st.form("register_details"):
                reg_domain = st.text_input("Choose a Domain", placeholder="e.g. johnd", key="reg_domain")
                reg_password = st.text_input("Choose a Password", type="password", key="reg_password")
                reg_password2 = st.text_input("Confirm Password", type="password", key="reg_password2")
                reg_submit = st.form_submit_button("Create Account", use_container_width=True, type="primary")

                if reg_submit:
                    if not reg_domain or not reg_password:
                        st.error("Please fill in all fields.")
                    elif reg_password != reg_password2:
                        st.error("Passwords do not match.")
                    else:
                        res = api_client.register(reg_domain, reg_password)
                        if res.get("success"):
                            st.session_state.logged_in_user_id = res["user_id"]
                            st.session_state.is_onboarded = res.get("is_onboarded", False)
                            st.session_state.session_token = res.get("token")
                            _save_session(res["user_id"], res.get("is_onboarded", False), res["token"])
                            st.success("Account created! Let's set up your profile.")
                            st.rerun()
                        else:
                            st.error(res.get("message", "Error creating account"))
    st.stop()

# --- ONBOARDING GATE ---
if not st.session_state.get("is_onboarded", True):
    render_html("""
    <div style="text-align: center; margin-top: 30px; margin-bottom: 30px;">
        <h1 style="font-size: 2.5rem; font-weight: 700; color: #f8fafc; margin-bottom: 10px;">👤 Complete Your Profile</h1>
        <p style="color: #94a3b8; font-size: 1.1rem;">Let's customize your discovery experience</p>
    </div>
    """)
    
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        with st.form("onboarding_form"):
            st.subheader("Workplace Details")
            full_name = st.text_input("Full Name", placeholder="e.g. Nguyen Thanh An")
            
            col_bu, col_grp = st.columns(2)
            with col_bu:
                company = st.selectbox("Business Unit", ["PY", "ZA", "Game", "GreenNode", "Other"])
            with col_grp:
                org_group = st.selectbox("Group", ["TEP", "BIZ", "OPS", "Other"])
                
            col_dept, col_sqd = st.columns(2)
            with col_dept:
                department = st.selectbox("Department", ["PCT", "PGE", "PCP", "DGS", "DLS", "MBS", "ZPO", "Other"])
            with col_sqd:
                squad = st.selectbox("Squad (Optional)", ["None", "Consumer Solutions", "Other"])
            
            st.markdown("---")
            st.subheader("Select Interests")
            st.caption("We will use these to match activities with you.")
            
            col_sports, col_learn, col_ent = st.columns(3)
            with col_sports:
                st.markdown("**Sports**")
                i_football = st.checkbox("Football")
                i_running = st.checkbox("Running")
                i_gym = st.checkbox("Gym")
                i_badminton = st.checkbox("Badminton")
            with col_learn:
                st.markdown("**Learning**")
                i_ai = st.checkbox("AI")
                i_product = st.checkbox("Product")
                i_english = st.checkbox("English")
            with col_ent:
                st.markdown("**Entertainment**")
                i_movies = st.checkbox("Movies")
                i_bg = st.checkbox("Board Games")
                i_coffee = st.checkbox("Coffee Chat")
                
            submit_onboard = st.form_submit_button("Save & Complete Onboarding", use_container_width=True, type="primary")
            if submit_onboard:
                if not full_name:
                    st.error("Please enter your Full Name.")
                else:
                    interests = []
                    if i_football: interests.append("football")
                    if i_running: interests.append("running")
                    if i_gym: interests.append("gym")
                    if i_badminton: interests.append("badminton")
                    if i_ai: interests.append("ai")
                    if i_product: interests.append("product")
                    if i_english: interests.append("english")
                    if i_movies: interests.append("movies")
                    if i_bg: interests.append("board games")
                    if i_coffee: interests.append("coffee")
                    
                    onboarding_data = {
                        "full_name": full_name,
                        "company": company,
                        "org_group": org_group,
                        "department": department,
                        "squad": squad if squad != "None" else None,
                        "interests": interests
                    }
                    res = api_client.onboard_user(st.session_state.logged_in_user_id, onboarding_data)
                    if res:
                        st.session_state.is_onboarded = True
                        token = st.session_state.get("session_token")
                        if token:
                            _save_session(st.session_state.logged_in_user_id, True, token)
                        st.success("Welcome aboard! Loading dashboard...")
                        st.rerun()
                    else:
                        st.error("Failed to complete onboarding. Check backend logs.")
    st.stop()

# --- MAIN APP (AUTHENTICATED) ---
current_user = api_client.get_user_profile(st.session_state.logged_in_user_id)
if not current_user:
    st.error("Active profile not found. Please log out and try again.")
    if st.button("🚪 Reset Session"):
        token = st.session_state.get("session_token")
        if token:
            api_client.logout(token)
        _clear_session()
        del st.session_state.logged_in_user_id
        if "is_onboarded" in st.session_state:
            del st.session_state.is_onboarded
        st.session_state.pop("session_token", None)
        st.rerun()
    st.stop()

# Sidebar: Profile & Switcher
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=800&q=80", use_column_width=True, caption="Connect After Work")
    st.header("👤 Active User Profile")
    
    st.markdown(f"### {current_user['full_name']} (@{current_user['domain']})")
    st.markdown(f"**Title**: {current_user['title']}")
    st.markdown(f"**Org Hierarchy**:")
    st.caption(f"🏢 Company: {current_user['company']}")
    st.caption(f"📁 Group: {current_user['org_group']}")
    st.caption(f"📂 Department: {current_user['department']}")
    if current_user.get("squad"):
        st.caption(f"👥 Squad: {current_user['squad']}")
    else:
        st.caption("👥 Squad: *None (Optional)*")
        
    st.markdown("**Core Interests**:")
    interests_html = ""
    for item in current_user["interests"]:
        interests_html += f'<span class="custom-badge badge-type">{item}</span>'
    render_html(interests_html)
    
    # Notifications Inbox
    st.markdown("---")
    notifications = api_client.get_notifications(current_user["id"])
    unread_count = len([n for n in notifications if not n["read"]])
    with st.expander(f"🔔 Notifications ({unread_count})" if unread_count > 0 else "🔔 Notifications", expanded=unread_count > 0):
        if not notifications:
            st.caption("No notifications yet.")
        else:
            for n in notifications:
                indicator = "🔵" if not n["read"] else "⚪"
                try:
                    dt = datetime.strptime(n["created_at"], "%Y-%m-%dT%H:%M:%S.%f")
                except ValueError:
                    try:
                        dt = datetime.strptime(n["created_at"], "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        dt = datetime.utcnow()
                time_str = dt.strftime("%b %d, %H:%M")
                
                st.markdown(f"**{indicator}** {n['message']} *({time_str})*")
                if not n["read"]:
                    if st.button("Mark read", key=f"read_{n['id']}", use_container_width=True):
                        api_client.mark_notification_read(n["id"])
                        st.rerun()
                    render_html("<hr style='border-color: rgba(255,255,255,0.05); margin: 5px 0;' />")
                
    st.markdown("---")
    # Log out
    st.markdown("---")
    with st.expander("🛠️ Dev Tools"):
        st.caption("Wipes all users, activities, and sessions.")
        if st.button("Reset All Data", use_container_width=True, type="secondary"):
            res = api_client.dev_reset()
            if res.get("success"):
                _clear_session()
                for key in ["logged_in_user_id", "is_onboarded", "session_token", "chat_history", "conversation_started"]:
                    st.session_state.pop(key, None)
                st.success("All data cleared. Redirecting to login...")
                st.rerun()
            else:
                st.error(res.get("message", "Reset failed"))

    if st.button("Log Out 🚪", use_container_width=True):
        token = st.session_state.get("session_token")
        if token:
            api_client.logout(token)
        _clear_session()
        del st.session_state.logged_in_user_id
        if "is_onboarded" in st.session_state:
            del st.session_state.is_onboarded
        st.session_state.pop("session_token", None)
        st.session_state.chat_history = []
        st.session_state.conversation_started = False
        st.rerun()

    st.markdown("---")
    # Sidebar Page Selection
    page = st.radio("Navigation", ["💬 Chat Assistant", "📅 Browse Activities", "➕ Create Activity", "👤 My Profile"])

# Daily Journal Feedback Prompt (Close the Feedback Loop)
if current_user:
    journal_data = api_client.get_pending_journal_prompt(current_user["id"])
    if journal_data.get("prompt"):
        target_date_str = journal_data.get("target_date")
        
        render_html(f"""
        <div style="background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
            <div style="font-size: 1.1rem; font-weight: 600; color: #60a5fa; margin-bottom: 6px;">📅 Evening Journal Prompt ({target_date_str})</div>
            <div style="font-size: 1.25rem; font-weight: 700; color: #f8fafc; margin-bottom: 12px;">What did you do yesterday evening?</div>
        </div>
        """)
        
        options = journal_data.get("options", [])
        
        # Create columns for buttons
        cols_count = len(options) + 2
        cols = st.columns(cols_count)
        
        col_idx = 0
        for opt in options:
            title = opt['title']
            # Shorten title if needed
            short_title = title[:20] + "..." if len(title) > 20 else title
            if cols[col_idx].button(f"Joined {short_title}", key=f"journal_opt_{opt.get('activity_id') or opt.get('gym_class_id')}", help=f"Confirm attendance to {title}"):
                api_client.resolve_journal_prompt(
                    user_id=current_user["id"],
                    status="resolved_activity",
                    activity_id=opt.get("activity_id"),
                    gym_class_id=opt.get("gym_class_id")
                )
                st.success("Thank you for sharing!")
                st.rerun()
            col_idx += 1
            
        if cols[col_idx].button("Rested / No Activity", key="journal_rested", help="I stayed at home / rested"):
            api_client.resolve_journal_prompt(
                user_id=current_user["id"],
                status="resolved_no_activity"
            )
            st.success("Recorded.")
            st.rerun()
        col_idx += 1
        
        if cols[col_idx].button("Skip", key="journal_skip", help="Ask me later"):
            api_client.resolve_journal_prompt(
                user_id=current_user["id"],
                status="skipped"
            )
            st.rerun()
            
        # Draw a line or smaller layout for custom activity selection
        other_col1, other_col2 = st.columns([3, 1])
        with other_col1:
            other_act = st.selectbox(
                "Or, did something else?",
                ["football", "badminton", "running", "gym", "board games", "coffee", "ai", "zumba", "yoga", "swimming", "other"],
                index=0,
                key="journal_other_activity_dropdown",
                label_visibility="collapsed"
            )
        with other_col2:
            if st.button("Submit Custom", key="journal_custom_submit", use_container_width=True):
                api_client.resolve_journal_prompt(
                    user_id=current_user["id"],
                    status="resolved_activity",
                    custom_activity=other_act
                )
                st.success(f"Recorded {other_act} activity.")
                st.rerun()
        render_html("<hr style='border-color: rgba(255,255,255,0.1); margin-top: 20px; margin-bottom: 20px;' />")

# --- PAGE 1: CHAT ASSISTANT ---
if page == "💬 Chat Assistant" and current_user:
    st.header("💬 Discover Tonight's Activities")

    # Conversation Starter: inject first message on fresh chat
    if not st.session_state.conversation_started and not st.session_state.chat_history:
        starter = api_client.get_conversation_starter(current_user["id"])
        st.session_state.chat_history.append({"role": "assistant", "content": starter["message"]})
        st.session_state.conversation_started = True

    # Showcase examples
    st.markdown("### Try these questions:")
    col1, col2, col3 = st.columns(3)
    
    suggested_query = None
    if col1.button("🙋 What should I do tonight?"):
        suggested_query = "What should I do tonight?"
    if col2.button("⚽ Post: Football at 6PM. Need 2 more players."):
        suggested_query = "Football at 6PM. Need 2 more players."
    if col3.button("🥱 I am bored of going to the gym every day."):
        suggested_query = "I am bored of going to the gym every day."
        
    # User Input
    user_query = st.chat_input("Ask about activities or announce a new one...")
    
    # If a quick action was clicked, override query
    if suggested_query:
        user_query = suggested_query

    # Display Chat History
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    # Send Chat Message
    if user_query:
        # Append user message
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)
            
        # Get AI Response
        with st.spinner("AI Agent is compiling recommendations..."):
            response = api_client.send_chat(current_user["id"], user_query)
            
        # Append AI response
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

# --- PAGE 2: BROWSE ACTIVITIES ---
elif page == "📅 Browse Activities" and current_user:
    st.header("📅 Available Activities")
    
    # Get user history and check routine trap status beforehand
    history = api_client.get_user_history(current_user["id"])
    joined_ids = [act["id"] for act in history] if history else []
    
    in_routine_trap = False
    dominant_type = None
    if history and len(history) >= 3:
        types = [act["activity_type"].lower() for act in history]
        from collections import Counter
        counts = Counter(types)
        most_common = counts.most_common(1)[0]
        dominant_ratio = most_common[1] / len(history)
        if dominant_ratio >= 0.7:
            in_routine_trap = True
            dominant_type = most_common[0]

    tab1, tab2 = st.tabs(["🔥 Dynamic Activities", "🏋️ Scheduled Gym Classes"])
    
    with tab1:
        st.subheader("User-Created Activities")
        activities = api_client.get_activities()
        
        if not activities:
            st.info("No upcoming activities found. Try creating one in the 'Create Activity' page!")
        else:
            # Map creators for badges
            users_list = api_client.get_users()
            all_users = {u["id"]: u for u in users_list}
            
            for act in activities:
                # Format start time & end time
                start_dt = datetime.fromisoformat(act["start_time"])
                if act.get("end_time"):
                    end_dt = datetime.fromisoformat(act["end_time"])
                    start_str = f"{start_dt.strftime('%A, %b %d from %H:%M')} to {end_dt.strftime('%H:%M')}"
                else:
                    start_str = start_dt.strftime("%A, %b %d at %H:%M")
                
                creator = all_users.get(act["created_by"], {"full_name": "Unknown", "squad": ""})
                creator_tag = f"{creator['full_name']} ({creator['squad'] if creator['squad'] else creator['department']})"
                
                spots_left = act["participant_limit"] - act["current_participants"]
                
                # Check if this activity is a routine-breaking match
                is_breaking = in_routine_trap and act["activity_type"].lower() != dominant_type
                breaking_badge = '<span class="custom-badge badge-uncomfort">⚡ Uncomfort Zone Match</span>' if is_breaking else ''
                
                emoji_map = {
                    "football": "⚽",
                    "badminton": "🏸",
                    "running": "🏃",
                    "gym": "🏋️",
                    "board games": "🎲",
                    "coffee": "☕",
                    "ai": "🤖",
                    "zumba": "💃",
                    "yoga": "🧘",
                    "swimming": "🏊"
                }
                act_emoji = emoji_map.get(act["activity_type"].lower(), "🔥")

                # HTML card representation
                status_label = "Active" if act.get("status") == "active" else "Full / Inactive"
                status_color_bg = "rgba(16, 185, 129, 0.2)" if act.get("status") == "active" else "rgba(239, 68, 68, 0.2)"
                status_color_text = "#34d399" if act.get("status") == "active" else "#f87171"
                status_color_border = "rgba(16, 185, 129, 0.3)" if act.get("status") == "active" else "rgba(239, 68, 68, 0.3)"
                status_badge = f'<span class="custom-badge" style="background-color: {status_color_bg}; color: {status_color_text}; border: 1px solid {status_color_border};">{status_label}</span>'
                
                guidelines_html = f'<p style="color:#94a3b8; font-size:13px; margin-top:5px; font-style:italic;">📋 Guidelines: {act["guidelines"]}</p>' if act.get("guidelines") else ""

                render_html(f"""
                <div class="activity-card">
                    <div class="activity-header">
                        <span class="activity-title">{act['title']}</span>
                        <div>{breaking_badge}{status_badge}<span class="custom-badge badge-location">📍 {act['location']}</span></div>
                    </div>
                    <p style="color:#cbd5e1; font-size:14px; margin-bottom:5px;">{act['description']}</p>{guidelines_html}
                    <div style="margin-top:10px;">
                        <span class="custom-badge badge-type">{act_emoji} {act['activity_type'].capitalize()}</span>
                        <span class="custom-badge badge-creator">👤 Host: {creator_tag}</span>
                        <span class="custom-badge badge-squad">📅 {start_str}</span>
                        <span class="custom-badge badge-dept">👥 Spots: {act['current_participants']}/{act['participant_limit']}</span>
                    </div>
                </div>
                """)
                
                # Buttons for Joining & Candidate matching
                col_join, col_cand = st.columns([2, 3])

                with col_join:
                    is_host = act["created_by"] == current_user["id"]
                    if is_host:
                        if st.button("Delete Activity 🗑️", key=f"delete_{act['id']}", use_container_width=True):
                            res = api_client.delete_activity(act["id"], current_user["id"])
                            if res.get("success"):
                                st.success("Activity deleted.")
                                st.rerun()
                            else:
                                st.error(res.get("message", "Delete failed."))
                    elif act["id"] in joined_ids:
                        st.button("Joined ✅", key=f"joined_{act['id']}", disabled=True, use_container_width=True)
                    elif spots_left <= 0 or act.get("status") == "inactive":
                        st.button("Full 🚫", key=f"full_{act['id']}", disabled=True, use_container_width=True)
                    else:
                        with st.expander("👉 Show Guidelines & Join", expanded=False):
                            st.markdown("**Preparation Guidelines:**")
                            st.info(act.get("guidelines") or "Arrive early and have fun!")
                            st.caption(f"Host: {creator_tag}")
                            st.caption(f"Location: {act['location']}")
                            st.caption(f"Spots remaining: {spots_left} of {act['participant_limit']}")
                            if st.button("Confirm Join", key=f"confirm_join_{act['id']}", type="primary", use_container_width=True):
                                res = api_client.join_activity(act["id"], current_user["id"])
                                if res["success"]:
                                    st.success("Joined successfully!")
                                    st.rerun()
                                else:
                                    st.error(res["message"])
                                
                with col_cand:
                    # SCENARIO 5: Missing players candidate recommendations
                    with st.expander("🔍 Match Candidate Players (Scenario 5)"):
                        candidates = api_client.get_activity_candidates(act["id"])
                        if not candidates:
                            st.caption("No matching candidate recommendations found.")
                        else:
                            st.caption(f"Recommending these matching colleagues who aren't registered yet:")
                            for cand in candidates[:3]: # Show top 3
                                reasons_str = ", ".join(cand["reasons"])
                                squad_label = f" ({cand['squad']})" if cand['squad'] else ""
                                st.markdown(f"- **{cand['full_name']}** from {cand['department']}{squad_label} | *Fit Score: {cand['fit_score']}*")
                                st.markdown(f"  *Reason*: {reasons_str}")
                                
    with tab2:
        st.subheader("Weekly Recurring Classes")
        st.markdown("*Configured by administrators. These automatically show up in recommendations.*")
        
        gym_classes = api_client.get_gym_classes()
        if not gym_classes:
            st.info("No recurring gym classes found.")
        else:
            for gc in gym_classes:
                time_range = f"{gc['start_time']} - {gc['end_time']}" if gc.get('end_time') else gc['start_time']
                
                # Check if this gym class is a routine-breaking match (if user is in routine trap, but NOT of dominant type gym)
                is_breaking = in_routine_trap and "gym" != dominant_type
                breaking_badge = '<span class="custom-badge badge-uncomfort">⚡ Uncomfort Zone Match</span>' if is_breaking else ''
                
                render_html(f"""
                <div class="activity-card">
                    <div class="activity-header">
                        <span class="activity-title">🧘 {gc['class_name']}</span>
                        <div>{breaking_badge}<span class="custom-badge badge-location">📍 {gc['location']}</span></div>
                    </div>
                    <p style="color:#cbd5e1; font-size:14px; margin-bottom:10px;">{gc['description']}</p>
                    <div>
                        <span class="custom-badge badge-type">⏰ Time: {time_range}</span>
                        <span class="custom-badge badge-squad">📅 Weekdays: {gc['weekday']}</span>
                        <span class="custom-badge badge-creator">👤 Instructor: {gc['instructor']}</span>
                        <span class="custom-badge badge-dept">Capacity: {gc['capacity']} seats</span>
                    </div>
                </div>
                """)

# --- PAGE 3: CREATE ACTIVITY ---
elif page == "➕ Create Activity" and current_user:
    st.header("➕ Create a Dynamic Activity")
    st.markdown("Announce a new after-work gathering. Your squad colleagues will be notified.")
    
    with st.form("create_activity_form"):
        title = st.text_input("Activity Title", placeholder="e.g. Wednesday Badminton Friendly")
        description = st.text_area("Description", placeholder="e.g. Playing double courts. Friendly matches, beginners welcome!")
        guidelines = st.text_area("Preparation Guidelines (Optional)", placeholder="e.g. Bring football shoes. Arrive 10 minutes early. Topic: AI Agents.")
        
        col1, col2 = st.columns(2)
        with col1:
            activity_type = st.selectbox("Activity Type", ["football", "badminton", "running", "gym", "board games", "coffee", "ai", "zumba", "yoga", "swimming"])
            location = st.text_input("Location", placeholder="e.g. Gym Room A, Pantry, Nearby Court")
        with col2:
            act_date = st.date_input("Date", date.today())
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                act_time = st.time_input("Start Time", time(18, 0))
            with col_t2:
                act_end_time = st.time_input("End Time", time(19, 0))
            
        participant_limit = st.number_input("Max Participants (including you)", min_value=2, max_value=100, value=10)
        
        submitted = st.form_submit_button("Publish Activity")
        if submitted:
            if not title or not location:
                st.error("Please fill in the Title and Location.")
            else:
                # Format start_time & end_time
                start_dt = datetime.combine(act_date, act_time)
                iso_time = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
                
                end_dt = datetime.combine(act_date, act_end_time)
                iso_end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
                
                res = api_client.create_activity(
                    title=title,
                    description=description,
                    activity_type=activity_type,
                    start_time=iso_time,
                    end_time=iso_end_time,
                    location=location,
                    participant_limit=participant_limit,
                    creator_id=current_user["id"],
                    guidelines=guidelines
                )
                
                if res:
                    st.success(f"🎉 Activity '{title}' created successfully!")
                    st.balloons()
                else:
                    st.error("Failed to create activity. Check server logs.")

# --- PAGE 4: MY PROFILE ---
elif page == "👤 My Profile" and current_user:
    st.header(f"👤 Employee Profile: {current_user['full_name']}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Your Workplace Details")
        st.markdown(f"**Domain/Username**: `{current_user['domain']}`")
        st.markdown(f"**Job Title**: {current_user['title']}")
        st.markdown(f"**Squad**: {current_user['squad'] if current_user['squad'] else 'N/A'}")
        st.markdown(f"**Department**: {current_user['department']}")
        st.markdown(f"**Group**: {current_user['org_group']}")
        st.markdown(f"**Company**: {current_user['company']}")
        
        st.subheader("AI Reflection Memories")
        st.markdown("*Extracted by the Reflection Agent based on your chat preferences.*")
        memories = api_client.get_user_memories(current_user["id"])
        
        if not memories:
            st.info("No AI memories recorded yet. Ask the chatbot to recommend activities and try expressing your feelings (e.g. 'I am bored of going to the gym').")
        else:
            for m in memories:
                st.markdown(f"💡 *\"{m['content']}\"* (Extracted on {datetime.strptime(m['created_at'], '%Y-%m-%dT%H:%M:%S.%f').strftime('%b %d, %Y')})")

        st.subheader("📝 Record Evening Experiences")
        st.markdown("*Share feedback on after-work activities you joined to close the learning loop.*")
        
        # Load user's joined activities (history)
        history = api_client.get_user_history(current_user["id"])
        # Load user's recorded experiences
        experiences = api_client.get_user_experiences(current_user["id"])
        
        # Map experience by activity_id for quick lookup
        exp_map = {e["activity_id"]: e for e in experiences if e.get("activity_id")}
        
        if not history:
            st.info("You haven't joined any activities yet. Join an activity in 'Browse Activities' first!")
        else:
            for act in history:
                act_id = act["id"]
                st.markdown(f"**{act['title']}** ({datetime.fromisoformat(act['start_time']).strftime('%b %d, %Y')})")
                
                if act_id in exp_map:
                    exp = exp_map[act_id]
                    # Display saved experience
                    energy_labels = {-2: "Draining 😫", -1: "Slightly Draining 🥱", 0: "Neutral 😐", 1: "Energizing 😊", 2: "Very Energizing ⚡"}
                    label = energy_labels.get(exp['energy_rating'], str(exp['energy_rating']))
                    st.caption(f"Energy: **{label}** | Connections: **{exp['connections_made']}**")
                    if exp.get('notes'):
                        st.markdown(f"💭 *\"{exp['notes']}\"*")
                    st.markdown("---")
                else:
                    # Form to record experience
                    with st.expander("Record your feedback"):
                        with st.form(key=f"exp_form_{act_id}"):
                            energy = st.select_slider(
                                "How did it make you feel?",
                                options=[-2, -1, 0, 1, 2],
                                value=0,
                                format_func=lambda x: {-2: "Draining 😫", -1: "Tiring 🥱", 0: "Neutral 😐", 1: "Energizing 😊", 2: "Very Energizing ⚡"}[x]
                            )
                            connections = st.number_input("New connections made:", min_value=0, max_value=50, value=0)
                            notes = st.text_area("What did you enjoy or learn?", placeholder="e.g. Great friendly match. Met three colleagues from Data Platform.")
                            
                            submit_exp = st.form_submit_button("Save Experience")
                            if submit_exp:
                                res = api_client.create_user_experience(
                                    user_id=current_user["id"],
                                    activity_id=act_id,
                                    energy_rating=energy,
                                    connections_made=connections,
                                    notes=notes,
                                    communities_enjoyed=[act["activity_type"]]
                                )
                                if res:
                                    st.success("Experience recorded! Learning updated.")
                                    st.rerun()
                                else:
                                    st.error("Failed to save experience.")
                
    with col2:
        st.subheader("Your Interests")
        st.markdown("*Select the categories you'd like to discover. This matches against upcoming events.*")
        
        # Standard interest options
        all_interests = ["football", "running", "gym", "yoga", "badminton", "board games", "coffee", "ai", "product", "startup", "english", "movies", "swimming"]
        
        # Prefill current interests
        user_interests = current_user["interests"]
        
        updated_interests = []
        for interest in all_interests:
            checked = st.checkbox(interest.capitalize(), value=(interest in user_interests), key=f"interest_{interest}")
            if checked:
                updated_interests.append(interest)
                
        if st.button("Update Interests", type="primary"):
            res = api_client.update_user_interests(current_user["id"], updated_interests)
            if res:
                st.success("🎉 Interests updated successfully!")
                st.rerun()
            else:
                st.error("Failed to update interests.")
