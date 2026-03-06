import sqlite3

SYSTEM_NAME = "NSPS_SF1"

conn = sqlite3.connect("accounts.db", check_same_thread=False)
cursor = conn.cursor()


def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts(
        account_id TEXT PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        email TEXT,
        phone TEXT,
        source_system TEXT
    )
    """)
    conn.commit()


def insert_account(account_id, first, last, email, phone, source):

    cursor.execute("""
    INSERT OR IGNORE INTO accounts
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        account_id,
        first,
        last,
        email,
        phone,
        source
    ))

    conn.commit()


def get_accounts():
    cursor.execute("SELECT * FROM accounts")
    return cursor.fetchall()