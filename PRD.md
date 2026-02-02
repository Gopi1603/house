# Product Requirements Document (PRD)

## Product Name

**Residential Electricity Consumption Forecasting Web Application**

---

## 1. Executive Summary

This Product Requirements Document (PRD) defines the scope, requirements, and implementation plan for a **Flask-based web application** that forecasts short-term residential electricity consumption using a deep learning model.

The application leverages a **CNN–BiLSTM with Self-Attention** model trained on the **UCI Individual Household Electric Power Consumption dataset** using Kaggle. The final system allows users to input recent household electrical measurements and receive a **next-hour electricity consumption prediction (kW)**.

The goal is to bridge **academic machine learning research** and **real-world deployment**, demonstrating an end-to-end pipeline from data preprocessing and model training to production-ready inference.

---

## 2. Business Context & Problem Statement

### 2.1 Problem

Residential electricity consumption varies significantly based on time, usage patterns, and appliance behavior. Utility providers and households lack accurate short-term forecasting tools that:

* Capture non-linear temporal dependencies
* Adapt to hourly consumption patterns
* Are easy to use and deploy

### 2.2 Opportunity

By combining deep learning with a lightweight web interface:

* Users can make **informed energy usage decisions**
* Researchers can demonstrate **applied AI deployment**
* The system can serve as a foundation for **smart grid and IoT integrations**

---

## 3. Target Users & Stakeholders

### 3.1 Primary Users

* Students / Researchers (academic demonstration)
* Energy analytics learners
* Technical evaluators (viva / project defense)

### 3.2 Stakeholders

* Project guide / evaluator
* Academic institution
* Future developers extending the system

---

## 4. Scope Definition

### 4.1 In Scope (What to Build)

* Flask-based prediction API
* Web UI for data input and output
* Integration with trained deep learning model
* Single-household, hourly forecasting
* Visualization of prediction results

### 4.2 Out of Scope (What NOT to Build)

* User authentication
* Multi-user accounts
* Real-time sensor ingestion
* Weather or pricing-based forecasting
* Mobile application

---

## 5. Kaggle Work (Completed – Model Development)

### 5.1 Dataset

* **UCI Individual Household Electric Power Consumption Dataset**
* Duration: Dec 2006 – Nov 2010
* Sampling: 1 minute → resampled to **hourly**
* Features: Voltage, Global Intensity, Sub-meterings, Reactive Power

### 5.2 Data Preprocessing

* Missing value handling (forward/backward fill)
* Date-time parsing and indexing
* Hourly resampling (mean aggregation)
* Feature scaling (MinMaxScaler)

### 5.3 Feature Selection

* Mutual Information (MI) analysis
* Selected features:

  * Global_intensity
  * Sub_metering_3
  * Voltage
  * Global_reactive_power
  * Sub_metering_2

### 5.4 Model Architecture

**Final Selected Model: CNN–BiLSTM–Self-Attention**

Pipeline:

* Conv1D → Local temporal feature extraction
* BiLSTM → Long-term temporal dependencies
* Self-Attention → Important timestep weighting
* Dense → Regression output

### 5.5 Model Comparison Results

| Model         | RMSE (kW) | MAE (kW)  | R²        |
| ------------- | --------- | --------- | --------- |
| CNN-BiLSTM-SA | **0.465** | **0.328** | **0.562** |
| CNN-BiGRU-SA  | 0.472     | 0.339     | 0.549     |

**CNN-BiLSTM-SA selected as final model.**

### 5.6 Exported Artifacts

* `final_model.keras`
* `scaler.pkl`
* `selected_features.json`
* `config.json`
* `metrics_final.json`

---

## 6. User Stories & Acceptance Criteria

### User Story 1: Forecast Consumption

**As a user**, I want to input recent household electrical parameters so that I can predict the next hour's power consumption.

**Acceptance Criteria:**

* User can enter all required features
* System returns prediction in kW
* Prediction completes in < 2 seconds

---

### User Story 2: Understand Model Output

**As a user**, I want a clear visual and numeric output to interpret the prediction.

**Acceptance Criteria:**

* Predicted value displayed clearly
* Units shown in kW
* Optional chart visualization

---

## 7. Functional Requirements

* Load trained model at application startup
* Accept input corresponding to selected features
* Validate input data
* Scale input using saved scaler
* Predict next-hour consumption
* Inverse-scale output
* Return result to UI

---

## 8. Non-Functional Requirements

### 8.1 Performance

* Prediction latency ≤ 2 seconds
* Model loaded once (no reload per request)

### 8.2 Scalability

* Single-instance Flask app
* Modular design for future API expansion

### 8.3 Usability

* Simple form-based UI
* Clear labels and units

---

## 9. System Architecture

### 9.1 High-Level Architecture

```
User → Web UI → Flask App → ML Model → Prediction → UI
```

### 9.2 Technology Stack

| Layer    | Technology         |
| -------- | ------------------ |
| Frontend | HTML, CSS, JS      |
| Backend  | Python, Flask      |
| ML       | TensorFlow / Keras |
| Data     | NumPy, Pandas      |

---

## 10. API Specifications

### POST /predict

**Request Payload:**

```json
{
  "Global_intensity": 15.2,
  "Sub_metering_3": 18.0,
  "Voltage": 234.5,
  "Global_reactive_power": 0.12,
  "Sub_metering_2": 3.5
}
```

**Response:**

```json
{
  "predicted_power_kw": 0.78
}
```

---

## 11. Data Model

* Input vector length = 6 (5 features + target history)
* Lookback window = 24 hours
* Output = 1-hour ahead prediction

---

## 12. Security & Compliance

* No personal data stored
* Local inference only
* No authentication required

---

## 13. Risks & Mitigation

| Risk                   | Mitigation                  |
| ---------------------- | --------------------------- |
| Overfitting            | Early stopping + validation |
| Data drift             | Future retraining           |
| Limited generalization | Documented as limitation    |

---

## 14. Implementation Timeline

| Phase                   | Duration  |
| ----------------------- | --------- |
| Model Training (Kaggle) | Completed |
| PRD & Design            | 1 week    |
| Flask Development       | 1 week    |
| Testing                 | 3 days    |
| Final Submission        | 2 days    |

---

## 15. Success Metrics (KPIs)

* RMSE < 0.5 kW
* R² > 0.55
* Successful Flask inference
* Positive evaluation feedback

---

## 16. Future Enhancements

* Multi-household forecasting
* Weather-based features
* Transformer-based models
* IoT sensor integration
* Real-time dashboard

---

## 17. Conclusion

This PRD defines a complete, production-aligned blueprint for deploying a deep learning-based electricity forecasting system. It demonstrates not only predictive accuracy but also engineering maturity through modular design, clear documentation, and real-world applicability.

---

**End of Document**
