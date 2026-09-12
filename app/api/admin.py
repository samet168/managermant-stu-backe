from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.dependencies import get_db, require_admin
from app.core.security import get_password_hash
from app.domain.models import (
    User, SchoolClass, Enrollment, Attendance, Grade, Homework, Submission, Invoice
)

router = APIRouter(prefix="/admin", tags=["Admin Management & RBAC Flow"])

class CreateTeacherRequest(BaseModel):
    name: str
    email: str
    password: Optional[str] = "123456"
    phone: Optional[str] = None
    role: Optional[str] = "teacher"

class UpdateRoleRequest(BaseModel):
    role: str  # 'admin', 'teacher', 'student'

class AssignTeacherRequest(BaseModel):
    teacher_id: int

class UpdateUserStatusRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None

@router.get("/stats")
def get_admin_stats(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    total_teachers = db.query(User).filter(User.role == "teacher").count()
    total_students = db.query(User).filter(User.role == "student").count()
    total_classes = db.query(SchoolClass).count()
    total_homeworks = db.query(Homework).count()
    
    # Financial summary
    invoices = db.query(Invoice).all()
    total_revenue = sum(float(inv.paid_amount) for inv in invoices)
    total_pending_fee = sum(float(inv.total_amount - inv.paid_amount) for inv in invoices if inv.status != "paid")
    
    # Attendance summary
    total_attendances = db.query(Attendance).count()
    present_attendances = db.query(Attendance).filter(Attendance.status == "present").count()
    permission_attendances = db.query(Attendance).filter(Attendance.status == "permission").count()
    
    if total_attendances > 0:
        attendance_rate = round(((present_attendances + permission_attendances * 0.5) / total_attendances) * 100, 1)
    else:
        attendance_rate = 100.0

    return {
        "total_teachers": total_teachers,
        "total_students": total_students,
        "total_classes": total_classes,
        "total_homeworks": total_homeworks,
        "attendance_rate": attendance_rate,
        "total_revenue": total_revenue,
        "total_pending_fee": total_pending_fee
    }

@router.get("/users")
def list_all_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    
    if role and role != "all":
        query = query.filter(User.role == role)
        
    if search:
        s = f"%{search.strip()}%"
        query = query.filter((User.name.ilike(s)) | (User.email.ilike(s)) | (User.student_code.ilike(s)))
        
    users = query.order_by(User.id.desc()).all()
    
    results = []
    for u in users:
        enrolled_class = None
        if u.role == "student":
            enr = db.query(Enrollment).filter(Enrollment.student_id == u.id).first()
            if enr and enr.school_class:
                enrolled_class = f"{enr.school_class.name} ({enr.school_class.grade_level})"
                
        taught_classes_count = 0
        if u.role in ["teacher", "admin"]:
            taught_classes_count = db.query(SchoolClass).filter(SchoolClass.teacher_id == u.id).count()
            
        results.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "student_code": u.student_code,
            "phone": u.phone,
            "avatar_url": u.avatar_url,
            "enrolled_class": enrolled_class,
            "taught_classes_count": taught_classes_count,
            "created_at": u.created_at
        })
        
    return results

@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: UpdateRoleRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if payload.role not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=400, detail="តួនាទីមិនត្រឹមត្រូវ (Invalid role)")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="រកមិនឃើញអ្នកប្រើប្រាស់នេះទេ")
        
    # Prevent demoting the last admin if only 1 admin left
    if user.role == "admin" and payload.role != "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="មិនអាចផ្លាស់ប្ដូរតួនាទី Admin ចុងក្រោយបានទេ")
            
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return {"success": True, "message": "បានកែប្រែតួនាទីដោយជោគជ័យ", "role": user.role}

@router.get("/teachers")
def list_teachers(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    teachers = db.query(User).filter(User.role.in_(["teacher", "admin"])).order_by(User.name.asc()).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "email": t.email,
            "role": t.role,
            "phone": t.phone
        }
        for t in teachers
    ]

@router.get("/classes")
def list_all_classes_admin(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    classes = db.query(SchoolClass).order_by(SchoolClass.id.asc()).all()
    results = []
    for c in classes:
        teacher = c.teacher
        student_count = db.query(Enrollment).filter(Enrollment.class_id == c.id).count()
        results.append({
            "id": c.id,
            "name": c.name,
            "grade_level": c.grade_level,
            "academic_year": c.academic_year,
            "teacher_id": c.teacher_id,
            "teacher_name": teacher.name if teacher else "គ្មានគ្រូបង្រៀន",
            "student_count": student_count
        })
    return results

@router.post("/classes/{class_id}/assign-teacher")
def assign_teacher_to_class(
    class_id: int,
    payload: AssignTeacherRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    school_class = db.query(SchoolClass).filter(SchoolClass.id == class_id).first()
    if not school_class:
        raise HTTPException(status_code=404, detail="រកមិនឃើញថ្នាក់រៀននេះទេ")
        
    teacher = db.query(User).filter(User.id == payload.teacher_id).first()
    if not teacher or teacher.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=400, detail="សូមជ្រើសរើសគណនីគ្រូបង្រៀន ឬ Admin")
        
    school_class.teacher_id = teacher.id
    db.commit()
    db.refresh(school_class)
    return {"success": True, "message": f"បានចាត់តាំងលោកគ្រូ/អ្នកគ្រូ {teacher.name} បង្រៀនថ្នាក់ {school_class.name} រួចរាល់"}

@router.post("/teachers")
def create_teacher(
    payload: CreateTeacherRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="អ៊ីមែលនេះមានក្នុងប្រព័ន្ធរួចហើយ (Email already exists)")
        
    new_user = User(
        name=payload.name.strip(),
        email=email,
        hashed_password=get_password_hash(payload.password or "123456"),
        role=payload.role if payload.role in ["admin", "teacher"] else "teacher",
        phone=payload.phone.strip() if payload.phone else None,
        created_at=datetime.utcnow().strftime("%Y-%m-%d")
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "id": new_user.id,
        "name": new_user.name,
        "email": new_user.email,
        "role": new_user.role,
        "phone": new_user.phone,
        "taught_classes_count": 0,
        "created_at": new_user.created_at,
        "message": f"បានបង្កើតគណនី {new_user.name} ដោយជោគជ័យ"
    }
