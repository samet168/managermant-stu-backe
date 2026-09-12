import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from app.core.database import SessionLocal
from app.domain.models import SchoolClass, User, Enrollment, Homework, Submission

db = SessionLocal()
print("CLASSES:")
for c in db.query(SchoolClass).all():
    print(f"ID: {c.id}, Name: {c.name}, Grade: {c.grade_level}")

print("\nSTUDENTS:")
for s in db.query(User).all():
    print(f"ID: {s.id}, Name: {s.name}, Code: {s.student_code}, Role: {s.role}, Email: {s.email}")

print("\nENROLLMENTS:")
for e in db.query(Enrollment).all():
    print(f"ID: {e.id}, ClassID: {e.class_id}, StudentID: {e.student_id}, Roll: {e.roll_no}")

print("\nHOMEWORKS:")
for h in db.query(Homework).all():
    print(f"ID: {h.id}, Title: {h.title}, ClassID: {h.class_id}, Submissions: {len(h.submissions)}")

print("\nSUBMISSIONS:")
for sub in db.query(Submission).all():
    print(f"ID: {sub.id}, HwID: {sub.homework_id}, StudentID: {sub.student_id}, Score: {sub.score}, Feedback: {sub.feedback}")
