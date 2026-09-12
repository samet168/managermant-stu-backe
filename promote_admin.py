import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from app.core.database import SessionLocal
from app.domain.models import User, SchoolClass, Enrollment

db = SessionLocal()
samet = db.query(User).filter(User.email.ilike("%samet.moeun88%")).first()
if samet:
    samet.role = "admin"
    db.commit()
    print(f"Updated user {samet.name} ({samet.email}) to role: {samet.role}")

print("\nCURRENT USERS & ROLES:")
for u in db.query(User).all():
    print(f"ID: {u.id}, Name: {u.name}, Email: {u.email}, Role: {u.role}, Code: {u.student_code}")
