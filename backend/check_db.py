"""
Simple database inspection tool for Phase 2
Run this script to view database contents
"""

import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'app.db')

def check_database():
    """Check if database exists and show basic info"""
    if not os.path.exists(DB_PATH):
        print("❌ Database not found!")
        print(f"Expected location: {DB_PATH}")
        print("\nRun the Flask app first to create the database:")
        print("  python app.py")
        return
    
    print("✅ Database found!")
    print(f"Location: {DB_PATH}")
    print(f"Size: {os.path.getsize(DB_PATH):,} bytes")
    print()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Show tables
    print("=" * 60)
    print("DATABASE TABLES")
    print("=" * 60)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  📋 {table[0]}")
    print()
    
    # Show users
    print("=" * 60)
    print("USERS TABLE")
    print("=" * 60)
    cursor.execute("SELECT id, email, created_at FROM users")
    users = cursor.fetchall()
    if users:
        print(f"{'ID':<5} {'Email':<30} {'Created At':<20}")
        print("-" * 60)
        for user in users:
            print(f"{user[0]:<5} {user[1]:<30} {user[2]:<20}")
        print(f"\nTotal users: {len(users)}")
    else:
        print("No users registered yet.")
    print()
    
    # Show prediction runs
    print("=" * 60)
    print("PREDICTION RUNS TABLE")
    print("=" * 60)
    cursor.execute("""
        SELECT pr.id, u.email, pr.filename, pr.predicted_power_kw, pr.created_at
        FROM prediction_runs pr
        JOIN users u ON pr.user_id = u.id
        ORDER BY pr.created_at DESC
        LIMIT 10
    """)
    runs = cursor.fetchall()
    if runs:
        print(f"{'ID':<5} {'User':<25} {'Filename':<20} {'kW':<8} {'Date':<20}")
        print("-" * 80)
        for run in runs:
            print(f"{run[0]:<5} {run[1]:<25} {run[2]:<20} {run[3]:<8.3f} {run[4]:<20}")
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM prediction_runs")
        total = cursor.fetchone()[0]
        print(f"\nShowing last 10 of {total} total predictions")
    else:
        print("No predictions saved yet.")
    print()
    
    # Statistics
    print("=" * 60)
    print("STATISTICS")
    print("=" * 60)
    cursor.execute("""
        SELECT u.email, COUNT(pr.id) as count
        FROM users u
        LEFT JOIN prediction_runs pr ON u.id = pr.user_id
        GROUP BY u.id
    """)
    stats = cursor.fetchall()
    if stats:
        print(f"{'User':<30} {'Predictions':<15}")
        print("-" * 45)
        for stat in stats:
            print(f"{stat[0]:<30} {stat[1]:<15}")
    print()
    
    conn.close()


def show_schema():
    """Show database schema"""
    if not os.path.exists(DB_PATH):
        print("❌ Database not found!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("DATABASE SCHEMA")
    print("=" * 60)
    
    # Get schema for each table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\n📋 Table: {table_name}")
        print("-" * 60)
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print(f"{'Column':<20} {'Type':<15} {'Nullable':<10} {'Default':<15}")
        print("-" * 60)
        for col in columns:
            nullable = "NULL" if col[3] == 0 else "NOT NULL"
            default = col[4] if col[4] else ""
            print(f"{col[1]:<20} {col[2]:<15} {nullable:<10} {default:<15}")
    
    print()
    conn.close()


def clear_database():
    """Clear all data from database (DANGER!)"""
    if not os.path.exists(DB_PATH):
        print("❌ Database not found!")
        return
    
    response = input("⚠️  WARNING: This will delete ALL data! Are you sure? (type 'yes' to confirm): ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM prediction_runs")
    cursor.execute("DELETE FROM users")
    conn.commit()
    
    print("✅ Database cleared!")
    conn.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'schema':
            show_schema()
        elif command == 'clear':
            clear_database()
        else:
            print("Unknown command!")
            print("Usage:")
            print("  python check_db.py          # Show database contents")
            print("  python check_db.py schema   # Show table schemas")
            print("  python check_db.py clear    # Clear all data (DANGER!)")
    else:
        check_database()
