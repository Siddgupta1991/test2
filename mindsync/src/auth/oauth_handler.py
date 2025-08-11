"""
OAuth 2.0 Authentication Handler for Google APIs
Manages authentication flow, token storage, and refresh
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config.google_config import (
    GOOGLE_CALENDAR_SCOPES,
    TOKEN_FILE,
    CREDENTIALS_FILE,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES
)

class GoogleOAuthHandler:
    """
    Handles Google OAuth 2.0 authentication flow for Streamlit
    """
    
    def __init__(self):
        self.scopes = GOOGLE_CALENDAR_SCOPES
        self.credentials = None
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return self.get_valid_credentials() is not None
    
    def get_valid_credentials(self) -> Optional[Credentials]:
        """Get valid credentials, refreshing if necessary"""
        if self.credentials and self.credentials.valid:
            return self.credentials
        
        # Try to load from session state
        if 'google_credentials' in st.session_state:
            try:
                creds_data = st.session_state.google_credentials
                self.credentials = Credentials(
                    token=creds_data.get('token'),
                    refresh_token=creds_data.get('refresh_token'),
                    token_uri=creds_data.get('token_uri'),
                    client_id=creds_data.get('client_id'),
                    client_secret=creds_data.get('client_secret'),
                    scopes=creds_data.get('scopes')
                )
                
                # Check if credentials are expired and refresh if possible
                if self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    self._save_credentials_to_session()
                
                if self.credentials.valid:
                    return self.credentials
            except Exception as e:
                st.error(f"Error loading credentials: {e}")
                self.logout()
        
        # Try to load from token file (for development)
        if os.path.exists(TOKEN_FILE):
            try:
                self.credentials = Credentials.from_authorized_user_file(TOKEN_FILE, self.scopes)
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                    self._save_credentials_to_file()
                
                if self.credentials and self.credentials.valid:
                    self._save_credentials_to_session()
                    return self.credentials
            except Exception as e:
                st.error(f"Error loading token file: {e}")
        
        return None
    
def get_auth_url(self) -> Optional[str]:
        """Generate OAuth authorization URL"""
        try:
            # Check if running on Streamlit Cloud or locally
            if hasattr(st, 'secrets') and 'google_oauth' in st.secrets:
                # Streamlit Cloud - use secrets directly
                oauth_config = {
                    "web": {
                        "client_id": st.secrets.google_oauth.client_id,
                        "client_secret": st.secrets.google_oauth.client_secret,
                        "auth_uri": st.secrets.google_oauth.auth_uri,
                        "token_uri": st.secrets.google_oauth.token_uri,
                        "auth_provider_x509_cert_url": st.secrets.google_oauth.auth_provider_x509_cert_url,
                        "redirect_uris": [st.secrets.google_oauth.redirect_uri]
                    }
                }
                from google_auth_oauthlib.flow import Flow
                flow = Flow.from_client_config(oauth_config, scopes=self.scopes)
                flow.redirect_uri = st.secrets.google_oauth.redirect_uri
            else:
                # Local development - use credentials file
                if not os.path.exists(CREDENTIALS_FILE):
                    st.error("credentials.json file not found. Please add it to your project root.")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, 
                    scopes=self.scopes
                )
            
            # Generate authorization URL
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            # Store flow in session for later use
            st.session_state.oauth_flow = flow
            
            return auth_url
            
        except Exception as e:
            st.error(f"Error generating auth URL: {e}")
            return None
    
    def handle_manual_auth_code(self, authorization_code: str) -> bool:
        """Handle manual authorization code entry"""
        try:
            if 'oauth_flow' not in st.session_state:
                st.error("OAuth flow not found. Please try again.")
                return False
            
            flow = st.session_state.oauth_flow
            
            # Fetch token using the authorization code
            flow.fetch_token(code=authorization_code)
            self.credentials = flow.credentials
            
            # Save credentials
            self._save_credentials_to_session()
            self._save_credentials_to_file()
            
            # Get user info
            user_info = self._get_user_info()
            if user_info:
                st.session_state.google_user_info = user_info
            
            st.success(SUCCESS_MESSAGES["auth_success"])
            return True
            
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            return False
    
    def logout(self):
        """Logout user and clear credentials"""
        self.credentials = None
        
        # Clear session state
        if 'google_credentials' in st.session_state:
            del st.session_state.google_credentials
        if 'google_user_info' in st.session_state:
            del st.session_state.google_user_info
        if 'oauth_flow' in st.session_state:
            del st.session_state.oauth_flow
        
        # Remove token file
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
        
        st.success("Successfully logged out!")
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get authenticated user information"""
        if 'google_user_info' in st.session_state:
            return st.session_state.google_user_info
        
        return self._get_user_info()
    
    def _get_user_info(self) -> Optional[Dict[str, Any]]:
        """Fetch user information from Google"""
        try:
            credentials = self.get_valid_credentials()
            if not credentials:
                return None
            
            # Build People API service
            service = build('people', 'v1', credentials=credentials)
            
            # Get user profile
            profile = service.people().get(
                resourceName='people/me',
                personFields='names,emailAddresses,photos'
            ).execute()
            
            # Extract user info
            user_info = {}
            
            if 'names' in profile:
                name = profile['names'][0]
                user_info['name'] = name.get('displayName', '')
                user_info['given_name'] = name.get('givenName', '')
                user_info['family_name'] = name.get('familyName', '')
            
            if 'emailAddresses' in profile:
                email = profile['emailAddresses'][0]
                user_info['email'] = email.get('value', '')
            
            if 'photos' in profile:
                photo = profile['photos'][0]
                user_info['picture'] = photo.get('url', '')
            
            return user_info
            
        except Exception as e:
            st.error(f"Error fetching user info: {e}")
            return None
    
    def _save_credentials_to_session(self):
        """Save credentials to Streamlit session state"""
        if self.credentials:
            st.session_state.google_credentials = {
                'token': self.credentials.token,
                'refresh_token': self.credentials.refresh_token,
                'token_uri': self.credentials.token_uri,
                'client_id': self.credentials.client_id,
                'client_secret': self.credentials.client_secret,
                'scopes': self.credentials.scopes
            }
    
    def _save_credentials_to_file(self):
        """Save credentials to file for development"""
        if self.credentials:
            try:
                with open(TOKEN_FILE, 'w') as token:
                    token.write(self.credentials.to_json())
            except Exception as e:
                # Don't show error for file operations in production

                pass
