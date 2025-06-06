#!/usr/bin/env python3
"""
Script to show the raw database content for educational purposes.
WARNING: This script is for understanding the database structure only.
"""

import os
import sys
import sqlite3
from tabulate import tabulate

def dump_raw_database():
    """Show the raw contents of the database"""
    db_path = os.path.join(os.path.dirname(__file__), 'users.db')
    
    if not os.path.exists(db_path):
        print(f"Database file not found at: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all raw user records
    cursor.execute('SELECT * FROM users')
    rows = cursor.fetchall()
    
    if not rows:
        print("No data found in the database.")
        return
    
    # Prepare data for display
    table_data = []
    for row in rows:
        row_dict = dict(row)
        # Mask sensitive data
        if 'encrypted_token' in row_dict:
            row_dict['encrypted_token'] = "[ENCRYPTED]"
        if 'encrypted_api_key' in row_dict:
            row_dict['encrypted_api_key'] = "[ENCRYPTED]"
        table_data.append(row_dict)
    
    # Display as a table
    print(tabulate(table_data, headers="keys", tablefmt="grid"))
    
    conn.close()

if __name__ == "__main__":
    print("WARNING: This script shows raw database content with sensitive values masked.")
    print("This is for educational purposes to understand the database structure.")
    print()
    
    dump_raw_database() 