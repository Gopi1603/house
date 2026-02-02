# Suppress TensorFlow warnings
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress all TensorFlow logging (ERROR only)
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN custom operations

# Suppress Python warnings
import warnings
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Suppress TensorFlow deprecation warnings
import logging
logging.getLogger('tensorflow').setLevel(logging.ERROR)

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from services.predictor import ElectricityPredictor
from utils.validators import validate_csv_window
from utils.auth import login_required, admin_required, get_current_user_id, is_logged_in, is_admin, set_user_session, clear_user_session
import db
import pandas as pd
import io
import json
import re
from datetime import datetime

app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend/static')

# Phase 2: Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB upload limit
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

CORS(app)

# Only run initialization once (not on Flask reloader restart)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    # Initialize database on startup
    print("\n" + "="*70)
    print("INITIALIZING APPLICATION")
    print("="*70)
    db.init_db()
    db.migrate_db()  # Run migrations for existing databases
    db.create_admin_if_not_exists()

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Health checks (only on reloader restart)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    print("\n" + "="*70)
    print("RUNNING STARTUP HEALTH CHECKS")
    print("="*70)

    # Check database health
    db_health = db.check_db_health()
    if db_health['status'] == 'healthy':
        print(f"✓ Database: {db_health['status']}")
        print(f"  - Tables: {', '.join(db_health['tables'])}")
        print(f"  - Users: {db_health['user_count']}")
        print(f"  - Predictions: {db_health['prediction_count']}")
    else:
        print(f"✗ Database: {db_health['status']} - {db_health.get('error', 'Unknown error')}")

# Initialize predictor (always needed)
model_path = os.path.join(os.path.dirname(__file__), 'model')
predictor = ElectricityPredictor(model_path)

if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    # Check predictor health
    print(f"✓ Model loaded: {predictor.is_loaded()}")
    print(f"  - Lookback window: {predictor.config['lookback']} hours")
    print(f"  - Prediction horizon: {predictor.config['horizon']} hour")
    print(f"  - Features: {len(predictor.selected_features)}")

    # Check endpoints
    print("\n" + "="*70)
    print("AVAILABLE ENDPOINTS")
    print("="*70)
    print("Public Endpoints:")
    print("  ✓ GET  /                    - Main application")
    print("  ✓ POST /predict             - Make prediction")
    print("  ✓ GET  /api/health          - Health check")
    print("  ✓ GET  /api/model-metrics   - Model performance")
    print("  ✓ GET  /sample-csv          - Download sample CSV")
    print("  ✓ GET  /debug/selftest      - PRD compliance test")
    print("\nAuthentication Endpoints:")
    print("  ✓ GET/POST /register        - User registration")
    print("  ✓ GET/POST /login           - User login")
    print("  ✓ GET      /logout          - User logout")
    print("\nProtected Endpoints (Login Required):")
    print("  ✓ GET  /history             - View prediction history")
    print("  ✓ GET  /history/<id>        - View prediction details")
    print("  ✓ GET  /history/<id>/download - Download CSV")
    print("\nAdmin Endpoints (Admin Only - Phase 3):")
    print("  ✓ GET  /admin/dashboard     - Admin dashboard")
    print("  ✓ GET  /admin/users         - User management")
    print("  ✓ POST /admin/users/delete/<id> - Delete user")
    print("  ✓ GET  /admin/predictions   - Prediction monitoring")
    print("  ✓ POST /admin/predictions/delete/<id> - Delete prediction")

    print("\n" + "="*70)
    print("STARTUP COMPLETE - All Systems Ready!")
    print("="*70)
    print(f"\n🌐 Application running on: http://localhost:5000")
    print(f"📝 Admin login: admin@localhost / admin123")
    print("="*70 + "\n")

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html', 
                         logged_in=is_logged_in(),
                         is_admin=is_admin(),
                         user_email=session.get('email'))

@app.route('/favicon.ico')
def favicon():
    """Return empty response to prevent 404 errors for favicon requests"""
    return '', 204

