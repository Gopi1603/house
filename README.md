# Residential Electricity Consumption Forecasting Web Application

A Flask-based web application for forecasting short-term residential electricity consumption using a **CNN-BiLSTM with Self-Attention** deep learning model trained on the UCI Individual Household Electric Power Consumption dataset.

## 📋 Overview

This application implements a complete end-to-end pipeline from data preprocessing and model training (Kaggle) to production-ready inference with a professional web interface. It provides **1-hour ahead electricity consumption predictions** based on a 24-hour lookback window.

### Key Features
- ✅ **24-Hour CSV Upload**: Upload CSV with 24 hours of historical data
- ✅ **Real-time Predictions**: Get instant next-hour consumption forecasts
- ✅ **Model Metrics Dashboard**: View RMSE, MAE, R² performance metrics
- ✅ **Interactive Charts**: Professional Chart.js visualizations
- ✅ **Thesis Figures Gallery**: Browse model comparison and performance charts
- ✅ **PRD Compliance**: Strict validation following PRD Section 11 requirements
- ✅ **Robust Error Handling**: Comprehensive validation and error messages

## 📁 Project Structure

```
app/
├── PRD.md                          # Product Requirements Document
├── README.md                       # This file
├── sample_input.csv                # Sample 24-hour test data
├── backend/
│   ├── app.py                      # Flask application with all API endpoints
│   ├── requirements.txt            # Python dependencies
│   ├── model/                      # Model artifacts (from Kaggle)
│   │   ├── final_model.keras       # CNN-BiLSTM-SA trained model
│   │   ├── scaler.pkl              # MinMaxScaler (6 features)
│   │   ├── config.json             # Model configuration (lookback=24, horizon=1)
│   │   ├── selected_features.json  # 5 selected features via MI analysis
│   │   └── metrics_final.json      # Model performance metrics
│   ├── services/
│   │   ├── predictor.py            # ElectricityPredictor class
│   │   └── custom_layers.py        # SelfAttention layer implementation
│   └── utils/
│       └── validators.py           # CSV validation (24 rows, 6 columns)
└── frontend/
    ├── templates/
    │   └── index.html              # Main web UI with metrics & gallery
    └── static/
        ├── style.css               # Professional styling
        ├── app.js                  # Frontend logic with Chart.js
        └── thesis_figures/         # Model comparison & performance figures
            ├── Fig_Model_Comparison_Table.png
            ├── Fig_Feature_MI_Ranking.png
            ├── Fig_Actual_vs_Pred_kW_First300.png
            ├── Fig_Scatter_Pred_vs_Actual_kW.png
            ├── Fig_Residuals_Hist_kW.png
            ├── Fig_Residuals_Time_kW.png
            ├── Fig_Compare_RMSE_kW.png
            ├── Fig_Compare_MAE_kW.png
            ├── Fig_Compare_R2_kW.png
            └── Fig_Loss_CNN_BiLSTM_SA.png
```

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.12** (or 3.10+)
- **pip** (latest version recommended)
- **Git** (for cloning)

### Installation Steps

#### 1. Navigate to the Backend Directory
```bash
cd app/backend
```

#### 2. Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows (Git Bash/PowerShell):
source venv/Scripts/activate
# Or on Windows (CMD):
venv\Scripts\activate.bat

# On macOS/Linux:
source venv/bin/activate
```

#### 3. Install All Dependencies
```bash
pip install -r requirements.txt
```

**Note:** This will install:
- Flask 2.3.3 (web framework)
- TensorFlow 2.20.0 (deep learning)
- pandas 3.0.0 (data processing)
- scikit-learn 1.6.1 (preprocessing)
- NumPy 2.1.3 (numerical computing)
- And other required packages

#### 4. Verify Model Artifacts
Ensure these files exist in `backend/model/`:
- ✅ `final_model.keras` (trained CNN-BiLSTM-SA model)
- ✅ `scaler.pkl` (MinMaxScaler for 6 features)
- ✅ `config.json` (lookback=24, horizon=1, target_col)
- ✅ `selected_features.json` (5 selected features)
- ✅ `metrics_final.json` (RMSE, MAE, R² metrics)

#### 5. Verify Thesis Figures (Optional)
Check `frontend/static/thesis_figures/` for PNG files (used in gallery).

---

## ▶️ Running the Application

### Start the Flask Server

```bash
cd app/backend
python app.py
```

**Expected Output:**
```
SCALER VERIFY: <class 'sklearn.preprocessing._data.MinMaxScaler'>
SCALER n_features_in_: 6

============================================================
PRD COMPLIANCE VERIFICATION - MODEL INPUT SHAPE
============================================================
Model Input Shape: (None, 24, 6)
Expected Shape: (None, 24, 6)
✓ PASS: Model shape matches PRD Section 11 requirements
============================================================

