"""
Google API Configuration
Handles Google Calendar API settings and credentials
"""

import os
import streamlit as st

# Google Calendar API Configuration
GOOGLE_CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# OAuth 2.0 Configuration
OAUTH_REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # For desktop app flow
TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"

# API Configuration
CALENDAR_API_SERVICE_NAME = "calendar"
CALENDAR_API_VERSION = "v3"
PEOPLE_API_SERVICE_NAME = "people"
PEOPLE_API_VERSION = "v1"

def get_google_credentials():
    """
    Get Google API credentials from Streamlit secrets or environment
    """
    try:
        # Try to get from Streamlit secrets first
        if hasattr(st, 'secrets') and 'google' in st.secrets:
            return {
                "client_id": st.secrets.google.client_id,
                "client_secret": st.secrets.google.client_secret,
                "api_key": st.secrets.google.api_key
            }
        
        # Fallback to environment variables
        return {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "api_key": os.getenv("GOOGLE_API_KEY")
        }
    except Exception as e:
        st.error(f"Error loading Google credentials: {e}")
        return None

def get_oauth_config():
    """
    Get OAuth 2.0 configuration for Google
    """
    creds = get_google_credentials()
    if not creds:
        return None
    
    return {
        "web": {
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
        }
    }

# Error Messages
ERROR_MESSAGES = {
    "no_credentials": "❌ Google API credentials not found. Please check your configuration.",
    "auth_failed": "❌ Authentication failed. Please try again.",
    "api_error": "❌ Error accessing Google Calendar API. Please try again later.",
    "rate_limit": "⚠️ API rate limit reached. Please wait a moment and try again.",
    "no_events": "📅 No calendar events found.",
    "token_expired": "🔄 Authentication expired. Please log in again."
}

# Success Messages
SUCCESS_MESSAGES = {
    "auth_success": "✅ Successfully authenticated with Google!",
    "calendar_loaded": "📅 Calendar data loaded successfully!",
    "sync_complete": "🔄 Calendar sync completed!"
}