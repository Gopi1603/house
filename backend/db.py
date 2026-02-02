"""
Database module for Phase 2: Authentication + SQLite Persistence

Handles:
- SQLite connection management
- Schema creation and initialization
- User authentication queries
- Prediction history storage and retrieval
"""

import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

# Database file path
DB_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_PATH = os.path.join(DB_DIR, 'app.db')


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable dict-like row access
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """
    Initialize database schema.
    Creates tables if they don't exist.
    Safe to call multiple times (idempotent).
    """
    # Create data directory if it doesn't exist
    os.makedirs(DB_DIR, exist_ok=True)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create prediction_runs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prediction_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                filename TEXT NOT NULL,
                model_name TEXT DEFAULT 'bilstm',
                predicted_power_kw REAL NOT NULL,
                predicted_next_hour_kw REAL NOT NULL,
                last24_json TEXT,
                csv_storage_type TEXT DEFAULT 'FILE',
                csv_text TEXT,
                csv_file_path TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prediction_runs_user_id 
            ON prediction_runs(user_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prediction_runs_created_at 
            ON prediction_runs(created_at DESC)
        ''')
        
        conn.commit()
        print(f"✓ Database initialized at: {DB_PATH}")


def migrate_db():
    """
    Run database migrations to update existing schema.
    Adds missing columns if database exists from older version.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if is_admin column exists in users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_admin' not in columns:
            print("⚙️  Running migration: Adding is_admin column...")
            cursor.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
            conn.commit()
            print("✓ Migration complete: is_admin column added")


def create_admin_if_not_exists():
    """
    Create default admin user if no admin exists.
    Admin credentials: admin@localhost / admin123
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if admin exists
        cursor.execute('SELECT id FROM users WHERE is_admin = 1')
        admin = cursor.fetchone()
        
        if admin is None:
            # Import here to avoid circular dependency
            from werkzeug.security import generate_password_hash
            
            # Create admin user
            admin_email = 'admin@localhost'
            admin_password = 'admin123'
            password_hash = generate_password_hash(admin_password)
            
            cursor.execute(
                'INSERT INTO users (email, password_hash, is_admin) VALUES (?, ?, 1)',
                (admin_email, password_hash)
            )
            conn.commit()
            print(f"✓ Admin user created: {admin_email} / {admin_password}")
        else:
            print(f"✓ Admin user already exists")


# ============================================================================
# USER AUTHENTICATION QUERIES
# ============================================================================

def create_user(email, password_hash):
    """
    Create a new user account.
    
    Args:
        email: User's email address (must be unique)
        password_hash: Hashed password (never store plain password)
    
    Returns:
        user_id if success, None if email already exists
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (email, password_hash) VALUES (?, ?)',
                (email, password_hash)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Email already exists
        return None


def get_user_by_email(email):
    """
    Retrieve user by email address.
    
    Args:
        email: User's email address
    
    Returns:
        dict-like Row object with user data, or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, email, password_hash, is_admin, created_at FROM users WHERE email = ?',
            (email,)
        )
        return cursor.fetchone()


def get_user_by_id(user_id):
    """
    Retrieve user by ID.
    
    Args:
        user_id: User's ID
    
    Returns:
        dict-like Row object with user data, or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, email, created_at FROM users WHERE id = ?',
            (user_id,)
        )
        return cursor.fetchone()


# ============================================================================
# PREDICTION HISTORY QUERIES
# ============================================================================

def save_prediction_run(user_id, filename, predicted_power_kw, predicted_next_hour_kw,
                       last24_json=None, csv_storage_type='FILE', 
                       csv_text=None, csv_file_path=None):
    """
    Save a prediction run to database.
    
    Args:
        user_id: ID of user who made the prediction
        filename: Original CSV filename
        predicted_power_kw: Predicted power in kW
        predicted_next_hour_kw: Same as predicted_power_kw (for compatibility)
        last24_json: Optional JSON string of last 24 hours data
        csv_storage_type: 'FILE' or 'TEXT'
        csv_text: CSV content as text (if storage_type is TEXT)
        csv_file_path: Path to saved CSV file (if storage_type is FILE)
    
    Returns:
        run_id of created record
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO prediction_runs 
            (user_id, filename, predicted_power_kw, predicted_next_hour_kw,
             last24_json, csv_storage_type, csv_text, csv_file_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, filename, predicted_power_kw, predicted_next_hour_kw,
              last24_json, csv_storage_type, csv_text, csv_file_path))
        conn.commit()
        return cursor.lastrowid


def get_user_prediction_runs(user_id, limit=100):
    """
    Get all prediction runs for a user, newest first.
    
    Args:
        user_id: User's ID
        limit: Maximum number of records to return
    
    Returns:
        List of dict-like Row objects
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, created_at, filename, model_name, 
                   predicted_power_kw, predicted_next_hour_kw
            FROM prediction_runs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        return cursor.fetchall()


def get_prediction_run_by_id(run_id, user_id):
    """
    Get a specific prediction run by ID.
    Only returns if the run belongs to the specified user (ownership check).
    
    Args:
        run_id: Prediction run ID
        user_id: User ID (for ownership verification)
    
    Returns:
        dict-like Row object, or None if not found or user doesn't own it
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, user_id, created_at, filename, model_name,
                   predicted_power_kw, predicted_next_hour_kw, last24_json,
                   csv_storage_type, csv_text, csv_file_path
            FROM prediction_runs
            WHERE id = ? AND user_id = ?
        ''', (run_id, user_id))
        return cursor.fetchone()


