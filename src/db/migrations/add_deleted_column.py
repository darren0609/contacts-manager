import sqlite3

def migrate():
    # Connect to the database
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()
    
    try:
        # Add the deleted column
        cursor.execute("ALTER TABLE contacts ADD COLUMN deleted BOOLEAN DEFAULT 0")
        conn.commit()
        print("Added 'deleted' column to contacts table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column 'deleted' already exists")
        else:
            raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate() 