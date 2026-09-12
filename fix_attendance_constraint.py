"""
Fix attendance table constraint to allow multiple subjects per day
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings

def fix_attendance_constraint():
    """
    Drop the unique constraint that prevents multiple attendance records
    for the same student on the same day for different subjects.
    """
    print("Fixing attendance table constraints...")
    
    try:
        conn = psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Drop the problematic constraint
        cur.execute("""
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'attendances_class_id_student_id_date_key'
              ) THEN
                ALTER TABLE attendances DROP CONSTRAINT attendances_class_id_student_id_date_key;
                RAISE NOTICE 'Dropped constraint: attendances_class_id_student_id_date_key';
              ELSE
                RAISE NOTICE 'Constraint attendances_class_id_student_id_date_key does not exist';
              END IF;
            END $$
        """)
        
        # Also check for other possible constraint names
        cur.execute("""
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_class_student_date_attendance'
              ) THEN
                ALTER TABLE attendances DROP CONSTRAINT uq_class_student_date_attendance;
                RAISE NOTICE 'Dropped constraint: uq_class_student_date_attendance';
              ELSE
                RAISE NOTICE 'Constraint uq_class_student_date_attendance does not exist';
              END IF;
            END $$
        """)
        
        cur.close()
        conn.close()
        print("✓ Attendance table constraints fixed successfully!")
        
    except Exception as e:
        print(f"✗ Failed to fix constraints: {e}")
        raise

if __name__ == "__main__":
    fix_attendance_constraint()
