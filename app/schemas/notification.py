from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class SendNotificationRequest(BaseModel):
    title: str
    message: str
    class_id: Optional[int] = None # If None, can be broadcast or to specific student
    student_id: Optional[int] = None # If set, direct to this student only
    type: Optional[str] = "announcement" # 'announcement', 'homework', 'grade', 'urgent'
    sound_type: Optional[str] = "bell" # 'bell', 'chime', 'gentle', 'alert'
    file_url: Optional[str] = None
    file_name: Optional[str] = None

class NotificationResponse(BaseModel):
    id: int
    sender_id: int
    sender_name: str
    class_id: Optional[int] = None
    class_name: Optional[str] = None
    title: str
    message: str
    type: str
    sound_type: str
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    created_at: datetime
    is_read: bool

class UserSettingsUpdate(BaseModel):
    notification_enabled: Optional[bool] = None
    sound_enabled: Optional[bool] = None
    sound_type: Optional[str] = None # 'bell', 'chime', 'gentle', 'alert'
    sound_volume: Optional[float] = None # 0.0 to 1.0
    theme: Optional[str] = None # 'light', 'dark', 'system'
    language: Optional[str] = None # 'km', 'en'
    email_notifications: Optional[bool] = None

class UserSettingsResponse(BaseModel):
    user_id: int
    notification_enabled: bool
    sound_enabled: bool
    sound_type: str
    sound_volume: float
    theme: str
    language: str
    email_notifications: bool
