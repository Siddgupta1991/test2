import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import hashlib
import urllib.parse

# Import custom modules
from src.calendar_parser import CalendarParser
from src.models.calendar_event import CalendarEvent
from src.google_calendar_api import GoogleCalendarAPI
from src.auth.oauth_handler import GoogleOAuthHandler

# Page configuration
st.set_page_config(
    page_title="MindSync - Personal Wellbeing Companion",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'calendar_provider' not in st.session_state:
    st.session_state.calendar_provider = None
if 'calendar_data' not in st.session_state:
    st.session_state.calendar_data = None
if 'parsed_events' not in st.session_state:
    st.session_state.parsed_events = []
if 'google_oauth_handler' not in st.session_state:
    st.session_state.google_oauth_handler = GoogleOAuthHandler()
if 'google_calendar_api' not in st.session_state:
    st.session_state.google_calendar_api = GoogleCalendarAPI()

# Simple user database (in production, use proper database)
USER_DATABASE = {
    "demo_user": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # "password"
    "test_user": "ef92c9ae4b6b63c4c84d5ddaf8b4f0b6e1f6c9c5d2f8f7e8d1c9a5b4e6f3d2a1"   # "test123"
}

def hash_password(password):
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

def main():
    # No need to handle OAuth callback in URL since we're using manual code entry
    if not st.session_state.authenticated:
        show_auth_page()
    elif st.session_state.calendar_provider is None:
        show_calendar_provider_selection()
    else:
        show_main_app()

def show_auth_page():
    """Display authentication page"""
    st.title("🧠 Welcome to MindSync")
    st.subheader("Your Personal Wellbeing Companion")
    st.markdown("---")
    
    # Center the auth form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        auth_mode = st.radio(
            "Choose an option:", 
            ["Login", "Create Account", "Sign in with Google"], 
            horizontal=False,
            key="auth_mode_selector"
        )
        
        if auth_mode == "Sign in with Google":
            st.subheader("🔐 Google Authentication")
            st.markdown("Connect with your Google account to access your calendar data.")
            
            # Step 1: Generate auth URL
            if st.button("🚀 Get Google Auth Link", use_container_width=True, type="primary"):
                oauth_handler = st.session_state.google_oauth_handler
                auth_url = oauth_handler.get_auth_url()
                
                if auth_url:
                    st.session_state.google_auth_url = auth_url
                    st.success("✅ Authentication URL generated!")
                else:
                    st.error("Failed to generate authentication URL. Please check your configuration.")
            
            # Step 2: Show auth URL and code input
            if 'google_auth_url' in st.session_state:
                st.markdown("### 🔗 Step 1: Click the link below to authenticate:")
                st.markdown(f"[🔐 Authenticate with Google]({st.session_state.google_auth_url})")
                
                st.markdown("### 📝 Step 2: Copy and paste the authorization code:")
                auth_code = st.text_input(
                    "Authorization Code",
                    placeholder="Paste the code from Google here...",
                    key="google_auth_code"
                )
                
                if st.button("✅ Verify Code", disabled=not auth_code):
                    oauth_handler = st.session_state.google_oauth_handler
                    if oauth_handler.handle_manual_auth_code(auth_code):
                        # Successfully authenticated
                        user_info = oauth_handler.get_user_info()
                        if user_info:
                            st.session_state.authenticated = True
                            st.session_state.username = user_info.get('name', user_info.get('email', 'Google User'))
                            st.session_state.calendar_provider = 'google'
                            st.session_state.google_user_info = user_info
                            
                            # Initialize Google Calendar API
                            st.session_state.google_calendar_api = GoogleCalendarAPI()
                            
                            # Clear auth URL from session
                            del st.session_state.google_auth_url
                            
                            st.success("🎉 Successfully authenticated! Redirecting...")
                            st.rerun()
        
        else:
            with st.form("auth_form"):
                st.subheader(f"🔐 {auth_mode}")
                
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                
                if auth_mode == "Create Account":
                    confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
                
                submit_button = st.form_submit_button(auth_mode, use_container_width=True)
                
                if submit_button:
                    if auth_mode == "Login":
                        handle_login(username, password)
                    else:
                        if auth_mode == "Create Account":
                            handle_signup(username, password, confirm_password if 'confirm_password' in locals() else "")
        
        # Demo credentials info
        st.markdown("---")
        st.info("**Demo Credentials:**\n- Username: `demo_user` Password: `password`\n- Username: `test_user` Password: `test123`")

