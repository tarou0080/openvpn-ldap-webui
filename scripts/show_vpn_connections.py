#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timezone, timedelta

DATABASE_PATH = '/app/data/db/vpn.db'
JST = timezone(timedelta(hours=9))

def convert_utc_to_jst(utc_str):
    if not utc_str:
        return None
    dt = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S')

conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

cursor.execute('''
    SELECT username, cert_common_name, client_ip, vpn_ip, connected_at, disconnected_at
    FROM vpn_connections 
    ORDER BY connected_at DESC 
    LIMIT 10
''')

print("=== VPN Connection History (Last 10) ===")
for row in cursor.fetchall():
    username, cert_name, client_ip, vpn_ip, connected_at, disconnected_at = row
    print(f"\nUser: {username}")
    print(f"Certificate: {cert_name}")
    print(f"Client IP: {client_ip}")
    print(f"VPN IP: {vpn_ip}")
    print(f"Connected at: {convert_utc_to_jst(connected_at)}")
    if disconnected_at:
        print(f"Disconnected at: {convert_utc_to_jst(disconnected_at)}")

conn.close()