from flask import Flask, request, jsonify, render_template, redirect
from flask_cors import CORS
from services.predictor import ElectricityPredictor
from utils.validators import validate_csv_window
import pandas as pd
import io
import os
import json

app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend/static')
CORS(app)

# Initialize predictor
model_path = os.path.join(os.path.dirname(__file__), 'model')
predictor = ElectricityPredictor(model_path)

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

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
    
    Expects:
    - multipart/form-data with CSV file (key: "file")
    - CSV must have exactly 24 rows
    - Required columns: Global_intensity, Sub_metering_3, Voltage,
                       Global_reactive_power, Sub_metering_2, Global_active_power
    
    Returns:
    {
        "predicted_power_kw": <float>,
        "actual_last_24h_kw": [<float>, ...],
        "predicted_next_hour_kw": <float>
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
        
        # Return PRD-compliant response
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Prediction error: {str(e)}'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': predictor.is_loaded(),
        'lookback_required': predictor.config['lookback'],
        'required_columns': predictor.selected_features + [predictor.config['target_col']]
    })

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