def handle_login(username, password):
    """Handle user login"""
    if not username or not password:
        st.error("Please enter both username and password")
        return
    
    hashed_password = hash_password(password)
    
    if username in USER_DATABASE and USER_DATABASE[username] == hashed_password:
        st.session_state.authenticated = True
        st.session_state.username = username
        st.success(f"Welcome back, {username}! 🎉")
        st.rerun()
    else:
        st.error("Invalid username or password")

def handle_signup(username, password, confirm_password):
    """Handle user account creation"""
    if not username or not password:
        st.error("Please enter both username and password")
        return
    
    if password != confirm_password:
        st.error("Passwords do not match")
        return
    
    if len(password) < 6:
        st.error("Password must be at least 6 characters long")
        return
    
    if username in USER_DATABASE:
        st.error("Username already exists")
        return
    
    # In a real app, you would save to a database
    USER_DATABASE[username] = hash_password(password)
    st.session_state.authenticated = True
    st.session_state.username = username
    st.success(f"Account created successfully! Welcome, {username}! 🎉")
    st.rerun()

def show_calendar_provider_selection():
    """Display calendar provider selection page"""
    st.title(f"👋 Welcome, {st.session_state.username}!")
    st.subheader("🗓️ Connect Your Calendar")
    
    # Center the provider selection
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Choose your calendar provider:")
        st.markdown("---")
        
        # Google Calendar option
        if st.button("📅 Google Calendar (Real Integration)", use_container_width=True, help="Connect with your actual Google Calendar", type="primary"):
            oauth_handler = st.session_state.google_oauth_handler
            if oauth_handler.is_authenticated():
                # Already authenticated, proceed with calendar setup
                st.session_state.calendar_provider = "google"
                load_real_google_calendar()
                st.rerun()
            else:
                # Need to authenticate first
                auth_url = oauth_handler.get_auth_url()
                if auth_url:
                    st.session_state.google_auth_url = auth_url
                    st.markdown("### 🔗 Step 1: Click the link below to authenticate:")
                    st.markdown(f"[🔐 Authenticate with Google Calendar]({auth_url})")
                    
                    st.markdown("### 📝 Step 2: Copy and paste the authorization code:")
                    auth_code = st.text_input(
                        "Authorization Code",
                        placeholder="Paste the code from Google here...",
                        key="provider_auth_code"
                    )
                    
                    if st.button("✅ Verify Code", disabled=not auth_code, key="provider_verify"):
                        if oauth_handler.handle_manual_auth_code(auth_code):
                            # Successfully authenticated
                            user_info = oauth_handler.get_user_info()
                            if user_info:
                                st.session_state.calendar_provider = "google"
                                st.session_state.google_user_info = user_info
                                
                                # Initialize Google Calendar API
                                st.session_state.google_calendar_api = GoogleCalendarAPI()
                                
                                # Load real calendar data
                                load_real_google_calendar()
                                st.rerun()
                else:
                    st.error("Failed to generate authentication URL.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Outlook option (still using sample data)
        if st.button("📧 Microsoft Outlook (Sample Data)", use_container_width=True, help="Connect with Microsoft Outlook (using sample data)"):
            st.session_state.calendar_provider = "outlook"
            load_calendar_data("outlook")
            st.rerun()
        
        st.markdown("---")
        st.info("💡 **Real Integration Available!** Google Calendar now connects to your actual calendar data.")
        
        # Logout option
        if st.button("🚪 Logout", type="secondary"):
            logout()

def load_real_google_calendar():
    """Load real Google Calendar data"""
    try:
        google_api = st.session_state.google_calendar_api
        
        if not google_api.is_connected():
            st.error("Not connected to Google Calendar. Please authenticate first.")
            return
        
        with st.spinner("🔄 Syncing your Google Calendar..."):
            # Sync calendar data
            sync_summary = google_api.sync_calendar_data()
            
            if sync_summary and 'events' in sync_summary:
                events = sync_summary['events']
                st.session_state.parsed_events = events
                st.session_state.calendar_data = {
                    'events': [event.to_dict() for event in events],
                    'sync_summary': sync_summary
                }
                
                st.success(f"✅ Successfully connected to Google Calendar! Loaded {len(events)} events.")
            else:
                st.warning("No events found in your Google Calendar for the next 7 days.")
                st.session_state.parsed_events = []
                st.session_state.calendar_data = {'events': []}
        
    except Exception as e:
        st.error(f"❌ Error loading Google Calendar data: {str(e)}")
        # Fallback to sample data
        st.warning("Falling back to sample data...")
        load_calendar_data("google")

def load_calendar_data(provider):
    """Load calendar data based on provider (fallback for sample data)"""
    try:
        # For now, load different sample data based on provider
        if provider == "google":
            sample_file = "data/sample_calendars/google_sample.json"
            try:
                with open(sample_file, 'r') as f:
                    calendar_data = json.load(f)
            except FileNotFoundError:
                # Fallback to mixed_day sample
                with open("data/sample_calendars/mixed_day.json", 'r') as f:
                    calendar_data = json.load(f)
        elif provider == "outlook":
            sample_file = "data/sample_calendars/outlook_sample.json"
            try:
                with open(sample_file, 'r') as f:
                    calendar_data = json.load(f)
            except FileNotFoundError:
                # Fallback to busy_day sample
                with open("data/sample_calendars/busy_day.json", 'r') as f:
                    calendar_data = json.load(f)
        
        st.session_state.calendar_data = calendar_data
        
        # Parse calendar events
        parser = CalendarParser()
        events = parser.parse_calendar(calendar_data)
        st.session_state.parsed_events = events
        
        st.success(f"✅ Successfully connected to {provider.title()} Calendar! Loaded {len(events)} events (sample data).")
        
    except Exception as e:
        st.error(f"❌ Error loading {provider} calendar data: {str(e)}")

def logout():
    """Handle user logout"""
    # Clear Google OAuth session
    if hasattr(st.session_state, 'google_oauth_handler'):
        st.session_state.google_oauth_handler.logout()
    
    # Clear all session state
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.calendar_provider = None
    st.session_state.calendar_data = None
    st.session_state.parsed_events = []
    
    # Reinitialize handlers
    st.session_state.google_oauth_handler = GoogleOAuthHandler()
    st.session_state.google_calendar_api = GoogleCalendarAPI()
    
    st.rerun()

def show_main_app():
    """Display the main application"""
    st.title("🧠 MindSync - Personal Wellbeing Companion")
    
    # Show connection status
    if st.session_state.calendar_provider == "google":
        google_api = st.session_state.google_calendar_api
        if google_api.is_connected():
            st.subheader("🔗 Connected to Google Calendar (Real Data)")
        else:
            st.subheader("📅 Google Calendar (Sample Data)")
    else:
        st.subheader(f"Connected to {st.session_state.calendar_provider.title()} Calendar (Sample Data)")
    
    # Sidebar navigation
    st.sidebar.title(f"👤 {st.session_state.username}")
    st.sidebar.markdown(f"📅 **Provider:** {st.session_state.calendar_provider.title()}")
    
    # Show real connection status in sidebar
    if st.session_state.calendar_provider == "google":
        google_api = st.session_state.google_calendar_api
        if google_api.is_connected():
            st.sidebar.success("✅ Real Google Calendar Connected")
        else:
            st.sidebar.warning("⚠️ Using Sample Data")
    
    st.sidebar.markdown("---")
    
    page = st.sidebar.selectbox("Navigate to:", [
        "📊 Dashboard",
        "📅 Calendar Data",
        "🔍 Stress Analysis", 
        "💡 Suggestions & Schedule",
        "📈 Analytics"
    ])
    
    # Sidebar actions
    st.sidebar.markdown("---")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 Sync Calendar", help="Refresh calendar data"):
            if st.session_state.calendar_provider == "google":
                load_real_google_calendar()
            else:
                load_calendar_data(st.session_state.calendar_provider)
            st.rerun()
    with col2:
        if st.button("🚪 Logout"):
            logout()
    
    # Page routing
    if page == "📊 Dashboard":
        dashboard_page()
    elif page == "📅 Calendar Data":
        calendar_data_page()
    elif page == "🔍 Stress Analysis":
        stress_analysis_page()
    elif page == "💡 Suggestions & Schedule":
        suggestions_page()
    elif page == "📈 Analytics":
        analytics_page()

def dashboard_page():
    """Main dashboard with overview"""
    st.header("📊 Dashboard Overview")
    
    if not st.session_state.parsed_events:
        st.warning("⚠️ No calendar data available!")
        
        # If using Google Calendar, show reconnect option
        if st.session_state.calendar_provider == "google":
            if st.button("🔄 Connect Google Calendar", type="primary"):
                oauth_handler = st.session_state.google_oauth_handler
                auth_url = oauth_handler.get_auth_url()
                if auth_url:
                    st.markdown(f"[Authenticate with Google Calendar]({auth_url})")
        return
    
    events = st.session_state.parsed_events
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📅 Total Events", len(events))
    with col2:
        total_duration = sum(event.duration_minutes for event in events)
        st.metric("⏱️ Total Duration", f"{total_duration} min")
    with col3:
        meetings = len([e for e in events if e.is_meeting])
        st.metric("🤝 Meetings", meetings)
    with col4:
        focus_time = len([e for e in events if e.event_type == 'focus_time'])
        st.metric("🎯 Focus Blocks", focus_time)
    
    st.markdown("---")
    
    # Show data source
    if st.session_state.calendar_provider == "google":
        google_api = st.session_state.google_calendar_api
        if google_api.is_connected():
            st.info("📊 **Real-time data** from your Google Calendar")
        else:
            st.warning("📊 **Sample data** - Connect your Google Calendar for real data")
    
    # Quick insights
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Upcoming Events")
        if events:
            # Sort by start time and show next 5
            upcoming_events = sorted(events, key=lambda x: x.start_time)[:5]
            for event in upcoming_events:
                if event.start_time >= datetime.now():
                    st.markdown(f"**{event.start_time.strftime('%H:%M')}** - {event.title}")
                    st.caption(f"{event.duration_minutes} min • {event.event_type}")
    
    with col2:
        st.subheader("⚡ Quick Stats")
        avg_duration = total_duration / len(events) if events else 0
        st.metric("Average Event Duration", f"{avg_duration:.1f} min")
        
        longest_event = max(events, key=lambda x: x.duration_minutes) if events else None
        if longest_event:
            st.metric("Longest Event", f"{longest_event.duration_minutes} min")
            st.caption(f"Event: {longest_event.title}")
    
    # Timeline preview
    if events:
        st.subheader("📅 Timeline Preview")
        create_timeline_chart(events[:10])  # Show first 10 events

def calendar_data_page():
    """Calendar data management page"""
    st.header("📅 Calendar Data Management")
    
    # Show current connection status
    if st.session_state.calendar_provider == "google":
        google_api = st.session_state.google_calendar_api
        if google_api.is_connected():
            st.success("✅ Connected to Google Calendar (Real Data)")
            
            # Show calendar selection options
            with st.expander("📋 Calendar Selection"):
                calendars = google_api.get_calendars()
                if calendars:
                    st.subheader("Your Calendars:")
                    for calendar in calendars:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"📅 **{calendar['summary']}**")
                            if calendar.get('description'):
                                st.caption(calendar['description'])
                        with col2:
                            if calendar.get('primary'):
                                st.badge("Primary", type="secondary")
                        with col3:
                            st.color_picker("", value=calendar.get('background_color', '#9FC6E7'), key=f"color_{calendar['id']}", disabled=True)
        else:
            st.warning("⚠️ Not connected to Google Calendar - Using sample data")
    
    # Option to load different sample data
    st.subheader("📄 Load Sample Data")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📄 Light Day Sample", use_container_width=True):
            load_sample_calendar("light_day")
    with col2:
        if st.button("📄 Busy Day Sample", use_container_width=True):
            load_sample_calendar("busy_day")
    with col3:
        if st.button("📄 Mixed Day Sample", use_container_width=True):
            load_sample_calendar("mixed_day")
    
    # Manual file upload option
    st.subheader("📁 Upload Custom Calendar File")
    uploaded_file = st.file_uploader(
        "Choose a JSON calendar file",
        type=['json'],
        help="Upload a JSON file containing your calendar events"
    )
    
    if uploaded_file is not None:
        try:
            calendar_data = json.load(uploaded_file)
            st.session_state.calendar_data = calendar_data
            
            # Parse calendar events
            parser = CalendarParser()
            events = parser.parse_calendar(calendar_data)
            st.session_state.parsed_events = events
            
            st.success(f"✅ Successfully loaded {len(events)} events!")
            
        except Exception as e:
            st.error(f"❌ Error loading calendar: {str(e)}")
    
    # Display current data if available
    if st.session_state.parsed_events:
        st.markdown("---")
        display_calendar_preview(st.session_state.parsed_events)

