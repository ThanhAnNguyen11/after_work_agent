import streamlit as st
import pandas as pd
from datetime import datetime, time, date, timedelta
from api_client import api_client

# Page Config
st.set_page_config(
    page_title="After Work Agent - Discover Activities & Communities",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
st.markdown("""
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
""", unsafe_allow_html=True)

# App Title
st.title("🤖 After Work Agent")
st.markdown("*Your AI-powered assistant for discovering company activities, breaking routines, and connecting with peers.*")

# Initialize Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_user_index" not in st.session_state:
    st.session_state.current_user_index = 0
if "interests_input" not in st.session_state:
    st.session_state.interests_input = ""

# Sidebar: Profile & Switcher
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=800&q=80", use_column_width=True, caption="Connect After Work")
    st.header("👤 Active User Profile")
    
    # Load users from backend
    users = api_client.get_users()
    if users:
        user_names = [f"{u['full_name']} (@{u['domain']})" for u in users]
        
        # Keep dropdown in sync
        def on_user_change():
            # Clear chat history when switching users
            st.session_state.chat_history = []
            
        selected_user_idx = st.selectbox(
            "Switch User Profile:", 
            range(len(users)), 
            format_func=lambda x: user_names[x],
            index=st.session_state.current_user_index,
            key="current_user_index",
            on_change=on_user_change
        )
        
        current_user = users[selected_user_idx]
        
        # Display profile details
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
        st.markdown(interests_html, unsafe_allow_html=True)
    else:
        st.error("Could not fetch users. Please ensure the backend is running.")
        current_user = None

    st.markdown("---")
    # Sidebar Page Selection
    page = st.radio("Navigation", ["💬 Chat Assistant", "📅 Browse Activities", "➕ Create Activity", "👤 My Profile"])

# --- PAGE 1: CHAT ASSISTANT ---
if page == "💬 Chat Assistant" and current_user:
    st.header("💬 Discover Tonight's Activities")
    
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
            all_users = {u["id"]: u for u in users}
            
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
                
                # HTML card representation
                st.markdown(f"""
                <div class="activity-card">
                    <div class="activity-header">
                        <span class="activity-title">{act['title']}</span>
                        <div>
                            {breaking_badge}
                            <span class="custom-badge badge-location">📍 {act['location']}</span>
                        </div>
                    </div>
                    <p style="color:#cbd5e1; font-size:14px; margin-bottom:10px;">{act['description']}</p>
                    <div>
                        <span class="custom-badge badge-type">⚽ {act['activity_type'].capitalize()}</span>
                        <span class="custom-badge badge-creator">👤 Host: {creator_tag}</span>
                        <span class="custom-badge badge-squad">📅 {start_str}</span>
                        <span class="custom-badge badge-dept">👥 Spots: {act['current_participants']}/{act['participant_limit']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Buttons for Joining & Candidate matching
                col_join, col_cand = st.columns([1, 4])
                
                with col_join:
                    if act["id"] in joined_ids:
                        st.button("Joined ✅", key=f"joined_{act['id']}", disabled=True)
                    elif spots_left <= 0:
                        st.button("Full 🚫", key=f"full_{act['id']}", disabled=True)
                    else:
                        if st.button("Join Activity", key=f"join_{act['id']}", type="primary"):
                            res = api_client.join_activity(act["id"], current_user["id"])
                            if res["success"]:
                                st.success("Joined!")
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
                
                st.markdown(f"""
                <div class="activity-card">
                    <div class="activity-header">
                        <span class="activity-title">🧘 {gc['class_name']}</span>
                        <div>
                            {breaking_badge}
                            <span class="custom-badge badge-location">📍 {gc['location']}</span>
                        </div>
                    </div>
                    <p style="color:#cbd5e1; font-size:14px; margin-bottom:10px;">{gc['description']}</p>
                    <div>
                        <span class="custom-badge badge-type">⏰ Time: {time_range}</span>
                        <span class="custom-badge badge-squad">📅 Weekdays: {gc['weekday']}</span>
                        <span class="custom-badge badge-creator">👤 Instructor: {gc['instructor']}</span>
                        <span class="custom-badge badge-dept">Capacity: {gc['capacity']} seats</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- PAGE 3: CREATE ACTIVITY ---
elif page == "➕ Create Activity" and current_user:
    st.header("➕ Create a Dynamic Activity")
    st.markdown("Announce a new after-work gathering. Your squad colleagues will be notified.")
    
    with st.form("create_activity_form"):
        title = st.text_input("Activity Title", placeholder="e.g. Wednesday Badminton Friendly")
        description = st.text_area("Description", placeholder="e.g. Playing double courts. Friendly matches, beginners welcome!")
        
        col1, col2 = st.columns(2)
        with col1:
            activity_type = st.selectbox("Activity Type", ["football", "badminton", "running", "gym", "board games", "coffee", "ai", "zumba", "yoga"])
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
                    creator_id=current_user["id"]
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
                
    with col2:
        st.subheader("Your Interests")
        st.markdown("*Select the categories you'd like to discover. This matches against upcoming events.*")
        
        # Standard interest options
        all_interests = ["football", "running", "gym", "yoga", "badminton", "board games", "coffee", "ai", "product", "startup", "english", "movies"]
        
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