@app.route('/predict', methods=['POST'])
def predict():
    """
    PRD-compliant endpoint for 24-hour lookback electricity prediction
    
    PRD Section 11:
    - Input vector length = 6 (5 features + target history)
    - Lookback window = 24 hours
    - Output = 1-hour ahead prediction
    
    Phase 2 Enhancement:
    - If user is logged in, saves prediction to history
    
    Expects:
    - multipart/form-data with CSV file (key: "file")
    - CSV must have exactly 24 rows
    - Required columns: Global_intensity, Sub_metering_3, Voltage,
                       Global_reactive_power, Sub_metering_2, Global_active_power
    
    Returns:
    {
        "predicted_power_kw": <float>,
        "actual_last_24h_kw": [<float>, ...],
        "predicted_next_hour_kw": <float>,
        "saved_to_history": <bool>
    }
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded. Please upload a CSV file with 24 hours of data.'}), 400
        
        file = request.files['file']
        
        # Check if filename is empty
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV file'}), 400
        
        # Read CSV file
        try:
            csv_content = file.read().decode('utf-8')
            df = pd.read_csv(io.StringIO(csv_content))
        except Exception as e:
            return jsonify({'error': f'Error reading CSV file: {str(e)}'}), 400
        
        # Validate CSV window (24 rows, correct columns, numeric values)
        is_valid, error_message, df_cleaned = validate_csv_window(
            df,
            selected_features=predictor.selected_features,
            target_col=predictor.config['target_col'],
            lookback=predictor.config['lookback']
        )
        
        if not is_valid:
            return jsonify({'error': error_message}), 400
        
        # Make prediction using 24-hour window
        result = predictor.predict_from_window(df_cleaned)
        
        # Phase 2: Save to history if user is logged in
        saved_to_history = False
        if is_logged_in():
            try:
                user_id = get_current_user_id()
                filename = secure_filename(file.filename)
                
                # Save CSV file to uploads directory
                user_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
                os.makedirs(user_upload_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_filename = f"{timestamp}_{filename}"
                csv_filepath = os.path.join(user_upload_dir, csv_filename)
                
                # Write CSV content to file
                with open(csv_filepath, 'w', encoding='utf-8') as f:
                    f.write(csv_content)
                
                # Save to database
                last24_json = json.dumps(result['actual_last_24h_kw'])
                run_id = db.save_prediction_run(
                    user_id=user_id,
                    filename=filename,
                    predicted_power_kw=result['predicted_power_kw'],
                    predicted_next_hour_kw=result['predicted_next_hour_kw'],
                    last24_json=last24_json,
                    csv_storage_type='FILE',
                    csv_file_path=csv_filepath
                )
                saved_to_history = True
            except Exception as e:
                # Don't fail prediction if history save fails
                print(f"Warning: Failed to save prediction history: {e}")
        
        # Return PRD-compliant response with history indicator
        result['saved_to_history'] = saved_to_history
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Prediction error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint"""
    # Database health
    db_health = db.check_db_health()
    
    # Model health
    model_health = {
        'loaded': predictor.is_loaded(),
        'lookback': predictor.config['lookback'],
        'features_count': len(predictor.selected_features)
    }
    
    # Overall status
    all_healthy = (
        db_health['status'] == 'healthy' and
        model_health['loaded']
    )
    
    response = {
        'status': 'healthy' if all_healthy else 'degraded',
        'timestamp': datetime.now().isoformat(),
        'database': db_health,
        'model': model_health,
        'lookback_required': predictor.config['lookback'],
        'required_columns': predictor.selected_features + [predictor.config['target_col']]
    }
    
    status_code = 200 if all_healthy else 503
    return jsonify(response), status_code

@app.route('/api/model-metrics', methods=['GET'])
def get_model_metrics():
    """
    Thesis Enhancement: Return model performance metrics for display
    Reads metrics_final.json and returns formatted metrics
    Robust fallbacks for missing fields
    """
    try:
        metrics_path = os.path.join(model_path, 'metrics_final.json')
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        
        # Defensive extraction with fallbacks
        original = metrics.get('original_kw', {})
        rmse = float(original.get('rmse', 0.0))
        mae = float(original.get('mae', 0.0))
        r2 = float(original.get('r2', 0.0))
        
        # Get features with fallback to predictor.selected_features
        features = metrics.get('selected_features')
        if not features:
            features = predictor.selected_features
        
        return jsonify({
            'rmse_kw': round(rmse, 3),
            'mae_kw': round(mae, 3),
            'r2': round(r2, 3),
            'lookback': metrics.get('lookback', 24),
            'horizon': metrics.get('horizon', 1),
            'features': features
        })
    except Exception as e:
        return jsonify({'error': f'Could not load metrics: {str(e)}'}), 500