Model artifacts loaded successfully
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.0.X:5000
Press CTRL+C to quit
```

### Access the Application

1. **Open your web browser**
2. **Navigate to:** `http://localhost:5000` or `http://127.0.0.1:5000`
3. **You should see:** The main prediction interface with model metrics

---

## 📖 How to Use

### Method 1: Upload CSV File

1. **Prepare CSV with 24 rows** (exactly 24 hours of historical data)
2. **Required columns** (6 total):
   - `Global_intensity`
   - `Sub_metering_3`
   - `Voltage`
   - `Global_reactive_power`
   - `Sub_metering_2`
   - `Global_active_power` (target column)

3. **Example CSV format:**
   ```csv
   Global_intensity,Sub_metering_3,Voltage,Global_reactive_power,Sub_metering_2,Global_active_power
   4.628,17.0,234.84,0.226,1.0,1.088
   4.588,17.0,234.35,0.224,1.0,1.080
   ... (22 more rows for total of 24)
   ```

4. **Click "Choose File"** and select your CSV
5. **Click "Predict Next Hour"**
6. **View results:**
   - Predicted consumption (kW)
   - Historical data chart (24 hours)
   - Prediction point marked with star ⭐

### Method 2: Download Sample CSV

1. Click **"Download Sample CSV"** button on the web page
2. Modify values in the CSV (keep 24 rows!)
3. Upload the modified CSV
4. Get prediction

---

## 🔌 API Endpoints

### `GET /`
**Description:** Main web interface with prediction form and metrics dashboard

**Response:** HTML page

---

### `POST /predict`
**Description:** Upload CSV with 24-hour window and get next-hour prediction

**Request:** `multipart/form-data` with file upload
- Key: `file`
- Value: CSV file with 24 rows, 6 columns

**CSV Requirements:**
- Exactly **24 rows** (24-hour lookback)
- Exactly **6 columns**: `Global_intensity`, `Sub_metering_3`, `Voltage`, `Global_reactive_power`, `Sub_metering_2`, `Global_active_power`
- All values must be numeric

**Response (Success):**
```json
{
  "predicted_power_kw": 0.519,
  "actual_last_24h_kw": [1.088, 1.080, ..., 0.904],
  "predicted_next_hour_kw": 0.519
}
```

**Response (Error):**
```json
{
  "error": "CSV must have exactly 24 rows (24-hour window). Found 20 rows."
}
```

---

### `GET /api/health`
**D🎯 Model Information

### Architecture: CNN-BiLSTM with Self-Attention

**Pipeline:**
1. **Conv1D** → Local temporal feature extraction
2. **BiLSTM** → Long-term temporal dependencies (forward + backward)
3. **Self-Attention** → Important timestep weighting
4. **Dense** → Regression output (1-hour prediction)

### Model Performance (on Test Set)

| Metric | Value |
|--------|-------|
| **RMSE** | 0.465 kW |
| **MAE** | 0.328 kW |
| **R²** | 0.562 |

### Dataset: UCI Individual Household Electric Power Consumption
- **Duration:** Dec 2006 – Nov 2010
- **Sampling:** 1-minute data → resampled to **hourly**
- **Training:** Performed on Kaggle with GPU acceleration

### Selected Features (via Mutual Information Analysis)

1. **Global_intensity** - Overall intensity measurement
2. **Sub_metering_3** - Electric water heater and air conditioner
3. **Voltage** - Voltage level
4. **Global_reactive_power** - Reactive power
5. **Sub_metering_2** - Laundry room (washing machine, dryer)

**Plus target:**
- **Global_active_power** - Total active power (kW) - prediction target

### PRD Compliance (Section 11)
- ✅ Input vector length = **6** (5 features + 1 target history)
- ✅ Lookback window = **24 hours**
- ✅ Output = **1-hour ahead prediction**
- ✅ Model shape = `(None, 24, 6)` ✓ VERIFIED at startup

---

### `GET /api/model-metrics`
**Description:** Get model performance metrics for display

**Response:**
```json
{
  "rmse_kw": 0.465,
  "mae_kw": 0.328,
  "r2": 0.563,
  "lookback": 24,
  "horizon": 1,
  "features": [
    "Global_intensity",
    "Sub_metering_3",
    "Voltage",
    "Global_reactive_power",
    "Sub_metering_2"
  ]
}
```

**Note:** Also accessible via typo-tolerant alias `/api/model-metric` (without 's')

---

### `GET /sample-csv`
**Description:** Download sample CSV file with 24 hours of valid test data

**Response:** CSV file download (`sample_24hour_data.csv`)

---

### `GET /debug/selftest`
**Description:** Automated PRD compliance verification endpoint

