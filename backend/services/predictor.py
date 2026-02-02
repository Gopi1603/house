import os
import json
import numpy as np
import pandas as pd
import joblib
from tensorflow import keras
from services.custom_layers import SelfAttention

class ElectricityPredictor:
    def __init__(self, model_dir):
        """
        Initialize the predictor with model artifacts
        
        Args:
            model_dir: Directory containing model artifacts
        """
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
        self.config = None
        self.selected_features = None
        
        self._load_artifacts()
    
    def _load_artifacts(self):
        """Load all model artifacts"""
        try:
            # Load model with custom objects and compile=False to skip missing weights
            model_path = os.path.join(self.model_dir, 'final_model.keras')
            try:
                self.model = keras.models.load_model(
                    model_path,
                    custom_objects={'SelfAttention': SelfAttention},
                    compile=False
                )
                # Recompile the model
                self.model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            except Exception as load_error:
                print(f"Warning: Could not load with SelfAttention: {load_error}")
                print("Trying alternative loading method...")
                # If loading with custom layer fails, try loading with safe_mode
                self.model = keras.models.load_model(
                    model_path,
                    custom_objects={'SelfAttention': SelfAttention},
                    safe_mode=False
                )
            
            # Load scaler
            scaler_path = os.path.join(self.model_dir, 'scaler.pkl')
            self.scaler = joblib.load(scaler_path)
            
            # SCALER SANITY CHECK
            print("SCALER VERIFY:", type(self.scaler))
            if hasattr(self.scaler, "n_features_in_"):
                print("SCALER n_features_in_:", self.scaler.n_features_in_)
            else:
                print("SCALER n_features_in_: <missing attribute>")
            
            # Enforce correct feature count (5 features + 1 target = 6)
            if hasattr(self.scaler, "n_features_in_") and self.scaler.n_features_in_ != 6:
                raise ValueError(f"Scaler expects {self.scaler.n_features_in_} features, but model pipeline requires 6 (5 features + target).")
            
            # Load config
            config_path = os.path.join(self.model_dir, 'config.json')
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            
            # Load selected features
            features_path = os.path.join(self.model_dir, 'selected_features.json')
            with open(features_path, 'r') as f:
                self.selected_features = json.load(f)
            
            # PRD VERIFICATION: Print model input shape
            print("\n" + "="*60)
            print("PRD COMPLIANCE VERIFICATION - MODEL INPUT SHAPE")
            print("="*60)
            print(f"Model Input Shape: {self.model.input_shape}")
            print(f"Expected Shape: (None, 24, 6)")
            if self.model.input_shape == (None, 24, 6):
                print("✓ PASS: Model shape matches PRD Section 11 requirements")
            else:
                print("✗ FAIL: Model shape does NOT match PRD requirements")
            print("="*60 + "\n")
            
            print("Model artifacts loaded successfully")
            
        except Exception as e:
            print(f"Error loading model artifacts: {e}")
            raise
    
    def is_loaded(self):
        """Check if model is loaded"""
        return self.model is not None
    
    def predict_from_window(self, df_window):
        """
        Make prediction from 24-hour historical window (PRD-compliant)
        
        PRD Section 11 Requirements:
        - Input vector length = 6 (5 features + target history)
        - Lookback window = 24 hours
        - Output = 1-hour ahead prediction
        
        Args:
            df_window: pandas DataFrame with exactly 24 rows
                      Columns: selected_features + target_col (Global_active_power)
                      Already validated by validate_csv_window()
            
        Returns:
            Dictionary with:
            - predicted_power_kw: Next hour prediction in kW
            - actual_last_24h_kw: List of 24 historical target values
            - predicted_next_hour_kw: Same as predicted_power_kw (for clarity)
        """
        try:
            # Verify we have exactly 24 rows
            if len(df_window) != 24:
                raise ValueError(f"Expected exactly 24 rows, got {len(df_window)}")
            
            # Extract column order: selected_features + target_col
            target_col = self.config['target_col']  # Global_active_power
            column_order = self.selected_features + [target_col]
            
            # Ensure all columns exist
            missing_cols = [col for col in column_order if col not in df_window.columns]
            if missing_cols:
                raise ValueError(f"Missing columns: {missing_cols}")
            
            # Extract data in correct order
            X_with_target = df_window[column_order].values  # Shape: (24, 6)
            
            # Store actual historical target values for response
            actual_last_24h = df_window[target_col].values.tolist()
            
            # Scale the entire window (features + target together)
            X_scaled = self.scaler.transform(X_with_target)  # Shape: (24, 6)
            
            # Reshape for model: (batch_size=1, timesteps=24, features=6)
            X_scaled = X_scaled.reshape(1, 24, len(column_order))
            
            # Make prediction (returns scaled target value)
            prediction_scaled = self.model.predict(X_scaled, verbose=0)  # Shape: (1, 1)
            
            # Inverse transform to get kW value
            # The scaler expects shape (n_samples, n_features) where n_features=6
            # We need to create a dummy array with the prediction in the target column position
            
            # Create dummy array: [0, 0, 0, 0, 0, predicted_value]
            # Target column is at index 5 (last column)
            dummy_scaled = np.zeros((1, len(column_order)))
            dummy_scaled[0, -1] = prediction_scaled[0, 0]  # Put prediction in last column
            
            # Inverse transform
            dummy_original = self.scaler.inverse_transform(dummy_scaled)
            predicted_kw = dummy_original[0, -1]  # Extract the target value
            
            return {
                'predicted_power_kw': float(predicted_kw),
                'actual_last_24h_kw': actual_last_24h,
                'predicted_next_hour_kw': float(predicted_kw)
            }
            
        except Exception as e:
            print(f"Error during prediction: {e}")
            raise