@app.route('/api/model-metric', methods=['GET'])
def get_model_metric_alias():
    """Redirect alias for common typo: /api/model-metric → /api/model-metrics"""
    return redirect('/api/model-metrics', code=301)

@app.route('/sample-csv', methods=['GET'])
def download_sample_csv():
    """
    Thesis Enhancement: Download endpoint for sample CSV with 24 hours of data
    Returns a properly formatted CSV file
    """
    from flask import Response
    
    csv_content = """Global_intensity,Sub_metering_3,Voltage,Global_reactive_power,Sub_metering_2,Global_active_power
4.628,17.0,234.84,0.226,1.0,1.088
4.588,17.0,234.35,0.224,1.0,1.080
4.548,17.0,233.86,0.222,1.0,1.072
4.510,16.0,233.29,0.220,1.0,1.064
4.470,16.0,233.74,0.218,1.0,1.056
4.432,17.0,234.22,0.216,1.0,1.048
4.392,17.0,233.95,0.214,1.0,1.040
4.354,17.0,234.45,0.212,1.0,1.032
4.314,17.0,234.99,0.210,1.0,1.024
4.276,17.0,234.53,0.208,1.0,1.016
4.236,16.0,234.06,0.206,1.0,1.008
4.198,16.0,233.58,0.204,1.0,1.000
4.158,16.0,234.11,0.202,1.0,0.992
4.120,17.0,234.64,0.200,1.0,0.984
4.080,17.0,234.16,0.198,1.0,0.976
4.042,17.0,233.69,0.196,1.0,0.968
4.002,17.0,234.21,0.194,1.0,0.960
3.964,17.0,234.74,0.192,1.0,0.952
3.924,16.0,234.27,0.190,1.0,0.944
3.886,16.0,233.79,0.188,1.0,0.936
3.846,16.0,234.32,0.186,1.0,0.928
3.808,17.0,234.85,0.184,1.0,0.920
3.768,17.0,234.37,0.182,1.0,0.912
3.730,17.0,233.90,0.180,1.0,0.904"""
    
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=sample_24hour_data.csv'}
    )

