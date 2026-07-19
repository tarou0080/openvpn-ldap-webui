#!/usr/bin/env python3
"""
Parse OpenVPN logs and record VPN connection history to the database.
Execution location: /srv/vpn/scripts/
"""

import re
import sqlite3
import os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Settings
DATABASE_PATH = os.environ.get('DATABASE_PATH', '/app/data/db/vpn.db')
OPENVPN_LOG_DIR = os.environ.get('OPENVPN_LOG_PATH', '/app/data/open-logs')
OPENVPN_LOG_PATH = os.path.join(OPENVPN_LOG_DIR, 'openvpn.log')
OPENVPN_STATUS_PATH = os.path.join(OPENVPN_LOG_DIR, 'openvpn-status.log')
STATE_FILE = '/app/data/logs/vpn_log_parser_state.txt'

# Japan Standard Time timezone
JST = timezone(timedelta(hours=9))

def parse_timestamp(timestamp_str):
    """Convert timestamp to UTC datetime object (logs are already in JST)"""
    try:
        # Logs are already in JST, so parse as JST and convert to UTC
        dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        dt_jst = dt.replace(tzinfo=JST)
        dt_utc = dt_jst.astimezone(timezone.utc)
        return dt_utc.isoformat()
    except Exception as e:
        print(f"Timestamp parsing error: {timestamp_str} - {e}")
        return None

def get_last_processed_line():
    """Get the last processed line number"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return int(f.read().strip())
    except:
        pass
    return 0

def save_last_processed_line(line_number):
    """Save the last processed line number"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        f.write(str(line_number))

