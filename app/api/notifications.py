from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Response
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
import requests
from io import BytesIO

from app.core.dependencies import get_db, get_current_user, require_teacher
from app.domain.models import (
    User, SchoolClass, Enrollment, Notification, NotificationRead, UserSetting
)
from app.schemas.notification import (
    SendNotificationRequest, NotificationResponse, UserSettingsUpdate, UserSettingsResponse
)
from app.domain.cloudinary_service import upload_file

router = APIRouter(prefix="/notifications", tags=["Notifications, Sounds & Settings"])

# -------------------------------------------------------------
# 1. User Settings (Notification & Sound preferences)
# -------------------------------------------------------------

def get_or_create_user_settings(user_id: int, db: Session) -> UserSetting:
    setting = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
    if not setting:
        setting = UserSetting(
            user_id=user_id,
            notification_enabled=1,
            sound_enabled=1,
            sound_type="bell",
            sound_volume=0.80,
            theme="light",
            language="km",
            email_notifications=1
        )
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting

@router.get("/settings", response_model=UserSettingsResponse)
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    setting = get_or_create_user_settings(user.id, db)
    return {
        "user_id": user.id,
        "notification_enabled": bool(setting.notification_enabled),
        "sound_enabled": bool(setting.sound_enabled),
        "sound_type": setting.sound_type,
        "sound_volume": float(setting.sound_volume),
        "theme": setting.theme,
        "language": setting.language,
        "email_notifications": bool(setting.email_notifications)
    }

@router.put("/settings", response_model=UserSettingsResponse)
def update_settings(
    payload: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    setting = get_or_create_user_settings(user.id, db)
    
    if payload.notification_enabled is not None:
        setting.notification_enabled = 1 if payload.notification_enabled else 0
    if payload.sound_enabled is not None:
        setting.sound_enabled = 1 if payload.sound_enabled else 0
    if payload.sound_type is not None:
        setting.sound_type = payload.sound_type.strip().lower()
    if payload.sound_volume is not None:
        setting.sound_volume = max(0.0, min(1.0, payload.sound_volume))
    if payload.theme is not None:
        setting.theme = payload.theme.strip().lower()
    if payload.language is not None:
        setting.language = payload.language.strip().lower()
    if payload.email_notifications is not None:
        setting.email_notifications = 1 if payload.email_notifications else 0
        
    db.commit()
    db.refresh(setting)
    
    return {
        "user_id": user.id,
        "notification_enabled": bool(setting.notification_enabled),
        "sound_enabled": bool(setting.sound_enabled),
        "sound_type": setting.sound_type,
        "sound_volume": float(setting.sound_volume),
        "theme": setting.theme,
        "language": setting.language,
        "email_notifications": bool(setting.email_notifications)
    }


# -------------------------------------------------------------
# 2. Sending Notifications (Teacher CRUD + Attachment upload)
# -------------------------------------------------------------

@router.post("/upload-attachment")
async def upload_notification_attachment(
    file: UploadFile = File(...),
    teacher: User = Depends(require_teacher)
):
    file_bytes = await file.read()
    res = upload_file(file_bytes, file.filename, folder="school_notifications")
    return {
        "success": True,
        "file_url": res["url"],
        "file_name": file.filename
    }

@router.post("", response_model=dict)
def create_notification(
    payload: SendNotificationRequest,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db)
):
    if payload.class_id and teacher.role != "admin":
        school_class = db.query(SchoolClass).filter(SchoolClass.id == payload.class_id).first()
        if not school_class or school_class.teacher_id != teacher.id:
            raise HTTPException(status_code=403, detail="អ្នកគ្មានសិទ្ធិផ្ញើការជូនដំណឹងទៅកាន់ថ្នាក់របស់គ្រូផ្សេងទេ")

    new_notif = Notification(
        sender_id=teacher.id,
        class_id=payload.class_id,
        student_id=payload.student_id,
        title=payload.title.strip(),
        message=payload.message.strip(),
        type=payload.type or "announcement",
        sound_type=payload.sound_type or "bell",
        file_url=payload.file_url,
        file_name=payload.file_name
    )
    db.add(new_notif)
    db.commit()
    db.refresh(new_notif)
    
    return {
        "success": True,
        "message": "បានផ្ញើដំណឹងដល់សិស្សដោយជោគជ័យ",
        "notification_id": new_notif.id
    }