def load_sample_calendar(sample_type):
    """Load predefined sample calendar data"""
    try:
        with open(f"data/sample_calendars/{sample_type}.json", 'r') as f:
            calendar_data = json.load(f)
        
        st.session_state.calendar_data = calendar_data
        
        # Parse events
        parser = CalendarParser()
        events = parser.parse_calendar(calendar_data)
        st.session_state.parsed_events = events
        
        st.success(f"✅ Loaded {sample_type.replace('_', ' ')} sample with {len(events)} events!")
        
    except FileNotFoundError:
        st.error(f"❌ Sample file not found: {sample_type}.json")
    except Exception as e:
        st.error(f"❌ Error loading sample: {str(e)}")

def display_calendar_preview(events):
    """Display a preview of calendar events"""
    if not events:
        return
    
    st.subheader("📊 Calendar Preview")
    
    # Convert events to DataFrame for display
    event_data = []
    for event in events:
        event_data.append({
            'Title': event.title,
            'Start': event.start_time.strftime('%Y-%m-%d %H:%M'),
            'End': event.end_time.strftime('%Y-%m-%d %H:%M'),
            'Duration (min)': event.duration_minutes,
            'Type': event.event_type,
            'Participants': event.participants
        })
    
    df = pd.DataFrame(event_data)
    
    # Display events table
    st.dataframe(df, use_container_width=True)
    
    # Timeline visualization
    if len(events) > 0:
        st.subheader("📅 Timeline View")
        create_timeline_chart(events)

