def validate_csv_window(df, selected_features, target_col, lookback=24):
    """
    Validate CSV upload for 24-hour lookback window prediction (PRD Section 11)
    
    PRD Requirements:
    - Input vector length = 6 (5 features + target history)
    - Lookback window = 24 hours
    - Output = 1-hour ahead prediction
    
    Args:
        df: pandas DataFrame from uploaded CSV
        selected_features: List of required feature column names
        target_col: Target column name (Global_active_power)
        lookback: Required number of timesteps (default: 24)
        
    Returns:
        Tuple (is_valid, error_message, cleaned_df)
    """
    import pandas as pd
    import numpy as np
    
    # Check if dataframe is empty
    if df is None or len(df) == 0:
        return False, "CSV file is empty", None
    
    # PRD Section 11: Must have exactly 24 rows for lookback window
    if len(df) != lookback:
        return False, f"CSV must contain exactly {lookback} rows (hours) of historical data. Found {len(df)} rows.", None
    
    # Required columns: selected_features + target_col
    required_columns = selected_features + [target_col]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}. Required: {', '.join(required_columns)}", None
    
    # Select only required columns in correct order
    try:
        df_cleaned = df[required_columns].copy()
    except Exception as e:
        return False, f"Error selecting columns: {str(e)}", None
    
    # Convert all columns to numeric
    for col in required_columns:
        try:
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
        except Exception as e:
            return False, f"Error converting column '{col}' to numeric: {str(e)}", None
    
    # Check for NaN values after conversion
    if df_cleaned.isnull().any().any():
        nan_columns = df_cleaned.columns[df_cleaned.isnull().any()].tolist()
        return False, f"Invalid or missing numeric values found in columns: {', '.join(nan_columns)}", None
    
    # Validate realistic ranges for features
    ranges = {
        "Global_intensity": (0, 50),
        "Sub_metering_3": (0, 50),
        "Voltage": (200, 260),
        "Global_reactive_power": (0, 2),
        "Sub_metering_2": (0, 50),
        "Global_active_power": (0, 12)  # Target column
    }
    
    for col, (min_val, max_val) in ranges.items():
        if col in df_cleaned.columns:
            out_of_range = (df_cleaned[col] < min_val) | (df_cleaned[col] > max_val)
            if out_of_range.any():
                bad_rows = out_of_range.sum()
                return False, f"Column '{col}' has {bad_rows} values out of realistic range [{min_val}, {max_val}]", None
    
    return True, None, df_cleaned

def validate_feature_range(features, ranges):
    """
    Validate that features are within expected ranges
    
    Args:
        features: Dictionary of feature values
        ranges: Dictionary of (min, max) tuples for each feature
        
    Returns:
        Tuple (is_valid, error_message)
    """
    for feature, value in features.items():
        if feature in ranges:
            min_val, max_val = ranges[feature]
            if value < min_val or value > max_val:
                return False, f"Feature '{feature}' value {value} out of range [{min_val}, {max_val}]"
    
    return True, None
