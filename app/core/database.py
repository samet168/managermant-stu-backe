from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings
from app.domain.models import Base

# ── Engine ───────────────────────────────────────────────────────────────────
db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_connection():
    """Raw psycopg2 connection with RealDictCursor (kept for backward compat)."""
    conn = psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)
    conn.autocommit = True
    return conn


def init_db():
    """
    1. Create all tables that don't exist yet (SQLAlchemy metadata).
    2. Apply incremental ALTER TABLE migrations so old databases are
       brought up to the current schema without data loss.
    Each ALTER is wrapped in its own try/except so one failure
    doesn't abort the rest.
    """
    # ── Step 1: create new tables ────────────────────────────────────────────
    Base.metadata.create_all(bind=engine)

    # ── Step 2: incremental column / constraint migrations ───────────────────
    migrations = [
        # users ---------------------------------------------------------------
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS hashed_password VARCHAR(255)",

        # attendances — new columns -------------------------------------------
        "ALTER TABLE attendances ADD COLUMN IF NOT EXISTS subject VARCHAR(100) DEFAULT 'ទូទៅ'",
        "ALTER TABLE attendances ADD COLUMN IF NOT EXISTS teacher_id INTEGER REFERENCES users(id) ON DELETE SET NULL",

        # attendances — drop old unique constraint that blocks multi-subject rows
        # (new schema has no unique constraint on attendance — subject differentiates rows)
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'uq_class_student_date_attendance'
          ) THEN
            ALTER TABLE attendances DROP CONSTRAINT uq_class_student_date_attendance;
          END IF;
        END $$
        """,
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = 'attendances_class_id_student_id_date_key'
          ) THEN
            ALTER TABLE attendances DROP CONSTRAINT attendances_class_id_student_id_date_key;
          END IF;
        END $$
        """,

        # invoices — rename amount → total_amount if old column still exists --
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='invoices' AND column_name='amount'
          ) AND NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='invoices' AND column_name='total_amount'
          ) THEN
            ALTER TABLE invoices RENAME COLUMN amount TO total_amount;
          END IF;
        END $$
        """,
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS total_amount NUMERIC(10,2)",
        "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS paid_amount  NUMERIC(10,2) DEFAULT 0.00",

        # class_subjects — created by SQLAlchemy above; ensure FK indexes -----
        "CREATE INDEX IF NOT EXISTS ix_class_subjects_class_id   ON class_subjects(class_id)",
        "CREATE INDEX IF NOT EXISTS ix_class_subjects_teacher_id ON class_subjects(teacher_id)",

        # homework_questions / student_answers — created by SQLAlchemy --------
        "ALTER TABLE homeworks ADD COLUMN IF NOT EXISTS is_qcm BOOLEAN DEFAULT FALSE",
        "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS student_note TEXT",
    ]

    conn = get_db_connection()
    cur  = conn.cursor()
    for sql in migrations:
        try:
            cur.execute(sql)
        except Exception as exc:
            # Log but continue — some statements may fail on already-applied migrations
            print(f"[MIGRATION WARN] {exc}")
    cur.close()
    conn.close()

    print("[DB OK] PostgreSQL schema verified and migrations applied.")


if __name__ == "__main__":
    init_db()
