import pandas as pd
import numpy as np

def preprocess_input(raw_data):
    """
    Preprocess raw input data for model prediction
    
    Args:
        raw_data: Dictionary or DataFrame containing raw feature values
        
    Returns:
        Preprocessed data ready for model input
    """
    if isinstance(raw_data, dict):
        df = pd.DataFrame([raw_data])
    else:
        df = raw_data.copy()
    
    # Apply any necessary transformations
    # (e.g., encoding, feature engineering, etc.)
    
    return df

def create_temporal_features(df, timestamp_col='timestamp'):
    """
    Create temporal features from timestamp
    
    Args:
        df: DataFrame with timestamp column
        timestamp_col: Name of timestamp column
        
    Returns:
        DataFrame with additional temporal features
    """
    if timestamp_col not in df.columns:
        return df
    
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    
    # Extract temporal features
    df['hour'] = df[timestamp_col].dt.hour
    df['day_of_week'] = df[timestamp_col].dt.dayofweek
    df['month'] = df[timestamp_col].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    return df

def handle_missing_values(df, strategy='mean'):
    """
    Handle missing values in the dataset
    
    Args:
        df: Input DataFrame
        strategy: Strategy for handling missing values ('mean', 'median', 'forward_fill')
        
    Returns:
        DataFrame with missing values handled
    """
    df = df.copy()
    
    if strategy == 'mean':
        df = df.fillna(df.mean())
    elif strategy == 'median':
        df = df.fillna(df.median())
    elif strategy == 'forward_fill':
        df = df.fillna(method='ffill')
    
    return df
