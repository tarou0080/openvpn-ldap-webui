#!/usr/bin/env python3
import sqlite3
import os

DATABASE_PATH = '/app/data/db/vpn.db'
conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

# テーブル一覧取得
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
tables = cursor.fetchall()

print("=== Database Table List ===")
for table in tables:
    print(f"  - {table[0]}")

# Check vpn_connections table schema
if any('vpn_connections' in t for t in tables):
    print("\n=== vpn_connections Table Structure ===")
    cursor.execute("PRAGMA table_info(vpn_connections);")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
else:
    print("\nvpn_connections table not found")

conn.close()
