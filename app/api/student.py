from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.dependencies import get_db, require_student
from app.domain.models import (
    User, SchoolClass, Enrollment, Attendance, Grade, Homework, Submission
)

router = APIRouter(prefix="/student", tags=["Student Management Flow"])

@router.get("/dashboard")
def get_student_dashboard(student: User = Depends(require_student), db: Session = Depends(get_db)):
    student_id = student.id
    
    # 1. Fetch class enrollment info for student
    enrollment = db.query(Enrollment).filter(Enrollment.student_id == student_id).first()
    if not enrollment:
        return {
            "student": {
                "id": student.id,
                "email": student.email,
                "name": student.name,
                "role": student.role,
                "student_code": student.student_code,
                "phone": student.phone,
                "avatar_url": student.avatar_url
            },
            "class_info": None,
            "attendance_summary": {"present": 0, "absent": 0, "permission": 0, "rate": 100},
            "grades_summary": {"average": 0.0, "letter": "N/A", "rank": "-"},
            "pending_homeworks": 0
        }
        
    class_obj = enrollment.school_class
    teacher = class_obj.teacher if class_obj else None
    
    class_info = {
        "id": class_obj.id,
        "name": class_obj.name,
        "grade_level": class_obj.grade_level,
        "academic_year": class_obj.academic_year,
        "teacher_name": teacher.name if teacher else "N/A",
        "roll_no": enrollment.roll_no
    }
    
    # 2. Attendance summary strictly for this student
    att_records = db.query(Attendance.status, func.count(Attendance.id)).filter(
        Attendance.student_id == student_id,
        Attendance.class_id == class_obj.id
    ).group_by(Attendance.status).all()
    
    att_counts = {status: count for status, count in att_records}
    present = att_counts.get("present", 0)
    absent = att_counts.get("absent", 0)
    permission = att_counts.get("permission", 0)
    total_days = present + absent + permission
    rate = round(((present + permission * 0.5) / total_days * 100) if total_days > 0 else 100.0, 1)
    
    # 3. Class rank and average
    total_students_in_class = db.query(Enrollment).filter(Enrollment.class_id == class_obj.id).count()
    all_ranks = db.query(
        Grade.student_id,
        func.avg(Grade.score).label("avg_score")
    ).filter(
        Grade.class_id == class_obj.id
    ).group_by(Grade.student_id).order_by(func.avg(Grade.score).desc()).all()
    
    my_rank = "-"
    my_avg = 0.0
    for idx, r in enumerate(all_ranks, start=1):
        if r.student_id == student_id:
            my_rank = f"{idx}/{total_students_in_class}" if total_students_in_class > 0 else str(idx)
            my_avg = round(float(r.avg_score), 2)
            break
            
    letter = "A" if my_avg >= 90 else ("B" if my_avg >= 80 else ("C" if my_avg >= 70 else ("D" if my_avg >= 60 else ("E" if my_avg >= 50 else "F"))))
    gpa = round(min(4.0, max(0.0, (my_avg / 100.0) * 4.0)), 2)
    
    # 4. Pending homework count
    submitted_hw_ids = db.query(Submission.homework_id).filter(
        Submission.student_id == student_id
    ).subquery()
    
    pending_hw = db.query(Homework).filter(
        Homework.class_id == class_obj.id,
        ~Homework.id.in_(submitted_hw_ids)
    ).count()
    
    return {
        "student": {
            "id": student.id,
            "email": student.email,
            "name": student.name,
            "role": student.role,
            "student_code": student.student_code,
            "phone": student.phone,
            "avatar_url": student.avatar_url
        },
        "class_info": class_info,
        "attendance_summary": {
            "present": present,
            "absent": absent,
            "permission": permission,
            "total_days": total_days,
            "rate": rate
        },
        "grades_summary": {
            "average": my_avg,
            "gpa": gpa,
            "letter": letter,
            "rank": my_rank
        },
        "pending_homeworks": pending_hw
    }

@router.get("/attendance")
def get_student_attendance(student: User = Depends(require_student), db: Session = Depends(get_db)):
    """Strict data isolation: student can only fetch their own attendance records."""
    records = db.query(Attendance).filter(
        Attendance.student_id == student.id
    ).order_by(Attendance.date.desc()).all()
    
    return [
        {
            "date": str(record.date),
            "status": record.status,
            "notes": record.notes,
            "created_at": record.created_at
        }
        for record in records
    ]

@router.get("/grades")
def get_student_grades(student: User = Depends(require_student), db: Session = Depends(get_db)):
    """Strict data isolation: student can only fetch their own grades."""
    records = db.query(Grade).join(SchoolClass, Grade.class_id == SchoolClass.id).filter(
        Grade.student_id == student.id
    ).order_by(Grade.date.desc(), Grade.subject.asc()).all()
    
    return [
        {
            "id": record.id,
            "subject": record.subject,
            "exam_type": record.exam_type,
            "score": float(record.score),
            "max_score": float(record.max_score),
            "date": str(record.date),
            "class_name": record.school_class.name if record.school_class else ""
        }
        for record in records
    ]

@router.get("/homework")
def get_student_homeworks(student: User = Depends(require_student), db: Session = Depends(get_db)):
    """
    Returns all homework assigned to student's enrolled class with status:
    - submitted: student already submitted
    - late: past deadline and not submitted
    - pending: not submitted yet and before deadline
    """
    enrollment = db.query(Enrollment).filter(Enrollment.student_id == student.id).first()
    if not enrollment:
        return []
        
    homeworks = db.query(Homework).filter(
        Homework.class_id == enrollment.class_id
    ).order_by(Homework.created_at.desc()).all()
    
    now_str = datetime.utcnow().strftime("%Y-%m-%d")
    results = []
    
    for hw in homeworks:
        sub = next((s for s in hw.submissions if s.student_id == student.id), None)
        
        if sub:
            status_flag = "submitted"
        else:
            # Compare deadline date string if ISO format or string comparison
            deadline_str = hw.deadline.strip()
            if deadline_str < now_str:
                status_flag = "late"
            else:
                status_flag = "pending"
                
        results.append({
            "id": hw.id,
            "class_id": hw.class_id,
            "title": hw.title,
            "subject": hw.subject,
            "description": hw.description,
            "file_url": hw.file_url,
            "file_name": hw.file_name,
            "deadline": hw.deadline,
            "is_qcm": bool(hw.is_qcm),
            "created_at": hw.created_at,
            "status": status_flag,
            "submission": {
                "id": sub.id,
                "file_url": sub.file_url,
                "file_name": sub.file_name,
                "student_note": sub.student_note,
                "score": float(sub.score) if sub.score is not None else None,
                "feedback": sub.feedback,
                "submitted_at": sub.submitted_at,
                "graded_at": sub.graded_at
            } if sub else None
        })
        
    return results