@app.route('/debug/selftest', methods=['GET'])
def debug_selftest():
    """
    PRD COMPLIANCE SELF-TEST ENDPOINT
    
    Loads app/sample_input.csv and runs end-to-end prediction
    to verify PRD Section 11 compliance:
    - Input vector length = 6 (5 features + target history)
    - Lookback window = 24 hours
    - Output = 1-hour ahead prediction
    
    Returns:
    {
        "ok": true/false,
        "predicted_power_kw": <float>,
        "input_shape": <model shape>,
        "window_rows": 24,
        "cols": [list of columns],
        "validation": {...},
        "error": <string if failed>
    }
    """
    try:
        # Path to sample CSV
        sample_csv_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'sample_input.csv'
        )
        
        # Check if sample CSV exists
        if not os.path.exists(sample_csv_path):
            # Create sample CSV if it doesn't exist
            sample_data = """Global_intensity,Sub_metering_3,Voltage,Global_reactive_power,Sub_metering_2,Global_active_power
4.628,17.0,234.84,0.226,1.0,1.088
4.588,17.0,234.35,0.224,1.0,1.080
4.548,17.0,233.86,0.222,1.0,1.072
4.510,16.0,233.29,0.220,1.0,1.064
4.470,16.0,233.74,0.218,1.0,1.056
4.432,17.0,234.22,0.216,1.0,1.048
4.392,17.0,233.95,0.214,1.0,1.040
4.354,17.0,234.45,0.212,1.0,1.032
4.314,17.0,234.99,0.210,1.0,1.024
4.276,17.0,234.53,0.208,1.0,1.016
4.236,16.0,234.06,0.206,1.0,1.008
4.198,16.0,233.58,0.204,1.0,1.000
4.158,16.0,234.11,0.202,1.0,0.992
4.120,17.0,234.64,0.200,1.0,0.984
4.080,17.0,234.16,0.198,1.0,0.976
4.042,17.0,233.69,0.196,1.0,0.968
4.002,17.0,234.21,0.194,1.0,0.960
3.964,17.0,234.74,0.192,1.0,0.952
3.924,16.0,234.27,0.190,1.0,0.944
3.886,16.0,233.79,0.188,1.0,0.936
3.846,16.0,234.32,0.186,1.0,0.928
3.808,17.0,234.85,0.184,1.0,0.920
3.768,17.0,234.37,0.182,1.0,0.912
3.730,17.0,233.90,0.180,1.0,0.904"""
            with open(sample_csv_path, 'w') as f:
                f.write(sample_data)
        
        # Load sample CSV
        df = pd.read_csv(sample_csv_path)
        
        # Validate CSV
        is_valid, error_message, df_cleaned = validate_csv_window(
            df,
            selected_features=predictor.selected_features,
            target_col=predictor.config['target_col'],
            lookback=predictor.config['lookback']
        )
        
        if not is_valid:
            return jsonify({
                'ok': False,
                'error': f'Sample CSV validation failed: {error_message}',
                'input_shape': str(predictor.model.input_shape),
                'window_rows': len(df),
                'cols': list(df.columns)
            }), 400
        
        # Make prediction
        result = predictor.predict_from_window(df_cleaned)
        
        # Robust model shape validation
        shape = predictor.model.input_shape
        model_shape_correct = (
            shape is not None and
            len(shape) == 3 and
            shape[1] == 24 and
            shape[2] == 6
        )
        
        # Return success response with all verification data
        return jsonify({
            'ok': True,
            'predicted_power_kw': result['predicted_power_kw'],
            'input_shape': str(predictor.model.input_shape),
            'window_rows': len(df_cleaned),
            'cols': list(df_cleaned.columns),
            'validation': {
                'csv_valid': is_valid,
                'exact_24_rows': len(df_cleaned) == 24,
                'exact_6_columns': len(df_cleaned.columns) == 6,
                'model_shape_correct': model_shape_correct
            },
            'sample_csv_path': sample_csv_path,
            'actual_last_24h_kw': result['actual_last_24h_kw'][:3] + ['...'] + result['actual_last_24h_kw'][-3:]
        })
        
    except Exception as e:
        return jsonify({
            'ok': False,
            'error': str(e),
            'input_shape': str(predictor.model.input_shape) if predictor.model else 'Model not loaded'
        }), 500

@app.route('/debug/benchmark', methods=['GET'])
def debug_benchmark():
    """
    Performance benchmark endpoint - measures prediction latency
    
    Runs 10 predictions on sample data and returns timing statistics
    """
    import time
    import numpy as np
    
    try:
        # Create sample 24x6 window
        sample_data = np.array([
            [4.628, 17.0, 234.84, 0.226, 1.0, 1.088],
            [4.588, 17.0, 234.35, 0.224, 1.0, 1.080],
            [4.548, 17.0, 233.86, 0.222, 1.0, 1.072],
            [4.510, 16.0, 233.29, 0.220, 1.0, 1.064],
            [4.470, 16.0, 233.74, 0.218, 1.0, 1.056],
            [4.432, 17.0, 234.22, 0.216, 1.0, 1.048],
            [4.392, 17.0, 233.95, 0.214, 1.0, 1.040],
            [4.354, 17.0, 234.45, 0.212, 1.0, 1.032],
            [4.314, 17.0, 234.99, 0.210, 1.0, 1.024],
            [4.276, 17.0, 234.53, 0.208, 1.0, 1.016],
            [4.236, 16.0, 234.06, 0.206, 1.0, 1.008],
            [4.198, 16.0, 233.58, 0.204, 1.0, 1.000],
            [4.158, 16.0, 234.11, 0.202, 1.0, 0.992],
            [4.120, 17.0, 234.64, 0.200, 1.0, 0.984],
            [4.080, 17.0, 234.16, 0.198, 1.0, 0.976],
            [4.042, 17.0, 233.69, 0.196, 1.0, 0.968],
            [4.002, 17.0, 234.21, 0.194, 1.0, 0.960],
            [3.964, 17.0, 234.74, 0.192, 0.952, 0.952],
            [3.924, 16.0, 234.27, 0.190, 1.0, 0.944],
            [3.886, 16.0, 233.79, 0.188, 1.0, 0.936],
            [3.846, 16.0, 234.32, 0.186, 1.0, 0.928],
            [3.808, 17.0, 234.85, 0.184, 1.0, 0.920],
            [3.768, 17.0, 234.37, 0.182, 1.0, 0.912],
            [3.730, 17.0, 233.90, 0.180, 1.0, 0.904]
        ])
        
        # Create DataFrame with correct columns
        column_order = predictor.selected_features + [predictor.config['target_col']]
        df_sample = pd.DataFrame(sample_data, columns=column_order)
        
        # Warm-up run (exclude from timing)
        _ = predictor.predict_from_window(df_sample)
        
        # Benchmark runs
        num_runs = 10
        timings = []
        
        for i in range(num_runs):
            start = time.time()
            _ = predictor.predict_from_window(df_sample)
            elapsed = time.time() - start
            timings.append(elapsed)
        
        # Calculate statistics
        avg_ms = np.mean(timings) * 1000
        min_ms = np.min(timings) * 1000
        max_ms = np.max(timings) * 1000
        std_ms = np.std(timings) * 1000
        
        return jsonify({
            'benchmark': 'prediction_latency',
            'num_runs': num_runs,
            'avg_ms': round(avg_ms, 2),
            'min_ms': round(min_ms, 2),
            'max_ms': round(max_ms, 2),
            'std_ms': round(std_ms, 2),
            'prd_target_ms': 2000,
            'meets_prd': avg_ms < 2000,
            'note': 'Excludes CSV parsing and validation overhead'
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Benchmark failed: {str(e)}'
        }), 500