# -------------------------------------------------------------
# 3. Reading & Listing Notifications (Student & Teacher)
# -------------------------------------------------------------

@router.get("", response_model=List[NotificationResponse])
def list_notifications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user.role == "teacher":
        # Teacher only sees notifications sent by themselves
        notifs = db.query(Notification).filter(
            Notification.sender_id == user.id
        ).order_by(desc(Notification.created_at)).all()
    elif user.role == "admin":
        # Admin sees all notifications
        notifs = db.query(Notification).order_by(desc(Notification.created_at)).all()
    else:
        # Student sees notifications matching their class or directed directly to them
        enrolled_class_ids = [e.class_id for e in user.enrollments]
        
        conditions = [
            Notification.student_id == user.id, # direct to this student
        ]
        if enrolled_class_ids:
            conditions.append(
                and_(Notification.class_id.in_(enrolled_class_ids), Notification.student_id.is_(None))
            )
        # Also include broadcast notifications (class_id is null and student_id is null)
        conditions.append(
            and_(Notification.class_id.is_(None), Notification.student_id.is_(None))
        )
        
        notifs = db.query(Notification).filter(or_(*conditions)).order_by(desc(Notification.created_at)).all()

    # Determine read state
    read_notif_ids = set(
        r.notification_id for r in db.query(NotificationRead).filter(NotificationRead.user_id == user.id).all()
    )
    
    results = []
    for n in notifs:
        results.append({
            "id": n.id,
            "sender_id": n.sender_id,
            "sender_name": n.sender.name if n.sender else "លោកគ្រូ/អ្នកគ្រូ",
            "class_id": n.class_id,
            "class_name": n.school_class.name if n.school_class else None,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "sound_type": n.sound_type,
            "file_url": n.file_url,
            "file_name": n.file_name,
            "created_at": n.created_at,
            "is_read": n.id in read_notif_ids
        })
    return results

@router.post("/{notification_id}/mark-read")
def mark_notification_read(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    existing = db.query(NotificationRead).filter(
        NotificationRead.notification_id == notification_id,
        NotificationRead.user_id == user.id
    ).first()
    
    if not existing:
        read_record = NotificationRead(
            notification_id=notification_id,
            user_id=user.id,
            read_at=datetime.utcnow()
        )
        db.add(read_record)
        db.commit()
        
    return {"success": True, "message": "បានសម្គាល់ថាបានអានរួច"}

@router.post("/mark-all-read")
def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notifs = list_notifications(user=user, db=db)
    read_ids = set(
        r.notification_id for r in db.query(NotificationRead).filter(NotificationRead.user_id == user.id).all()
    )
    
    for n in notifs:
        if n["id"] not in read_ids:
            db.add(NotificationRead(
                notification_id=n["id"],
                user_id=user.id,
                read_at=datetime.utcnow()
            ))
    db.commit()
    return {"success": True, "message": "បានសម្គាល់ទាំងអស់ថាបានអានរួច"}


# -------------------------------------------------------------
# 4. Download Attached Notification File
# -------------------------------------------------------------

@router.get("/{notification_id}/download")
def download_notification_file(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif or not notif.file_url:
        raise HTTPException(status_code=404, detail="រកមិនឃើញឯកសារភ្ជាប់សម្រាប់ដំណឹងនេះទេ")
        
    # Check permission if student
    if user.role == "student":
        enrolled_class_ids = [e.class_id for e in user.enrollments]
        allowed = (
            notif.student_id == user.id or
            (notif.class_id in enrolled_class_ids and notif.student_id is None) or
            (notif.class_id is None and notif.student_id is None)
        )
        if not allowed:
            raise HTTPException(status_code=403, detail="អ្នកគ្មានសិទ្ធិទាញយកឯកសារនេះទេ")
            
    # Stream the file from Cloudinary or external URL directly to the user
    try:
        req = requests.get(notif.file_url, stream=True, timeout=15)
        req.raise_for_status()
        
        filename = notif.file_name or f"notification_file_{notif.id}"
        content_type = req.headers.get("Content-Type", "application/octet-stream")
        
        return StreamingResponse(
            req.iter_content(chunk_size=8192),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except Exception as e:
        # Fallback redirect to direct file URL
        return RedirectResponse(url=notif.file_url)
