from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class CalendarEvent:
    """
    Represents a calendar event with standardized fields
    Compatible with Google Calendar and Outlook formats
    """
    id: str
    title: str
    start_time: datetime
    end_time: datetime
    event_type: str = "default"
    description: Optional[str] = None
    location: Optional[str] = None
    participants: int = 0
    attendees: Optional[List[str]] = None
    organizer: Optional[str] = None
    is_all_day: bool = False
    is_online_meeting: bool = False
    importance: str = "normal"  # low, normal, high
    status: str = "confirmed"  # confirmed, tentative, cancelled
    recurring: bool = False
    reminder_minutes: int = 15
    categories: Optional[List[str]] = None
    
    # Computed properties
    @property
    def duration_minutes(self) -> int:
        """Calculate event duration in minutes"""
        return int((self.end_time - self.start_time).total_seconds() / 60)
    
    @property
    def is_meeting(self) -> bool:
        """Check if event is a meeting (has attendees or certain keywords)"""
        if self.participants > 1 or (self.attendees and len(self.attendees) > 1):
            return True
        
        meeting_keywords = ['meeting', 'call', 'conference', 'standup', 'sync', 'review']
        return any(keyword in self.title.lower() for keyword in meeting_keywords)
    
    @property
    def is_long_meeting(self) -> bool:
        """Check if meeting is longer than 60 minutes"""
        return self.duration_minutes > 60
    
    @property
    def stress_indicators(self) -> Dict[str, bool]:
        """Return dictionary of potential stress indicators"""
        return {
            'is_long': self.duration_minutes > 60,
            'is_back_to_back': False,  # Will be calculated at calendar level
            'is_late_day': self.start_time.hour >= 17,
            'is_early_day': self.start_time.hour <= 7,
            'high_importance': self.importance == 'high',
            'many_attendees': self.participants > 10,
            'is_online': self.is_online_meeting
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation"""
        return {
            'id': self.id,
            'title': self.title,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'event_type': self.event_type,
            'description': self.description,
            'location': self.location,
            'participants': self.participants,
            'attendees': self.attendees,
            'organizer': self.organizer,
            'is_all_day': self.is_all_day,
            'is_online_meeting': self.is_online_meeting,
            'importance': self.importance,
            'status': self.status,
            'recurring': self.recurring,
            'reminder_minutes': self.reminder_minutes,
            'categories': self.categories,
            'duration_minutes': self.duration_minutes,
            'is_meeting': self.is_meeting,
            'stress_indicators': self.stress_indicators
        }
    
    @classmethod
    def from_google_calendar(cls, event_data: Dict[str, Any]) -> 'CalendarEvent':
        """Create CalendarEvent from Google Calendar API format"""
        # Parse start and end times
        start_data = event_data.get('start', {})
        end_data = event_data.get('end', {})
        
        # Handle both dateTime and date formats
        if 'dateTime' in start_data:
            start_time = datetime.fromisoformat(start_data['dateTime'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_data['dateTime'].replace('Z', '+00:00'))
            is_all_day = False
        else:
            # All-day event
            start_time = datetime.fromisoformat(start_data['date'])
            end_time = datetime.fromisoformat(end_data['date'])
            is_all_day = True
        
        # Extract attendees
        attendees_data = event_data.get('attendees', [])
        attendees = [att.get('email', '') for att in attendees_data]
        participants = len(attendees_data)
        
        # Determine event type based on various factors
        event_type = cls._determine_event_type(event_data)
        
        return cls(
            id=event_data.get('id', ''),
            title=event_data.get('summary', 'Untitled Event'),
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
            description=event_data.get('description', ''),
            location=event_data.get('location', ''),
            participants=participants,
            attendees=attendees,
            organizer=event_data.get('organizer', {}).get('email', ''),
            is_all_day=is_all_day,
            is_online_meeting=bool(event_data.get('conferenceData')),
            status=event_data.get('status', 'confirmed'),
            recurring=bool(event_data.get('recurringEventId')),
            categories=event_data.get('categories', [])
        )
    
    @classmethod
    def from_outlook_calendar(cls, event_data: Dict[str, Any]) -> 'CalendarEvent':
        """Create CalendarEvent from Outlook/Microsoft Graph API format"""
        # Parse start and end times
        start_data = event_data.get('start', {})
        end_data = event_data.get('end', {})
        
        start_time = datetime.fromisoformat(start_data['dateTime'])
        end_time = datetime.fromisoformat(end_data['dateTime'])
        
        # Extract attendees
        attendees_data = event_data.get('attendees', [])
        attendees = [att.get('emailAddress', {}).get('address', '') for att in attendees_data]
        participants = len(attendees_data)
        
        # Map importance
        importance_map = {'low': 'low', 'normal': 'normal', 'high': 'high'}
        importance = importance_map.get(event_data.get('importance', 'normal'), 'normal')
        
        return cls(
            id=event_data.get('id', ''),
            title=event_data.get('subject', 'Untitled Event'),
            start_time=start_time,
            end_time=end_time,
            event_type=cls._determine_event_type(event_data),
            description=event_data.get('body', {}).get('content', ''),
            location=event_data.get('location', {}).get('displayName', ''),
            participants=participants,
            attendees=attendees,
            organizer=event_data.get('organizer', {}).get('emailAddress', {}).get('address', ''),
            is_all_day=event_data.get('isAllDay', False),
            is_online_meeting=event_data.get('isOnlineMeeting', False),
            importance=importance,
            status='confirmed' if not event_data.get('isCancelled', False) else 'cancelled',
            recurring=bool(event_data.get('recurrence')),
            categories=event_data.get('categories', [])
        )
    
    @staticmethod
    def _determine_event_type(event_data: Dict[str, Any]) -> str:
        """Determine event type based on event data"""
        title = event_data.get('summary', event_data.get('subject', '')).lower()
        
        # Meeting types
        if any(word in title for word in ['meeting', 'call', 'conference', 'standup', 'sync']):
            return 'meeting'
        elif any(word in title for word in ['interview', 'candidate']):
            return 'interview'
        elif any(word in title for word in ['training', 'workshop', 'seminar']):
            return 'training'
        elif any(word in title for word in ['break', 'lunch', 'coffee']):
            return 'break'
        elif any(word in title for word in ['focus', 'deep work', 'coding']):
            return 'focus_time'
        elif any(word in title for word in ['travel', 'commute']):
            return 'travel'
        else:
            return 'other'