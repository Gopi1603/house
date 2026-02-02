"""
Authentication utilities for Phase 2

Provides:
- Login required decorator
- Helper functions for session management
"""

from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """
    Decorator to protect routes that require authentication.
    
    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            # user_id is available in session
            return "Protected content"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to protect routes that require admin privileges.
    Checks both authentication AND admin status.
    
    Usage:
        @app.route('/admin/dashboard')
        @admin_required
        def admin_dashboard():
            return "Admin content"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # First check if logged in
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        # Then check if admin
        if not session.get('is_admin', False):
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def get_current_user_id():
    """
    Get the current logged-in user's ID from session.
    
    Returns:
        user_id (int) or None if not logged in
    """
    return session.get('user_id')


def is_logged_in():
    """
    Check if a user is currently logged in.
    
    Returns:
        True if logged in, False otherwise
    """
    return 'user_id' in session


def is_admin():
    """
    Check if the current logged-in user is an admin.
    
    Returns:
        True if logged in AND is_admin, False otherwise
    """
    return is_logged_in() and session.get('is_admin', False)


def set_user_session(user_id, email, is_admin=False):
    """
    Set session data for a logged-in user.
    
    Args:
        user_id: User's database ID
        email: User's email address
        is_admin: Whether user has admin privileges (default: False)
    """
    session['user_id'] = user_id
    session['email'] = email
    session['is_admin'] = is_admin


def clear_user_session():
    """
    Clear all session data (logout).
    """
    session.clear()