def save_connection_to_db(connection):
    """Save connection information to the database immediately"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Check if the same connection is already recorded
        cursor.execute('''
            SELECT id FROM vpn_connections 
            WHERE username = ? AND client_ip = ? AND client_port = ? AND connected_at = ?
            LIMIT 1
        ''', (connection['username'], connection['client_ip'], connection['client_port'], connection['connected_at']))
        
        if cursor.fetchone():
            print(f"Skipping (existing): {connection['username']} from {connection['client_ip']}:{connection['client_port']}")
            conn.close()
            return False
        
        # Save new connection
        cursor.execute('''
            INSERT INTO vpn_connections 
            (username, cert_common_name, client_ip, client_port, vpn_ip, connected_at, disconnected_at, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            connection['username'],
            connection['cert_common_name'],
            connection['client_ip'],
            connection['client_port'],
            connection['vpn_ip'],
            connection['connected_at'],
            None,
            None
        ))
        
        conn.commit()
        conn.close()
        
        print(f"Saved: {connection['username']} ({connection['cert_common_name']}) from {connection['client_ip']}:{connection['client_port']}")
        return True
        
    except Exception as e:
        print(f"Save error: {e}")
        return False

def update_disconnection(username, client_ip, client_port, disconnected_at_str):
    """
    Update the database with disconnection information
    disconnection_type: 'normal' (normal disconnection detected in logs)
    """
    try:
        disconnected_at = parse_timestamp(disconnected_at_str)
        
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Identify session by port number (for records that are not disconnected)
        cursor.execute('''
            SELECT id, connected_at FROM vpn_connections 
            WHERE username = ? AND client_ip = ? AND client_port = ? AND disconnected_at IS NULL
            ORDER BY connected_at DESC
            LIMIT 1
        ''', (username, client_ip, client_port))
        
        result = cursor.fetchone()
        
        if result:
            conn_id, connected_at = result
            
            # Calculate connection duration (seconds)
            try:
                conn_dt = datetime.fromisoformat(connected_at.replace('Z', '+00:00'))
                disconn_dt = datetime.fromisoformat(disconnected_at.replace('Z', '+00:00'))
                
                if conn_dt.tzinfo is None:
                    conn_dt = conn_dt.replace(tzinfo=timezone.utc)
                if disconn_dt.tzinfo is None:
                    disconn_dt = disconn_dt.replace(tzinfo=timezone.utc)
                
                duration_seconds = int((disconn_dt - conn_dt).total_seconds())
                
                # Check for negative values
                if duration_seconds < 0:
                    print(f"Warning: Connection duration is negative ({duration_seconds} seconds). Disconnection time is earlier than connection time.")
                    duration_seconds = 0
                    
            except Exception as e:
                print(f"Connection duration calculation error: {e}")
                duration_seconds = None
            
            # Update disconnection time and duration (normal for log detection)
            cursor.execute('''
                UPDATE vpn_connections 
                SET disconnected_at = ?,
                    duration_seconds = ?,
                    disconnection_type = 'normal',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (disconnected_at, duration_seconds, conn_id))
            
            conn.commit()
            print(f"Disconnection record updated: {username} from {client_ip}:{client_port}, duration: {duration_seconds} seconds")
        else:
            print(f"No corresponding connection record found for disconnection: {username} from {client_ip}:{client_port}")
        
        conn.close()
        
    except Exception as e:
        print(f"Disconnection record update error: {e}")

def parse_status_log():
    """Parse openvpn-status.log to get current connection information"""
    active_connections = {}
    status_updated_at = None
    
    if not os.path.exists(OPENVPN_STATUS_PATH):
        print(f"Status file not found: {OPENVPN_STATUS_PATH}")
        return active_connections, status_updated_at
    
    try:
        with open(OPENVPN_STATUS_PATH, 'r') as f:
            lines = f.readlines()
            
        # Get update time from "Updated" line
        for line in lines:
            if line.startswith('Updated,') :
                timestamp_str = line.strip().split(',', 1)[1]
                status_updated_at = timestamp_str
                break
        
        # Parse CLIENT LIST section
        in_client_list = False
        for line in lines:
            line = line.strip()
            
            if line == 'OpenVPN CLIENT LIST':
                in_client_list = True
                continue
            elif line == 'ROUTING TABLE':
                in_client_list = False
                break
            
            if in_client_list and ',' in line and not line.startswith('Common Name') and not line.startswith('Updated'):
                # Common Name,Real Address,Bytes Received,Bytes Sent,Connected Since
                parts = line.split(',')
                if len(parts) >= 2:
                    common_name = parts[0]
                    real_address = parts[1]  # IP:Port format
                    
                    if ':' in real_address:
                        client_ip, client_port = real_address.rsplit(':', 1)
                        key = f"{common_name}:{client_ip}:{client_port}"
                        active_connections[key] = {
                            'common_name': common_name,
                            'client_ip': client_ip,
                            'client_port': int(client_port)
                        }
        
        print(f"Status log read: {len(active_connections)} active connections")
        
    except Exception as e:
        print(f"Status log parsing error: {e}")
    
    return active_connections, status_updated_at

def reconcile_active_connections():
    """
    Reconcile with status.log to update connections that are actually disconnected.
    disconnection_type: 'abnormal' (abnormal disconnection where no log was output, e.g., service restart)
    """
    active_connections, status_updated_at = parse_status_log()
    
    if status_updated_at is None:
        print("Could not get status log update time")
        return
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get records where disconnected_at is NULL
        cursor.execute('''
            SELECT id, username, cert_common_name, client_ip, client_port, connected_at
            FROM vpn_connections
            WHERE disconnected_at IS NULL
        ''')
        
        db_connections = cursor.fetchall()
        print(f"Active connection records in DB: {len(db_connections)}")
        
        updated_count = 0
        for record in db_connections:
            conn_id, username, cert_common_name, client_ip, client_port, connected_at = record
            
            # Check if it exists in status.log
            # cert_common_name and username are usually the same, but check both just in case
            key1 = f"{cert_common_name}:{client_ip}:{client_port}"
            key2 = f"{username}:{client_ip}:{client_port}"
            
            if key1 not in active_connections and key2 not in active_connections:
                # Does not exist in status.log = disconnected
                disconnected_at = parse_timestamp(status_updated_at)
                
                # Calculate connection duration
                try:
                    conn_dt = datetime.fromisoformat(connected_at.replace('Z', '+00:00'))
                    disconn_dt = datetime.fromisoformat(disconnected_at.replace('Z', '+00:00'))
                    
                    if conn_dt.tzinfo is None:
                        conn_dt = conn_dt.replace(tzinfo=timezone.utc)
                    if disconn_dt.tzinfo is None:
                        disconn_dt = disconn_dt.replace(tzinfo=timezone.utc)
                    
                    duration_seconds = int((disconn_dt - conn_dt).total_seconds())
                    
                    if duration_seconds < 0:
                        print(f"Warning: Connection duration is negative ({duration_seconds} seconds)")
                        duration_seconds = 0
                        
                except Exception as e:
                    print(f"Connection duration calculation error: {e}")
                    duration_seconds = None
                
                # Update to disconnected state (abnormal for auto-detection)
                cursor.execute('''
                    UPDATE vpn_connections
                    SET disconnected_at = ?,
                        duration_seconds = ?,
                        disconnection_type = 'abnormal',
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (disconnected_at, duration_seconds, conn_id))
                
                updated_count += 1
                print(f"Abnormal disconnection detected: {username} ({cert_common_name}) from {client_ip}:{client_port}, duration: {duration_seconds} seconds")
        
        conn.commit()
        conn.close()
        
        print(f"Reconciliation complete: {updated_count} records updated as abnormal disconnection")
        
    except Exception as e:
        print(f"Reconciliation processing error: {e}")

def parse_log_file():
    """Parse log file to extract VPN connection information"""
    
    if not os.path.exists(OPENVPN_LOG_PATH):
        print(f"Log file not found: {OPENVPN_LOG_PATH}")
        return
    
    last_line = get_last_processed_line()
    current_line = 0
    
    # Temporarily store connection information (keyed by client_ip:port)
    temp_connections = {}
    
    # Regex patterns
    # Get certificate name: "133.32.227.188:3219 VERIFY OK: depth=0, CN=testuser-iphone"
    cert_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([\d.]+):(\d+) VERIFY OK: depth=0, CN=(.+)$')
    
    # Connection complete: "testuser/133.32.227.188:3219 MULTI: primary virtual IP for testuser/133.32.227.188:3219: 10.8.0.6"
    connect_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([^/]+)/([\d.]+):(\d+) MULTI: primary virtual IP for .+: ([\d.]+)$')
    
    # Disconnection: "testuser/133.32.227.188:3209 SIGTERM[soft,remote-exit] received, client-instance exiting"
    disconnect_pattern = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([^/]+)/([\d.]+):(\d+) SIGTERM.*client-instance exiting$')
    
    with open(OPENVPN_LOG_PATH, 'r') as f:
        for line in f:
            current_line += 1
            
            # Skip already processed lines
            if current_line <= last_line:
                continue
            
            line = line.strip()
            
            # Get certificate name
            cert_match = cert_pattern.search(line)
            if cert_match:
                timestamp, client_ip, client_port, cert_name = cert_match.groups()
                session_key = f"{client_ip}:{client_port}"
                if session_key not in temp_connections:
                    temp_connections[session_key] = {}
                temp_connections[session_key]['cert_name'] = cert_name
                temp_connections[session_key]['client_port'] = int(client_port)
                continue
            
            # Detect connection completion
            connect_match = connect_pattern.search(line)
            if connect_match:
                timestamp, username, client_ip, client_port, vpn_ip = connect_match.groups()
                session_key = f"{client_ip}:{client_port}"
                
                if session_key not in temp_connections:
                    temp_connections[session_key] = {}
                
                temp_connections[session_key].update({
                    'username': username,
                    'client_ip': client_ip,
                    'client_port': int(client_port),
                    'vpn_ip': vpn_ip,
                    'connected_at': timestamp
                })
                
                # Immediately save to DB if certificate name and connection info are available
                if 'cert_name' in temp_connections[session_key]:
                    conn_info = temp_connections[session_key]
                    connection = {
                        'username': conn_info['username'],
                        'cert_common_name': conn_info['cert_name'],
                        'client_ip': conn_info['client_ip'],
                        'client_port': conn_info['client_port'],
                        'vpn_ip': conn_info['vpn_ip'],
                        'connected_at': parse_timestamp(conn_info['connected_at'])
                    }
                    print(f"Connection detected: {conn_info['username']} ({conn_info['cert_name']}) from {client_ip}:{client_port}")
                    save_connection_to_db(connection)
                continue
            
            # Detect disconnection (SIGTERM)
            disconnect_match = disconnect_pattern.search(line)
            if disconnect_match:
                timestamp, username, client_ip, client_port = disconnect_match.groups()
                client_port = int(client_port)
                print(f"Disconnection detected: {username} from {client_ip}:{client_port} at {timestamp}")
                
                # Update corresponding connection record in the database
                update_disconnection(username, client_ip, client_port, timestamp)
                continue
    
    # Save state
    save_last_processed_line(current_line)

def main():
    now = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
    print(f"=== Starting OpenVPN log analysis [{now}] ===")
    print(f"Log file: {OPENVPN_LOG_PATH}")
    print(f"Status file: {OPENVPN_STATUS_PATH}")
    print(f"Database: {DATABASE_PATH}")
    print(f"State file: {STATE_FILE}")
    print()
    
    # Parse logs
    parse_log_file()
    
    # Reconcile with status.log (auto-disconnection process)
    print("\n--- Reconciling connection status ---")
    reconcile_active_connections()
    
    end_time = datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n=== Processing complete [{end_time}] ===")
    print()

if __name__ == '__main__':
    main()