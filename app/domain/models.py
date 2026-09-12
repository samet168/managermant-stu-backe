from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Date, DateTime, ForeignKey, Boolean,
    CheckConstraint, UniqueConstraint, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="student")  # 'teacher', 'student', 'admin'
    student_code = Column(String(50), unique=True, nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    avatar_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    taught_classes = relationship("SchoolClass", back_populates="teacher", cascade="all, delete-orphan")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")
    attendances = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    grades = relationship("Grade", back_populates="student", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="student", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="student", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("role IN ('teacher', 'student', 'admin')", name="check_user_role"),
    )

    @property
    def is_teacher(self) -> bool:
        return self.role == "teacher"

    @property
    def is_student(self) -> bool:
        return self.role == "student"


class SchoolClass(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    grade_level = Column(String(50), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    academic_year = Column(String(50), default="2025-2026")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    teacher = relationship("User", back_populates="taught_classes")
    enrollments = relationship("Enrollment", back_populates="school_class", cascade="all, delete-orphan")
    attendances = relationship("Attendance", back_populates="school_class", cascade="all, delete-orphan")
    grades = relationship("Grade", back_populates="school_class", cascade="all, delete-orphan")
    homeworks = relationship("Homework", back_populates="school_class", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    roll_no = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    school_class = relationship("SchoolClass", back_populates="enrollments")
    student = relationship("User", back_populates="enrollments")

    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_class_student_enrollment"),
    )


class Attendance(Base):
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    status = Column(String(20), nullable=False)  # 'present', 'absent', 'permission'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    school_class = relationship("SchoolClass", back_populates="attendances")
    student = relationship("User", back_populates="attendances")

    __table_args__ = (
        CheckConstraint("status IN ('present', 'absent', 'permission')", name="check_attendance_status"),
        UniqueConstraint("class_id", "student_id", "date", name="uq_class_student_date_attendance"),
    )


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String(100), nullable=False)
    exam_type = Column(String(50), default="monthly")
    score = Column(Numeric(5, 2), nullable=False)
    max_score = Column(Numeric(5, 2), default=100.0)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    school_class = relationship("SchoolClass", back_populates="grades")
    student = relationship("User", back_populates="grades")

    @property
    def letter_grade(self) -> str:
        avg = (float(self.score) / float(self.max_score)) * 100 if self.max_score and float(self.max_score) > 0 else 0
        if avg >= 90:
            return "A"
        elif avg >= 80:
            return "B"
        elif avg >= 70:
            return "C"
        elif avg >= 60:
            return "D"
        elif avg >= 50:
            return "E"
        return "F"


class Homework(Base):
    __tablename__ = "homeworks"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    subject = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    file_url = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    deadline = Column(String(50), nullable=False)
    # QCM flag: True = this homework uses multiple-choice questions, False = file upload
    is_qcm = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    school_class = relationship("SchoolClass", back_populates="homeworks")
    teacher = relationship("User")
    submissions = relationship("Submission", back_populates="homework", cascade="all, delete-orphan")
    questions = relationship("HomeworkQuestion", back_populates="homework", cascade="all, delete-orphan", order_by="HomeworkQuestion.order_index")


class HomeworkQuestion(Base):
    """A single MCQ question belonging to a QCM homework."""
    __tablename__ = "homework_questions"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    # choices stored as JSON list: ["choice A", "choice B", "choice C", "choice D"]
    choices = Column(JSON, nullable=False)
    # correct_answer is 0-based index into choices list (e.g. 0 = first choice)
    correct_answer = Column(Integer, nullable=False)
    order_index = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    homework = relationship("Homework", back_populates="questions")
    student_answers = relationship("StudentAnswer", back_populates="question", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    # file_url is nullable because QCM submissions don't need a file
    file_url = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    student_note = Column(Text, nullable=True)
    score = Column(Numeric(5, 2), nullable=True)
    feedback = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    graded_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    homework = relationship("Homework", back_populates="submissions")
    student = relationship("User", back_populates="submissions")
    qcm_answers = relationship("StudentAnswer", back_populates="submission", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("homework_id", "student_id", name="uq_homework_student_submission"),
    )

    @property
    def is_graded(self) -> bool:
        return self.score is not None


class StudentAnswer(Base):
    """A student's answer to a single QCM question."""
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("homework_questions.id", ondelete="CASCADE"), nullable=False)
    # chosen_answer is 0-based index matching HomeworkQuestion.choices
    chosen_answer = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=True)  # set at grading time
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    submission = relationship("Submission", back_populates="qcm_answers")
    question = relationship("HomeworkQuestion", back_populates="student_answers")

    __table_args__ = (
        UniqueConstraint("submission_id", "question_id", name="uq_submission_question_answer"),
    )


class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(10), nullable=False)
    expires_at = Column(Integer, nullable=False)
    used = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="USD")
    status = Column(String(20), default="unpaid")
    due_date = Column(Date, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("User", back_populates="invoices")

    __table_args__ = (
        CheckConstraint("status IN ('paid', 'unpaid', 'pending')", name="check_invoice_status"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True) # None means sent to all students in class
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), default="announcement") # 'announcement', 'homework', 'grade', 'attendance', 'urgent'
    sound_type = Column(String(50), default="bell") # 'bell', 'chime', 'gentle', 'alert'
    file_url = Column(Text, nullable=True) # Attached file url
    file_name = Column(String(255), nullable=True) # Attached file name
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    sender = relationship("User", foreign_keys=[sender_id])
    school_class = relationship("SchoolClass")
    reads = relationship("NotificationRead", back_populates="notification", cascade="all, delete-orphan")


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    read_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    notification = relationship("Notification", back_populates="reads")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("notification_id", "user_id", name="uq_notification_user_read"),
    )


class UserSetting(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    notification_enabled = Column(Integer, default=1) # 1=enabled, 0=disabled
    sound_enabled = Column(Integer, default=1) # 1=sound on, 0=sound off
    sound_type = Column(String(50), default="bell") # 'bell', 'chime', 'gentle', 'alert'
    sound_volume = Column(Numeric(3, 2), default=0.80) # 0.00 to 1.00
    theme = Column(String(20), default="light") # 'light', 'dark', 'system'
    language = Column(String(10), default="km") # 'km', 'en'
    email_notifications = Column(Integer, default=1)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="settings")