def get_prediction_count(user_id):
    """
    Get total number of predictions for a user.
    
    Args:
        user_id: User's ID
    
    Returns:
        Integer count
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM prediction_runs WHERE user_id = ?',
            (user_id,)
        )
        result = cursor.fetchone()
        return result[0] if result else 0


def check_db_health():
    """
    Check database health and return status.
    
    Returns:
        dict with health status
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Check if tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Count records
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM prediction_runs")
            prediction_count = cursor.fetchone()[0]
            
            return {
                'status': 'healthy',
                'tables': tables,
                'user_count': user_count,
                'prediction_count': prediction_count,
                'db_path': DB_PATH
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

# ============================================================================
# ADMIN QUERIES (Phase 3)
# ============================================================================

def get_admin_stats():
    """
    Get system statistics for admin dashboard.
    
    Returns:
        dict with system stats
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Total users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        # Total predictions
        cursor.execute('SELECT COUNT(*) FROM prediction_runs')
        total_predictions = cursor.fetchone()[0]
        
        # Average predicted power
        cursor.execute('SELECT AVG(predicted_power_kw) FROM prediction_runs')
        avg_power = cursor.fetchone()[0] or 0.0
        
        # Latest prediction timestamp
        cursor.execute('SELECT MAX(created_at) FROM prediction_runs')
        latest_prediction = cursor.fetchone()[0]
        
        # Admins count
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
        admin_count = cursor.fetchone()[0]
        
        return {
            'total_users': total_users,
            'total_predictions': total_predictions,
            'avg_power_kw': round(avg_power, 3),
            'latest_prediction': latest_prediction,
            'admin_count': admin_count
        }


def get_all_users_admin():
    """
    Get all users with prediction counts (admin only).
    
    Returns:
        list of user dicts with prediction counts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                u.id,
                u.email,
                u.is_admin,
                u.created_at,
                COUNT(p.id) as prediction_count
            FROM users u
            LEFT JOIN prediction_runs p ON u.id = p.user_id
            GROUP BY u.id
            ORDER BY u.created_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_all_predictions_admin(limit=100):
    """
    Get all predictions across all users (admin only).
    
    Args:
        limit: Maximum number of predictions to return
    
    Returns:
        list of prediction dicts with user info
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                p.id,
                p.user_id,
                u.email as user_email,
                p.created_at,
                p.filename,
                p.predicted_power_kw,
                p.csv_file_path
            FROM prediction_runs p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.created_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_all_prediction_runs_admin(limit=100):
    """
    Get all prediction runs with user info (admin only).
    
    Args:
        limit: Maximum number of runs to return
    
    Returns:
        list of prediction dicts with user info
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                p.id,
                p.user_id,
                u.email as user_email,
                p.created_at,
                p.filename,
                p.model_name,
                p.predicted_power_kw,
                p.csv_file_path,
                p.csv_storage_type
            FROM prediction_runs p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.created_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_prediction_run_by_id_admin(run_id):
    """
    Get a specific prediction run by ID (admin only, no user restriction).
    
    Args:
        run_id: Prediction run ID
    
    Returns:
        dict-like Row object with user info, or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.id, p.user_id, u.email as user_email, p.created_at, 
                   p.filename, p.model_name, p.predicted_power_kw, 
                   p.predicted_next_hour_kw, p.last24_json,
                   p.csv_storage_type, p.csv_text, p.csv_file_path
            FROM prediction_runs p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
        ''', (run_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_total_prediction_count_admin():
    """
    Get total number of predictions across all users.
    
    Returns:
        Integer count
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM prediction_runs')
        result = cursor.fetchone()
        return result[0] if result else 0


def get_unique_users_with_predictions():
    """
    Get count of unique users who have made predictions.
    
    Returns:
        Integer count
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM prediction_runs')
        result = cursor.fetchone()
        return result[0] if result else 0


def delete_user_admin(user_id):
    """
    Delete a user and all their predictions (admin only).
    WARNING: This is a destructive operation!
    
    Args:
        user_id: ID of user to delete
    
    Returns:
        dict with success status and counts
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if user is admin (can't delete admins)
        cursor.execute('SELECT is_admin, email FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        if user['is_admin']:
            return {'success': False, 'error': 'Cannot delete admin users'}
        
        # Count predictions to be deleted
        cursor.execute('SELECT COUNT(*) FROM prediction_runs WHERE user_id = ?', (user_id,))
        prediction_count = cursor.fetchone()[0]
        
        # Delete predictions first (foreign key constraint)
        cursor.execute('DELETE FROM prediction_runs WHERE user_id = ?', (user_id,))
        
        # Delete user
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        
        return {
            'success': True,
            'email': user['email'],
            'predictions_deleted': prediction_count
        }


def delete_prediction_admin(prediction_id):
    """
    Delete a prediction (admin only).
    
    Args:
        prediction_id: ID of prediction to delete
    
    Returns:
        dict with success status
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get prediction details before deleting
        cursor.execute('''
            SELECT p.id, p.filename, u.email
            FROM prediction_runs p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
        ''', (prediction_id,))
        prediction = cursor.fetchone()
        
        if not prediction:
            return {'success': False, 'error': 'Prediction not found'}
        
        # Delete prediction
        cursor.execute('DELETE FROM prediction_runs WHERE id = ?', (prediction_id,))
        conn.commit()
        
        return {
            'success': True,
            'prediction_id': prediction['id'],
            'filename': prediction['filename'],
            'user_email': prediction['email']
        }