def create_timeline_chart(events):
    """Create a timeline visualization of events"""
    # Prepare data for timeline
    timeline_data = []
    for event in events:
        timeline_data.append({
            'Task': event.title[:30] + "..." if len(event.title) > 30 else event.title,
            'Start': event.start_time,
            'Finish': event.end_time,
            'Type': event.event_type
        })
    
    df_timeline = pd.DataFrame(timeline_data)
    
    # Create Gantt chart
    fig = px.timeline(
        df_timeline,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Type",
        title="Daily Schedule Timeline"
    )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

def stress_analysis_page():
    st.header("🔍 Stress Analysis")
    
    if not st.session_state.parsed_events:
        st.warning("⚠️ Please load calendar data first!")
        return
    
    st.info("🚧 Stress prediction functionality will be implemented in Week 2")
    
    # Placeholder for stress analysis
    st.subheader("Stress Prediction Rules Configuration")
    
    col1, col2 = st.columns(2)
    with col1:
        st.slider("Max consecutive meetings", 1, 10, 3)
        st.slider("Minimum break time (minutes)", 5, 60, 15)
    with col2:
        st.slider("Long meeting threshold (minutes)", 30, 180, 60)
        st.slider("Meeting density threshold", 1, 20, 8)

def suggestions_page():
    st.header("💡 Suggestions & Schedule")
    
    if not st.session_state.parsed_events:
        st.warning("⚠️ Please load calendar data first!")
        return
    
    st.info("🚧 Suggestion engine will be implemented in Week 2-3")

def analytics_page():
    st.header("📈 Analytics")
    
    if not st.session_state.parsed_events:
        st.warning("⚠️ Please load calendar data first!")
        return
    
    st.info("🚧 Analytics dashboard will be implemented in Week 3-4")

if __name__ == "__main__":
    main()