**Response:**
```json
{
  "ok": true,
  "predicted_power_kw": 0.519,
  "input_shape": "(None, 24, 6)",
  "window_rows": 24,
  "cols": ["Global_intensity", "Sub_metering_3", "Voltage", "Global_reactive_power", "Sub_metering_2", "Global_active_power"],
  "validation": {
    "csv_valid": true,
    "exact_24_rows": true,
    "exact_6_columns": true,
    "model_shape_correct": true
  },
  "sample_csv_path": "C:\\...\\app\\sample_input.csv",
  "actual_last_24h_kw": [1.088, 1.080, 1.072, "...", 0.920, 0.912, 0.904]
}
```

---🧪 Testing the Application

### Test Health Endpoint
```bash
curl http://localhost:5000/api/health
```

### Test Model Metrics
```bash
curl http://localhost:5000/api/model-metrics
```

### Test Self-Test Endpoint (PRD Compliance)
```bash
curl http://localhost:5000/debug/selftest
```

### Test Prediction with Python
```python
import requests

# Using sample CSV
url = 'http://localhost:5000/predict'
files = {'file': open('sample_input.csv', 'rb')}
response = requests.post(url, files=files)
print(response.json())
```

### Test Prediction with cURL
```bash
curl -X POST http://localhost:5000/predict \
  -F "file=@sample_input.csv"
```

---

## 🐛 Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'pandas'`
**Solution:** Install dependencies:
```bash
cd app/backend
pip install -r requirements.txt
```

### Issue: Model Loading Errors
**Possible causes:**
- Missing model artifacts in `backend/model/`
- TensorFlow version mismatch
- Corrupted model files

**Solution:**
1. Verify all files exist: `final_model.keras`, `scaler.pkl`, `config.json`, etc.
2. Check TensorFlow version: `pip show tensorflow`
3. Re-download model artifacts from Kaggle if needed

### Issue: Port 5000 Already in Use
**Solution 1:** Stop the running process:
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5000 | xargs kill -9
```

**Solution 2:** Change port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Issue: CSV Validation Fails
**Common errors:**
- Not exactly 24 rows → Must have exactly 24 hours of data
- Wrong column names → Check spelling and case sensitivity
- Missing columns → Must have all 6 columns
- Non-numeric values → All values must be numbers

**Solution:** Use the sample CSV as a template:
```bash
# Download from the web UI or use sample_input.csv
```

### Issue: scikit-learn Version Warning
```
InconsistentVersionWarning: Trying to unpickle estimator MinMaxScaler 
from version 1.6.1 when using version 1.5.2
```

**Solution:** Upgrade scikit-learn:
```bash
pip install scikit-learn==1.6.1
```

### Issue: CORS Errors in Browser
**Solution:** Flask-CORS is already configured. If issues persist:
1. Check browser console for specific errors
2. Verify Flask-CORS is installed: `pip show flask-cors`
3. Try accessing from `http://127.0.0.1:5000` instead of `localhost`

---

## 📚 Documentation

- **PRD.md** - Complete Product Requirements Document
- **API Endpoints** - See "API Endpoints" section above
- **Model Architecture** - See "Model Information" section
- **Code Comments** - All Python files are well-documented

---

## 🎓 Academic Use

This project was developed for academic demonstration purposes as part of a thesis on residential electricity forecasting using deep learning.

**Key Highlights:**
- End-to-end ML pipeline (data → training → deployment)
- PRD-driven development methodology
- Production-ready Flask API
- Professional UI/UX with Chart.js
- Comprehensive error handling and validation
- Model metrics dashboard for presentation

---

## 📄 License

This project is for academic and educational purposes.

---

## 👤 Author

Developed as part of a residential electricity consumption forecasting research project.

**Technologies Used:**
- Python 3.12
- Flask 2.3.3
- TensorFlow 2.20.0 / Keras 3.13.2
- pandas 3.0.0
- scikit-learn 1.6.1
- Chart.js 4.4.1
- HTML5 / CSS3 / JavaScript

---

## 🙏 Acknowledgments

- **Dataset:** UCI Machine Learning Repository - Individual Household Electric Power Consumption
- **Training Platform:** Kaggle (GPU acceleration)
- **Deep Learning Framework:** TensorFlow/Keras
- **Web Framework:** Flaskrature": 25.5, "humidity": 65.0, "hour": 14, "day_of_week": 2}}'
```

## Troubleshooting

### Model Loading Issues
- Ensure all model artifacts are in the `backend/model/` directory
- Check that the model file is compatible with your TensorFlow version

### Port Already in Use
- Change the port in `app.py`: `app.run(port=5001)`

### Missing Dependencies
- Reinstall requirements: `pip install -r requirements.txt --force-reinstall`

## License

[Your License Here]

## Contact

[Your Contact Information]