# ============================================================================
# PHASE 2: AUTHENTICATION ROUTES
# ============================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page and handler"""
    if request.method == 'GET':
        # Already logged in? Redirect to home
        if is_logged_in():
            return redirect(url_for('index'))
        return render_template('register.html')
    
    # POST: Handle registration
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    
    # Validation
    if not email or not password:
        flash('Email and password are required.', 'error')
        return render_template('register.html', email=email)
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        flash('Please enter a valid email address.', 'error')
        return render_template('register.html', email=email)
    
    # Password length check
    if len(password) < 6:
        flash('Password must be at least 6 characters long.', 'error')
        return render_template('register.html', email=email)
    
    # Password confirmation
    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return render_template('register.html', email=email)
    
    # Hash password
    password_hash = generate_password_hash(password)
    
    # Create user
    user_id = db.create_user(email, password_hash)
    
    if user_id is None:
        flash('Email already registered. Please log in.', 'error')
        return render_template('register.html', email=email)
    
    # Auto-login after registration (new users are never admins)
    set_user_session(user_id, email, is_admin=False)
    flash('Account created successfully! Welcome!', 'success')
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page and handler"""
    if request.method == 'GET':
        # Already logged in? Redirect to home
        if is_logged_in():
            return redirect(url_for('index'))
        return render_template('login.html')
    
    # POST: Handle login
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    
    # Validation
    if not email or not password:
        flash('Email and password are required.', 'error')
        return render_template('login.html', email=email)
    
    # Get user from database
    user = db.get_user_by_email(email)
    
    if user is None:
        flash('Invalid email or password.', 'error')
        return render_template('login.html', email=email)
    
    # Check password
    if not check_password_hash(user['password_hash'], password):
        flash('Invalid email or password.', 'error')
        return render_template('login.html', email=email)
    
    # Login successful - set session with admin flag
    # sqlite3.Row doesn't have .get() method, so access directly
    is_admin = user['is_admin'] == 1 if 'is_admin' in user.keys() else False
    set_user_session(user['id'], user['email'], is_admin)
    flash('Logged in successfully!', 'success')
    
    # Redirect to next page if specified, otherwise home
    next_page = request.args.get('next')
    if next_page:
        return redirect(next_page)
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """User logout handler"""
    clear_user_session()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))


# ============================================================================
# PHASE 2: HISTORY ROUTES
# ============================================================================

@app.route('/history')
@login_required
def history():
    """Display user's prediction history"""
    user_id = get_current_user_id()
    runs = db.get_user_prediction_runs(user_id, limit=100)
    total_count = db.get_prediction_count(user_id)
    
    return render_template('history.html', 
                         runs=runs, 
                         total_count=total_count,
                         logged_in=True,
                         is_admin=is_admin(),
                         user_email=session.get('email'))


