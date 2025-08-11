import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dateutil import parser as date_parser
import pytz

from .models.calendar_event import CalendarEvent

class CalendarParser:
    """
    Parses calendar data from various JSON formats
    Supports Google Calendar and Outlook/Microsoft Graph formats
    """
    
    def __init__(self):
        self.supported_formats = ['google', 'outlook', 'custom']
    
    def parse_calendar(self, calendar_data: Dict[str, Any]) -> List[CalendarEvent]:
        """
        Parse calendar data and return list of CalendarEvent objects
        Auto-detects format and processes accordingly
        """
        # Detect format
        calendar_format = self._detect_format(calendar_data)
        
        if calendar_format == 'google':
            return self._parse_google_calendar(calendar_data)
        elif calendar_format == 'outlook':
            return self._parse_outlook_calendar(calendar_data)
        elif calendar_format == 'custom':
            return self._parse_custom_calendar(calendar_data)
        else:
            raise ValueError(f"Unsupported calendar format detected")
    
    def _detect_format(self, calendar_data: Dict[str, Any]) -> str:
        """
        Auto-detect calendar format based on structure
        """
        # Check for Google Calendar format
        if 'items' in calendar_data and isinstance(calendar_data['items'], list):
            # Google Calendar API format
            return 'google'
        
        # Check for Outlook format
        if 'value' in calendar_data and isinstance(calendar_data['value'], list):
            # Microsoft Graph API format
            return 'outlook'
        
        # Check for custom format
        if 'events' in calendar_data and isinstance(calendar_data['events'], list):
            return 'custom'
        
        # Default to custom if we have a list directly
        if isinstance(calendar_data, list):
            return 'custom'
        
        return 'unknown'
    
    def _parse_google_calendar(self, calendar_data: Dict[str, Any]) -> List[CalendarEvent]:
        """Parse Google Calendar API format"""
        events = []
        items = calendar_data.get('items', [])
        
        for item in items:
            try:
                event = CalendarEvent.from_google_calendar(item)
                events.append(event)
            except Exception as e:
                print(f"Error parsing Google Calendar event: {e}")
                continue
        
        return events
    
    def _parse_outlook_calendar(self, calendar_data: Dict[str, Any]) -> List[CalendarEvent]:
        """Parse Outlook/Microsoft Graph API format"""
        events = []
        items = calendar_data.get('value', [])
        
        for item in items:
            try:
                event = CalendarEvent.from_outlook_calendar(item)
                events.append(event)
            except Exception as e:
                print(f"Error parsing Outlook event: {e}")
                continue
        
        return events
    
    def _parse_custom_calendar(self, calendar_data: Dict[str, Any]) -> List[CalendarEvent]:
        """Parse custom/simplified JSON format"""
        events = []
        
        # Handle both {'events': [...]} and direct list formats
        if 'events' in calendar_data:
            items = calendar_data['events']
        elif isinstance(calendar_data, list):
            items = calendar_data
        else:
            raise ValueError("Invalid custom calendar format")
        
        for item in items:
            try:
                event = self._create_event_from_custom(item)
                events.append(event)
            except Exception as e:
                print(f"Error parsing custom event: {e}")
                continue
        
        return events
    
    def _create_event_from_custom(self, event_data: Dict[str, Any]) -> CalendarEvent:
        """Create CalendarEvent from custom JSON format"""
        # Parse datetime strings
        start_time = self._parse_datetime(event_data['start'])
        end_time = self._parse_datetime(event_data['end'])
        
        # Extract attendees count
        participants = 0
        attendees = []
        
        if 'attendees' in event_data:
            if isinstance(event_data['attendees'], list):
                attendees = event_data['attendees']
                participants = len(attendees)
            elif isinstance(event_data['attendees'], int):
                participants = event_data['attendees']
        elif 'participants' in event_data:
            participants = event_data['participants']
        
        return CalendarEvent(
            id=event_data.get('id', str(hash(event_data.get('title', '') + str(start_time)))),
            title=event_data.get('title', event_data.get('summary', 'Untitled Event')),
            start_time=start_time,
            end_time=end_time,
            event_type=event_data.get('type', event_data.get('event_type', 'other')),
            description=event_data.get('description', ''),
            location=event_data.get('location', ''),
            participants=participants,
            attendees=attendees,
            organizer=event_data.get('organizer', ''),
            is_all_day=event_data.get('is_all_day', False),
            is_online_meeting=event_data.get('is_online_meeting', False),
            importance=event_data.get('importance', 'normal'),
            status=event_data.get('status', 'confirmed'),
            recurring=event_data.get('recurring', False),
            reminder_minutes=event_data.get('reminder_minutes', 15),
            categories=event_data.get('categories', [])
        )
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string in various formats"""
        try:
            # Try parsing as ISO format first
            if 'T' in dt_str:
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            else:
                # Try with dateutil parser for more flexibility
                return date_parser.parse(dt_str)
        except Exception as e:
            raise ValueError(f"Unable to parse datetime: {dt_str}. Error: {e}")
    
    def validate_calendar_data(self, calendar_data: Dict[str, Any]) -> List[str]:
        """
        Validate calendar data and return list of validation errors
        """
        errors = []
        
        # Check basic structure
        if not isinstance(calendar_data, dict) and not isinstance(calendar_data, list):
            errors.append("Calendar data must be a dictionary or list")
            return errors
        
        # Detect format and validate accordingly
        try:
            calendar_format = self._detect_format(calendar_data)
            
            if calendar_format == 'unknown':
                errors.append("Unknown calendar format")
                return errors
            
            # Try to parse events
            events = self.parse_calendar(calendar_data)
            
            if not events:
                errors.append("No valid events found in calendar data")
            
            # Validate individual events
            for i, event in enumerate(events):
                event_errors = self._validate_event(event, i)
                errors.extend(event_errors)
        
        except Exception as e:
            errors.append(f"Error parsing calendar: {str(e)}")
        
        return errors
    
    def _validate_event(self, event: CalendarEvent, index: int) -> List[str]:
        """Validate individual event"""
        errors = []
        
        if not event.title:
            errors.append(f"Event {index}: Missing title")
        
        if event.start_time >= event.end_time:
            errors.append(f"Event {index}: Start time must be before end time")
        
        if event.duration_minutes <= 0:
            errors.append(f"Event {index}: Invalid duration")
        
        if event.participants < 0:
            errors.append(f"Event {index}: Invalid participant count")
        
        return errors
    
    def export_events_to_json(self, events: List[CalendarEvent], format_type: str = 'custom') -> str:
        """Export events back to JSON format"""
        if format_type == 'custom':
            data = {
                'events': [event.to_dict() for event in events],
                'metadata': {
                    'total_events': len(events),
                    'exported_at': datetime.now().isoformat(),
                    'format': 'mindsync_custom'
                }
            }
        else:
            raise ValueError(f"Export format '{format_type}' not supported")
        
        return json.dumps(data, indent=2, default=str)