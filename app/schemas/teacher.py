from typing import List, Optional
from pydantic import BaseModel, EmailStr

class CreateClassRequest(BaseModel):
    name: str
    grade_level: str
    academic_year: Optional[str] = "2025-2026"
    teacher_id: Optional[int] = None

class UpdateClassRequest(BaseModel):
    name: Optional[str] = None
    grade_level: Optional[str] = None
    academic_year: Optional[str] = None
    teacher_id: Optional[int] = None

class AddStudentRequest(BaseModel):
    name: str
    email: EmailStr
    student_code: Optional[str] = None
    phone: Optional[str] = None

class UpdateStudentRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    student_code: Optional[str] = None
    email: Optional[EmailStr] = None

class AttendanceItem(BaseModel):
    student_id: int
    status: str
    notes: Optional[str] = None

class SaveAttendanceRequest(BaseModel):
    class_id: int
    date: str
    subject: Optional[str] = "ទូទៅ"
    records: List[AttendanceItem]

class GradeItem(BaseModel):
    student_id: int
    score: float
    max_score: Optional[float] = 100.0

class SaveGradesRequest(BaseModel):
    class_id: int
    subject: str
    exam_type: str = "monthly"
    date: str
    records: List[GradeItem]

class AssignSubjectTeacherRequest(BaseModel):
    class_id: int
    teacher_id: int
    subject_name: str
