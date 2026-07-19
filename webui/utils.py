#!/usr/bin/env python3
from datetime import datetime, timezone, timedelta
import logging
from config import JST

logger = logging.getLogger(__name__)

def convert_utc_to_jst(utc_datetime_str):
    """Convert UTC time string to JST time string"""
    if not utc_datetime_str:
        return None
    
    try:
        # Convert string from SQLite to datetime object
        utc_dt = datetime.fromisoformat(utc_datetime_str.replace('Z', '+00:00'))
        
        # Recognize as UTC
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        
        # Convert to JST
        jst_dt = utc_dt.astimezone(JST)
        
        # Return as display string
        return jst_dt.strftime('%Y-%m-%d %H:%M:%S')
    
    except Exception as e:
        logger.error(f"Timezone conversion error: {str(e)}")
        return utc_datetime_str  # Return original string in case of error

def convert_db_row_timestamps(row_data, timestamp_columns):
    """Convert timestamps in specified columns of database row data to JST"""
    if not row_data:
        return row_data
    
    # Convert tuple to list
    row_list = list(row_data) if isinstance(row_data, tuple) else row_data
    
    for col_index in timestamp_columns:
        if col_index < len(row_list) and row_list[col_index]:
            row_list[col_index] = convert_utc_to_jst(row_list[col_index])
    
    return tuple(row_list) if isinstance(row_data, tuple) else row_list

def get_current_jst_time():
    """Get current JST time"""
    return datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')

def escape_like(s):
    """Escape for LIKE clause"""
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

def format_duration(seconds):
    """Convert seconds to 'X hours Y minutes' format"""
    if seconds is None:
        return None
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours} hours {minutes} minutes"
    else:
        return f"{minutes} minutes"

def validate_cert_serial(cert_serial):
    """Certificate serial validation (security check)"""
    # Check for dangerous characters
    dangerous_chars = ['..', '/', '\\', ';', '&', '|', '$', '`', '\n', '\r', '\0']
    for char in dangerous_chars:
        if char in cert_serial:
            return False
    
    # Length limit
    if len(cert_serial) > 100:
        return False
    
    return True
