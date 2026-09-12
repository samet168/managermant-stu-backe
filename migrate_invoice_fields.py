"""
Migration script to update Invoice model fields:
- Rename 'amount' to 'total_amount'
- Add 'paid_amount' field with default 0.00
- For existing paid invoices, set paid_amount = total_amount
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings

def migrate_invoice_fields():
    """
    Migrate Invoice model from single 'amount' field to 'total_amount' and 'paid_amount' fields.
    """
    print("Starting Invoice field migration...")
    
    try:
        conn = psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check if amount column exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'invoices' AND column_name = 'amount'
        """)
        amount_exists = cur.fetchone()
        
        if amount_exists:
            print("Found existing 'amount' column. Migrating data...")
            
            # Step 1: Add new columns if they don't exist
            cur.execute("""
                ALTER TABLE invoices ADD COLUMN IF NOT EXISTS total_amount NUMERIC(10, 2);
                ALTER TABLE invoices ADD COLUMN IF NOT EXISTS paid_amount NUMERIC(10, 2) DEFAULT 0.00;
            """)
            print("Added new columns total_amount and paid_amount")
            
            # Step 2: Migrate data from amount to total_amount
            cur.execute("""
                UPDATE invoices 
                SET total_amount = amount 
                WHERE total_amount IS NULL AND amount IS NOT NULL
            """)
            print(f"Migrated {cur.rowcount} records from amount to total_amount")
            
            # Step 3: Set paid_amount for paid invoices
            cur.execute("""
                UPDATE invoices 
                SET paid_amount = total_amount 
                WHERE status = 'paid' AND paid_amount = 0
            """)
            print(f"Updated {cur.rowcount} paid invoices with paid_amount")
            
            # Step 4: Drop the old amount column
            cur.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS amount")
            print("Dropped old 'amount' column")
            
        else:
            print("No 'amount' column found. Invoice table already migrated.")
            # Just ensure the new columns exist
            cur.execute("""
                ALTER TABLE invoices ADD COLUMN IF NOT EXISTS total_amount NUMERIC(10, 2);
                ALTER TABLE invoices ADD COLUMN IF NOT EXISTS paid_amount NUMERIC(10, 2) DEFAULT 0.00;
            """)
            print("Ensured new columns exist")
        
        cur.close()
        conn.close()
        print("Invoice field migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_invoice_fields()
