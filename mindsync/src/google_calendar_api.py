"""
Google Calendar API Integration
Handles real-time calendar data fetching and processing
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.models.calendar_event import CalendarEvent
from config.google_config import (
    CALENDAR_API_SERVICE_NAME,
    CALENDAR_API_VERSION,
    ERROR_MESSAGES,
    SUCCESS_MESSAGES
)

class GoogleCalendarAPI:
    """
    Google Calendar API client for fetching and managing calendar data
    """
    
    def __init__(self):
        self.oauth_handler = None  # Will be set when needed
        self.service = None
    
    def _initialize_service(self):
        """Initialize Google Calendar API service"""
        try:
            if not self.oauth_handler:
                # Get oauth handler from session state
                if 'google_oauth_handler' in st.session_state:
                    self.oauth_handler = st.session_state.google_oauth_handler
                else:
                    return
            
            credentials = self.oauth_handler.get_valid_credentials()
            if credentials:
                self.service = build(
                    CALENDAR_API_SERVICE_NAME,
                    CALENDAR_API_VERSION,
                    credentials=credentials
                )
        except Exception as e:
            st.error(f"Error initializing Calendar API: {e}")
            self.service = None
    
    def is_connected(self) -> bool:
        """Check if connected to Google Calendar API"""
        if not self.service:
            self._initialize_service()
        return self.service is not None
    
    def get_calendars(self) -> List[Dict[str, Any]]:
        """Get list of user's calendars"""
        if not self.is_connected():
            return []
        
        try:
            calendar_list = self.service.calendarList().list().execute()
            calendars = []
            
            for calendar_item in calendar_list.get('items', []):
                calendars.append({
                    'id': calendar_item['id'],
                    'summary': calendar_item.get('summary', 'Unnamed Calendar'),
                    'description': calendar_item.get('description', ''),
                    'primary': calendar_item.get('primary', False),
                    'access_role': calendar_item.get('accessRole', 'reader'),
                    'selected': calendar_item.get('selected', True),
                    'color_id': calendar_item.get('colorId', '1'),
                    'background_color': calendar_item.get('backgroundColor', '#9FC6E7')
                })
            
            return calendars
            
        except HttpError as e:
            if e.resp.status == 403:
                st.error(ERROR_MESSAGES["rate_limit"])
            else:
                st.error(f"Error fetching calendars: {e}")
            return []
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            return []
    
    def get_events(
        self,
        calendar_id: str = 'primary',
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
        single_events: bool = True,
        order_by: str = 'startTime'
    ) -> List[CalendarEvent]:
        """
        Fetch events from Google Calendar
        
        Args:
            calendar_id: Calendar ID to fetch from (default: 'primary')
            time_min: Start time for event range
            time_max: End time for event range
            max_results: Maximum number of events to fetch
            single_events: Whether to expand recurring events
            order_by: Sort order for events
        
        Returns:
            List of CalendarEvent objects
        """
        if not self.is_connected():
            st.error("Not connected to Google Calendar")
            return []
        
        try:
            # Set default time range if not provided
            if time_min is None:
                time_min = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if time_max is None:
                time_max = time_min + timedelta(days=7)  # Next 7 days
            
            # Convert to RFC3339 format
            time_min_rfc = time_min.isoformat() + 'Z'
            time_max_rfc = time_max.isoformat() + 'Z'
            
            # Fetch events from Google Calendar API
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min_rfc,
                timeMax=time_max_rfc,
                maxResults=max_results,
                singleEvents=single_events,
                orderBy=order_by,
                showDeleted=False
            ).execute()
            
            events = events_result.get('items', [])
            
            if not events:
                st.info(ERROR_MESSAGES["no_events"])
                return []
            
            # Convert to CalendarEvent objects
            calendar_events = []
            for event in events:
                try:
                    calendar_event = CalendarEvent.from_google_calendar(event)
                    calendar_events.append(calendar_event)
                except Exception as e:
                    st.warning(f"Error processing event '{event.get('summary', 'Unknown')}': {e}")
                    continue
            
            st.success(f"{SUCCESS_MESSAGES['calendar_loaded']} Found {len(calendar_events)} events.")
            return calendar_events
            
        except HttpError as e:
            if e.resp.status == 403:
                st.error(ERROR_MESSAGES["rate_limit"])
            elif e.resp.status == 401:
                st.error(ERROR_MESSAGES["token_expired"])
                if self.oauth_handler:
                    self.oauth_handler.logout()
            else:
                st.error(f"API Error: {e}")
            return []
        except Exception as e:
            st.error(f"Error fetching events: {e}")
            return []
    
    def get_events_for_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        calendar_ids: List[str] = None
    ) -> List[CalendarEvent]:
        """
        Get events for a specific date range from multiple calendars
        
        Args:
            start_date: Start date
            end_date: End date  
            calendar_ids: List of calendar IDs (default: primary only)
        
        Returns:
            List of CalendarEvent objects
        """
        if calendar_ids is None:
            calendar_ids = ['primary']
        
        all_events = []
        
        for calendar_id in calendar_ids:
            events = self.get_events(
                calendar_id=calendar_id,
                time_min=start_date,
                time_max=end_date,
                max_results=250  # Higher limit for date range queries
            )
            all_events.extend(events)
        
        # Sort events by start time
        all_events.sort(key=lambda x: x.start_time)
        
        return all_events
    
    def get_today_events(self) -> List[CalendarEvent]:
        """Get today's events"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        
        return self.get_events(
            time_min=today,
            time_max=tomorrow,
            max_results=50
        )
    
    def get_week_events(self) -> List[CalendarEvent]:
        """Get this week's events"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today + timedelta(days=7)
        
        return self.get_events(
            time_min=today,
            time_max=week_end,
            max_results=100
        )
    
    def get_upcoming_events(self, limit: int = 10) -> List[CalendarEvent]:
        """Get upcoming events starting from now"""
        now = datetime.now()
        week_later = now + timedelta(days=7)
        
        return self.get_events(
            time_min=now,
            time_max=week_later,
            max_results=limit
        )
    
    def search_events(self, query: str, max_results: int = 25) -> List[CalendarEvent]:
        """
        Search for events containing specific text
        
        Args:
            query: Search query
            max_results: Maximum number of results
        
        Returns:
            List of matching CalendarEvent objects
        """
        if not self.is_connected():
            return []
        
        try:
            # Search in the next 30 days
            time_min = datetime.now()
            time_max = time_min + timedelta(days=30)
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime',
                q=query  # Search query
            ).execute()
            
            events = events_result.get('items', [])
            
            # Convert to CalendarEvent objects
            calendar_events = []
            for event in events:
                try:
                    calendar_event = CalendarEvent.from_google_calendar(event)
                    calendar_events.append(calendar_event)
                except Exception as e:
                    continue
            
            return calendar_events
            
        except Exception as e:
            st.error(f"Error searching events: {e}")
            return []
    
    def sync_calendar_data(self) -> Dict[str, Any]:
        """
        Sync calendar data and return summary
        
        Returns:
            Dictionary with sync summary
        """
        try:
            # Get calendar list
            calendars = self.get_calendars()
            
            # Get events for the next week
            events = self.get_week_events()
            
            # Calculate summary statistics
            total_events = len(events)
            total_meetings = len([e for e in events if e.is_meeting])
            total_duration = sum(e.duration_minutes for e in events)
            
            today_events = [e for e in events if e.start_time.date() == datetime.now().date()]
            
            sync_summary = {
                'calendars_count': len(calendars),
                'total_events': total_events,
                'total_meetings': total_meetings,
                'total_duration_hours': round(total_duration / 60, 1),
                'today_events': len(today_events),
                'sync_time': datetime.now(),
                'events': events,
                'calendars': calendars
            }
            
            # Store in session state
            st.session_state.calendar_sync_data = sync_summary
            
            st.success(SUCCESS_MESSAGES["sync_complete"])
            return sync_summary
            
        except Exception as e:
            st.error(f"Error syncing calendar data: {e}")
            return {}
    
    def get_calendar_statistics(self) -> Dict[str, Any]:
        """Get calendar usage statistics"""
        events = self.get_week_events()
        
        if not events:
            return {}
        
        # Calculate various statistics
        stats = {
            'total_events': len(events),
            'total_meetings': len([e for e in events if e.is_meeting]),
            'total_focus_time': len([e for e in events if e.event_type == 'focus_time']),
            'total_duration_minutes': sum(e.duration_minutes for e in events),
            'average_event_duration': sum(e.duration_minutes for e in events) / len(events),
            'longest_event_duration': max(e.duration_minutes for e in events),
            'events_by_day': {},
            'events_by_type': {},
            'events_by_hour': {}
        }
        
        # Group by day
        for event in events:
            day = event.start_time.strftime('%A')
            stats['events_by_day'][day] = stats['events_by_day'].get(day, 0) + 1
        
        # Group by type
        for event in events:
            event_type = event.event_type
            stats['events_by_type'][event_type] = stats['events_by_type'].get(event_type, 0) + 1
        
        # Group by hour
        for event in events:
            hour = event.start_time.hour
            stats['events_by_hour'][hour] = stats['events_by_hour'].get(hour, 0) + 1
        
        return stats