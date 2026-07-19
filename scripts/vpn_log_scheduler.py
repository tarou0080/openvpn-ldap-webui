#!/usr/bin/env python3
"""
Scheduler for the VPN log analysis script.
The operation mode and interval can be controlled by environment variables.
Skips the next execution if the process is already running and records the status in the DB.
"""
import time
import subprocess
import sys
import os
import sqlite3
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
DATABASE_PATH = os.environ.get('DATABASE_PATH', '/app/data/db/vpn.db')

# Read settings from environment variables
SCHEDULE_MODE = os.environ.get('VPN_LOG_SCHEDULE_MODE', 'FIXED')
SCHEDULE_INTERVAL = int(os.environ.get('VPN_LOG_SCHEDULE_INTERVAL', '15'))
SCHEDULE_TIMES = os.environ.get('VPN_LOG_SCHEDULE_TIMES', '0,15,30,45')
PARSER_TIMEOUT = int(os.environ.get('VPN_LOG_PARSER_TIMEOUT', '300'))

def update_scheduler_status(is_running=None, last_run_at=None, status=None, 
                           duration=None, next_run_at=None, error=None):
    """Record scheduler status in the DB"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if is_running is not None:
            updates.append("is_running = ?")
            params.append(is_running)
        if last_run_at is not None:
            updates.append("last_run_at = ?")
            params.append(last_run_at)
        if status is not None:
            updates.append("last_run_status = ?")
            params.append(status)
        if duration is not None:
            updates.append("last_run_duration_seconds = ?")
            params.append(duration)
        if next_run_at is not None:
            updates.append("next_run_at = ?")
            params.append(next_run_at)
        if error is not None:
            updates.append("last_error = ?")
            params.append(error)
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append('vpn-log-parser')
        
        sql = f"UPDATE scheduler_status SET {', '.join(updates)} WHERE task_name = ?"
        cursor.execute(sql, params)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to update scheduler status: {e}", file=sys.stderr)

def log_scheduler_event(event_type, status, message=None, duration=None):
    """Record scheduler event in the DB"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scheduler_events 
            (task_name, event_type, status, message, duration_seconds)
            VALUES (?, ?, ?, ?, ?)
        ''', ('vpn-log-parser', event_type, status, message, duration))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log event: {e}", file=sys.stderr)

def is_running():
    """Check from the DB if it is already running"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_running FROM scheduler_status WHERE task_name = ?",
            ('vpn-log-parser',)
        )
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == 1
    except Exception as e:
        print(f"Failed to check running status: {e}", file=sys.stderr)
        return False

def run_log_parser():
    """Execute the log analysis script"""
    start_time = time.time()
    now_str = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
    
    # Check if running
    if is_running():
        message = f"[{now_str}] Skipped: Previous execution is still running"
        print(message)
        log_scheduler_event('skip', 'skipped', 'Previous execution is still running')
        return False
    
    try:
        # Mark as running
        update_scheduler_status(is_running=1, last_run_at=now_str, error=None)
        print(f"[{now_str}] Starting VPN log parser...")
        
        result = subprocess.run(
            ['/usr/local/bin/python3', '/scripts/parse_vpn_logs.py'],
            capture_output=True,
            text=True,
            timeout=PARSER_TIMEOUT
        )
        
        duration = time.time() - start_time
        
        # Display standard output
        if result.stdout:
            print(result.stdout)
        
        # Display error output
        if result.stderr:
            print(f"STDERR: {result.stderr}", file=sys.stderr)
        
        if result.returncode == 0:
            print(f"[{now_str}] Log parser completed successfully ({duration:.2f}s)")
            update_scheduler_status(
                is_running=0,
                status='success',
                duration=duration
            )
            log_scheduler_event('run', 'success', None, duration)
            return True
        else:
            error_msg = f"Exit code {result.returncode}"
            print(f"[{now_str}] Log parser failed: {error_msg}")
            update_scheduler_status(
                is_running=0,
                status='failed',
                duration=duration,
                error=error_msg
            )
            log_scheduler_event('run', 'failed', error_msg, duration)
            return False
            
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        error_msg = f"Timeout ({PARSER_TIMEOUT}s exceeded)"
        print(f"[{now_str}] {error_msg}")
        update_scheduler_status(
            is_running=0,
            status='timeout',
            duration=duration,
            error=error_msg
        )
        log_scheduler_event('run', 'timeout', error_msg, duration)
        return False
    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        print(f"[{now_str}] Error: {error_msg}")
        update_scheduler_status(
            is_running=0,
            status='error',
            duration=duration,
            error=error_msg
        )
        log_scheduler_event('run', 'error', error_msg, duration)
        return False

def calculate_next_run_fixed():
    """Calculate the next execution time (FIXED: specific time mode)"""
    now = datetime.now(JST)
    current_minute = now.minute
    
    # Parse execution time list
    times = sorted([int(t.strip()) for t in SCHEDULE_TIMES.split(',')])
    
    # Find the next execution minute
    next_minute = None
    for t in times:
        if current_minute < t:
            next_minute = t
            break
    
    # Calculate the next execution time
    if next_minute is None:
        # First execution time of the next hour
        next_run = now.replace(minute=times[0], second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_run = now.replace(minute=next_minute, second=0, microsecond=0)
    
    return next_run

def calculate_next_run_interval():
    """Calculate the next execution time (INTERVAL: every N minutes mode)"""
    now = datetime.now(JST)
    next_run = now + timedelta(minutes=SCHEDULE_INTERVAL)
    return next_run.replace(second=0, microsecond=0)

def calculate_next_run():
    """Calculate the next execution time according to the schedule mode"""
    if SCHEDULE_MODE == 'INTERVAL':
        return calculate_next_run_interval()
    else:  # FIXED
        return calculate_next_run_fixed()

def main():
    mode_desc = f"{SCHEDULE_MODE} mode"
    if SCHEDULE_MODE == 'INTERVAL':
        mode_desc += f" (every {SCHEDULE_INTERVAL} minutes)"
    else:
        mode_desc += f" (at minutes: {SCHEDULE_TIMES})"
    
    print(f"VPN Log Scheduler started - {mode_desc}")
    print(f"Parser timeout: {PARSER_TIMEOUT}s")
    sys.stdout.flush()
    
    while True:
        # Calculate the next execution time
        next_run = calculate_next_run()
        now = datetime.now(JST)
        
        # Record the next execution time in the DB
        update_scheduler_status(next_run_at=next_run.strftime('%Y-%m-%d %H:%M:%S'))
        
        # Calculate wait time
        wait_seconds = (next_run - now).total_seconds()
        
        print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Next run at {next_run.strftime('%Y-%m-%d %H:%M:%S')} (waiting {int(wait_seconds)}s)")
        sys.stdout.flush()
        
        # Wait
        time.sleep(wait_seconds)
        
        # Execute log analysis
        run_log_parser()
        sys.stdout.flush()

if __name__ == '__main__':
    main()