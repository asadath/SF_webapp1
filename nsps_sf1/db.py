import os
import sqlite3

SYSTEM_NAME = "NSPS_SF1"

# Each app has its own database (bidirectional CDC with 2 separate data stores)
_db_path = os.path.join(os.path.dirname(__file__), "nsps_sf1_accounts.db")
conn = sqlite3.connect(_db_path, check_same_thread=False)
cursor = conn.cursor()


def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts(
        account_id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        phone TEXT,
        source_system TEXT,
        created_by TEXT
    )
    """)
    # Add created_by column if table already existed without it
    try:
        cursor.execute("ALTER TABLE accounts ADD COLUMN created_by TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()


def insert_account(account_id, first, last, email, phone, source, created_by="database"):

    cursor.execute("""
    INSERT OR IGNORE INTO accounts
    (account_id, first_name, last_name, email, phone, source_system, created_by)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        account_id,
        first,
        last,
        email,
        phone,
        source,
        created_by,
    ))

    conn.commit()


def get_accounts():
    cursor.execute("SELECT * FROM accounts")
    return cursor.fetchall()


def get_account(account_id):
    cursor.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
    row = cursor.fetchone()
    return row


def update_account(account_id, first, last, email, phone, source_system=None, created_by=None):
    if source_system is not None and created_by is not None:
        cursor.execute("""
        UPDATE accounts
        SET first_name = ?, last_name = ?, email = ?, phone = ?, source_system = ?, created_by = ?
        WHERE account_id = ?
        """, (first, last, email, phone, source_system, created_by, account_id))
    else:
        cursor.execute("""
        UPDATE accounts
        SET first_name = ?, last_name = ?, email = ?, phone = ?
        WHERE account_id = ?
        """, (first, last, email, phone, account_id))
    conn.commit()


def delete_account(account_id):
    cursor.execute("DELETE FROM accounts WHERE account_id = ?", (account_id,))
    conn.commit()