@app.route('/history/<int:run_id>')
@login_required
def history_detail(run_id):
    """Display details of a specific prediction run"""
    user_id = get_current_user_id()
    run = db.get_prediction_run_by_id(run_id, user_id)
    
    if run is None:
        flash('Prediction not found or access denied.', 'error')
        return redirect(url_for('history'))
    
    # Parse last24_json if available
    last24_data = None
    if run['last24_json']:
        try:
            last24_data = json.loads(run['last24_json'])
        except:
            pass
    
    return render_template('history_detail.html',
                         run=run,
                         last24_data=last24_data,
                         logged_in=True,
                         is_admin=is_admin(),
                         user_email=session.get('email'))


@app.route('/history/<int:run_id>/download')
@login_required
def download_csv(run_id):
    """Download the original CSV file for a prediction run"""
    user_id = get_current_user_id()
    run = db.get_prediction_run_by_id(run_id, user_id)
    
    if run is None:
        flash('Prediction not found or access denied.', 'error')
        return redirect(url_for('history'))
    
    # Check storage type
    if run['csv_storage_type'] == 'FILE':
        # Serve file
        csv_path = run['csv_file_path']
        if not os.path.exists(csv_path):
            flash('CSV file not found on server.', 'error')
            return redirect(url_for('history_detail', run_id=run_id))
        
        return send_file(csv_path, 
                        mimetype='text/csv',
                        as_attachment=True,
                        download_name=run['filename'])
    
    elif run['csv_storage_type'] == 'TEXT':
        # Generate file from stored text
        from flask import Response
        return Response(
            run['csv_text'],
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={run["filename"]}'}
        )
    
    else:
        flash('Unknown storage type.', 'error')
        return redirect(url_for('history_detail', run_id=run_id))


# ============================================================================
# PHASE 3: ADMIN ROUTES (Monitoring & Maintenance Only - NO ML Changes)
# ============================================================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """
    Admin dashboard with system statistics.
    
    Displays:
    - Total users and predictions
    - Average predicted power
    - Latest prediction timestamp
    - System health status
    """
    stats = db.get_admin_stats()
    health = db.check_db_health()
    
    return render_template('admin_dashboard.html', 
                          stats=stats, 
                          health=health)


@app.route('/admin/users')
@admin_required
def admin_users():
    """
    Admin user management page.
    
    Shows all users with:
    - Email
    - Registration date
    - Prediction count
    - Admin status
    - Delete actions
    """
    users = db.get_all_users_admin()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """
    Delete a user and all their predictions (admin only).
    
    Security:
    - Cannot delete admin users
    - Cascade deletes all user predictions
    - Requires POST method
    """
    result = db.delete_user_admin(user_id)
    
    if result['success']:
        flash(f"User {result['email']} deleted successfully. "
              f"{result['predictions_deleted']} predictions removed.", 'success')
    else:
        flash(f"Error: {result['error']}", 'error')
    
    return redirect(url_for('admin_users'))


@app.route('/admin/predictions')
@admin_required
def admin_predictions():
    """
    Admin prediction monitoring page.
    
    Shows all predictions across all users with:
    - User email
    - Timestamp
    - Predicted power value
    - CSV download link
    - Delete actions
    """
    # Get recent predictions (last 100)
    limit = request.args.get('limit', 100, type=int)
    predictions = db.get_all_predictions_admin(limit=limit)
    
    return render_template('admin_predictions.html', 
                          predictions=predictions,
                          limit=limit)


@app.route('/admin/predictions/<int:prediction_id>')
@admin_required
def admin_prediction_detail(prediction_id):
    """
    View detailed information about a specific prediction.
    """
    prediction = db.get_prediction_by_id(prediction_id)
    
    if not prediction:
        flash('Prediction not found.', 'error')
        return redirect(url_for('admin_predictions'))
    
    return render_template('history_detail.html', 
                          run=prediction,
                          is_admin_view=True)


@app.route('/admin/predictions/delete/<int:prediction_id>', methods=['POST'])
@admin_required
def admin_delete_prediction(prediction_id):
    """
    Delete a prediction (admin only).
    
    Args:
        prediction_id: ID of prediction to delete
    
    Returns:
        Redirect to admin predictions page with status message
    """
    result = db.delete_prediction_admin(prediction_id)
    
    if result['success']:
        flash(f"Prediction #{result['prediction_id']} ({result['filename']}) deleted successfully.", 'success')
    else:
        flash(f"Error: {result['error']}", 'error')
    
    return redirect(url_for('admin_predictions'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
